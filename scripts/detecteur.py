"""Modules d'une image thermique : centres (réseau de `train_detector.py`) → rectangles inclinés → découpe de chaque
module dans la matrice de températures → forme de l'anomalie (`anomalies.decrire`) et module plus chaud que ses
voisins (`anomalies.modules_chauds`).

Inclinaison : moyenne des angles quadruplés des gradients autour du centre (bords des modules et des cellules,
les deux familles perpendiculaires votent ensemble), connue à 90° près ; le rectangle incliné (longueur a, largeur b, angle θ) est déduit du cadre droit (W, H) prédit :
    W = a·cos θ + b·sin θ,  H = a·sin θ + b·cos θ.
Vers 45° le système devient mal conditionné : on reprend alors les proportions médianes (longueur / largeur) des
modules sûrs de la même photo (une centrale a des modules identiques) ; à défaut, un carré (`incertain`).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anomalies  # noqa: E402
import train_detector as td  # noqa: E402

MARGE = 0.06          # part de chaque côté retirée à la découpe (cadre alu, joints, imprécision du centre)


def angle_local(img, cx, cy, w, h):
    """Orientation dominante (rad, dans [0, π/2)) des bords dans le cadre droit agrandi de 20 %."""
    H, W = img.shape
    x0, x1 = int(max(0, cx - 0.6 * w)), int(min(W, cx + 0.6 * w + 1))
    y0, y1 = int(max(0, cy - 0.6 * h)), int(min(H, cy + 0.6 * h + 1))
    z = np.asarray(img[y0:y1, x0:x1], dtype=np.float64)
    if z.shape[0] < 3 or z.shape[1] < 3:
        return 0.0
    gx, gy = ndimage.sobel(z, 1), ndimage.sobel(z, 0)
    # angles quadruplés : les deux familles de bords perpendiculaires (θ et θ + 90°) votent pour le même angle
    psi = np.arctan2(gy, gx)
    poids = gx * gx + gy * gy
    phi = math.atan2(float((poids * np.sin(4 * psi)).sum()), float((poids * np.cos(4 * psi)).sum())) / 4
    return phi % (math.pi / 2)


def rectangle(w, h, theta):
    """Cadre droit (w, h) + angle θ ∈ [0, π/2) → (côté selon θ, côté selon θ + 90°, incertain)."""
    c, s = math.cos(theta), math.sin(theta)
    det = c * c - s * s
    if abs(det) > 0.25:
        a, b = (w * c - h * s) / det, (h * c - w * s) / det
        if a > 0 and b > 0:
            return a, b, False
    a = math.sqrt(max(w * h, 1.0) / max(1 + 2 * c * s, 1e-6))
    return a, a, True


def rectangle_proportions(w, h, theta, r):
    """Cadre droit + angle + proportions r = longueur / largeur → (côté selon θ, côté selon θ + 90°) : des deux
    affectations possibles (longueur selon θ ou selon θ + 90°), celle qui reproduit le mieux (w, h)."""
    c, s = math.cos(theta), math.sin(theta)
    meilleur = None
    for ra, rb in ((r, 1.0), (1.0, r)):
        k = (w * (ra * c + rb * s) + h * (ra * s + rb * c)) / ((ra * c + rb * s) ** 2 + (ra * s + rb * c) ** 2)
        e = (ra * k * c + rb * k * s - w) ** 2 + (ra * k * s + rb * k * c - h) ** 2
        if meilleur is None or e < meilleur[0]:
            meilleur = (e, ra * k, rb * k)
    return meilleur[1], meilleur[2]


def detecter(img, modele=None, seuil=td.SEUIL_CENTRE):
    """Image (niveaux de gris ou températures) → liste de modules {cx, cy, angle_deg, longueur, largeur, coins,
    score, incertain, complet} ; longueur ≥ largeur, angle de la longueur par rapport à l'axe x (sens image).
    `complet` est faux pour un module coupé par le bord de l'image (90 % des manqués et 75 % des faux positifs
    du jeu de test Zenodo y sont)."""
    modele = modele or td.charger_modele()
    img = np.asarray(img, dtype=np.float32)
    bruts = []
    for cx, cy, w, h, s in td.predire(modele, img, seuil):
        th = angle_local(img, cx, cy, w, h)
        bruts.append((cx, cy, w, h, s, th, *rectangle(w, h, th)))
    surs = [max(a, b) / min(a, b) for *_, a, b, inc in bruts if not inc]
    r = float(np.median(surs)) if len(surs) >= 3 else None
    out = []
    for cx, cy, w, h, s, th, a, b, incertain in bruts:
        if incertain and r:
            (a, b), incertain = rectangle_proportions(w, h, th, r), False
        if b > a:
            a, b, th = b, a, th + math.pi / 2
        u, v = np.array([math.cos(th), math.sin(th)]), np.array([-math.sin(th), math.cos(th)])
        coins = [(np.array([cx, cy]) + i * a / 2 * u + j * b / 2 * v).round(1).tolist()
                 for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        out.append({"cx": round(float(cx), 1), "cy": round(float(cy), 1),
                    "angle_deg": round(math.degrees(th) % 180, 1), "longueur": round(a, 1), "largeur": round(b, 1),
                    "coins": coins, "score": round(float(s), 3), "incertain": incertain,
                    "complet": all(1 <= x <= img.shape[1] - 2 and 1 <= y <= img.shape[0] - 2 for x, y in coins)})
    return out


def decouper(t, m, marge=MARGE, pas=1.0):
    """Matrice du module `m` (rectangle incliné), rééchantillonnée sur sa grille (longueur en lignes : portrait),
    sans `marge` de chaque côté."""
    th = math.radians(m["angle_deg"])
    a, b = m["longueur"] * (1 - 2 * marge), m["largeur"] * (1 - 2 * marge)
    na, nb = max(2, int(round(a / pas))), max(2, int(round(b / pas)))
    i, j = np.meshgrid(np.linspace(-a / 2, a / 2, na), np.linspace(-b / 2, b / 2, nb), indexing="ij")
    x = m["cx"] + i * math.cos(th) - j * math.sin(th)
    y = m["cy"] + i * math.sin(th) + j * math.cos(th)
    return ndimage.map_coordinates(np.asarray(t, dtype=np.float64), [y, x], order=1, mode="nearest")


def analyser(t, modele=None, seuil_k=anomalies.SEUIL_K):
    """Matrice de températures d'une photo → modules détectés, chacun avec sa forme d'anomalie ; `module_chaud`
    remplace « sain » pour un module plus chaud que la médiane des autres de la photo. Les modules coupés par le
    bord de l'image sont écartés (incomplets : ils seront vus entiers sur une photo voisine du vol)."""
    mods = [m for m in detecter(t, modele) if m["complet"]]
    moyennes = []
    for m in mods:
        z = decouper(t, m)
        m.update(anomalies.decrire(z, seuil_k))
        m["t_moyenne"] = round(float(np.mean(z)), 2)
        m["t_max"] = round(float(np.max(z)), 2)
        moyennes.append(m["t_moyenne"])
    for i, m in enumerate(mods):                          # écart de la moyenne avec les autres modules de la photo
        autres = np.delete(np.asarray(moyennes), i)
        m["dT_voisins"] = round(float(m["t_moyenne"] - np.median(autres)), 2) if len(autres) >= 2 else None
    for i in anomalies.modules_chauds(moyennes, seuil_k):
        if mods[i]["forme"] == "sain":
            mods[i].update(forme="module_chaud", libelle=anomalies.FORMES["module_chaud"])
    return mods
