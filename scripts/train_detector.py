"""Détecteur de modules PV dans une image thermique (étape 3, option « maison » du 06/11/2026).

Pourquoi ce réseau : Ultralytics YOLO est sous AGPL (licence payante revendiquée même en usage interne) ; ici,
PyTorch seul (BSD), entraîné de zéro, aucun poids tiers.

Données : Zenodo 16420123 (« Thermal PV Panel Detection and Fault Detection Dataset for UAV-Based Inspection »,
CC BY 4.0, Mavic 3T, Sindos ; 235 / 83 / 35 images 640 × 512, 26 678 modules), téléchargé hors dépôt :
    ~/donnees_externes/zenodo_pv_detection/extrait/Thermal PV Panel Detection Dataset for UAV Inspection/
Ses annotations sont des cadres **droits** alors que les rangées sont inclinées : un cadre déborde sur les
voisins et le sol. D'où une détection par **centres** (« Objects as Points », Zhou et al. 2019) : le centre du
cadre droit d'un rectangle incliné est son vrai centre. Le réseau donne une carte de chaleur des centres et la
taille du cadre droit (pas de 4 px) ; `detecteur.py` en tire l'inclinaison (bords de l'image) et le rectangle
incliné du module.

Entrée : image en niveaux de gris standardisée (moyenne 0, écart type 1), pour accepter plus tard une matrice
de températures. Augmentations : découpes 256 × 256, retournements, rotations de 90°, inversion des contrastes
(modules plus froids que le sol le matin), contraste ±.

    .venv/bin/python scripts/train_detector.py [--donnees <dossier du jeu>] [--epochs 60]
    .venv/bin/python scripts/train_detector.py --eval-only models/detector.pt
Un point de reprise est écrit toutes les 5 époques (output/detector_reprise.pt) : relancer la même commande
reprend là où l'entraînement s'est arrêté. Calcul prévu sur DELLODM (8 cœurs), pas sur AEX.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
DONNEES = Path.home() / "donnees_externes" / "zenodo_pv_detection" / "extrait" / \
    "Thermal PV Panel Detection Dataset for UAV Inspection"
MODELES, SORTIE = RACINE / "models", RACINE / "output"
PAS = 4               # sortie au quart de la résolution
DECOUPE = 256
SEUIL_CENTRE = 0.3


def standardiser(img):
    img = img.astype(np.float32)
    return (img - img.mean()) / max(float(img.std()), 1e-6)


def charger(dossier, part):
    """[(image float32 standardisée (H, W), cadres (N, 4) cx, cy, w, h en px)]."""
    out = []
    for f in sorted((Path(dossier) / part / "images").glob("*.jpg")):
        img = np.asarray(Image.open(f).convert("L"), dtype=np.float32)
        h, w = img.shape
        lab = Path(dossier) / part / "labels" / (f.stem + ".txt")
        b = np.loadtxt(lab, ndmin=2)[:, 1:5] if lab.is_file() and lab.stat().st_size else np.zeros((0, 4))
        b = b * np.array([w, h, w, h])
        out.append((standardiser(img), b.astype(np.float32)))
    return out


# --------------------------------------------------------------------------------------------- cibles

def rayon(w, h, iou=0.7):
    """Rayon gaussien de CenterNet (Law & Deng 2018) : décalage du centre gardant un IoU ≥ 0,7."""
    a1, b1, c1 = 1, w + h, w * h * (1 - iou) / (1 + iou)
    r1 = (b1 + math.sqrt(b1 ** 2 - 4 * a1 * c1)) / 2
    a2, b2, c2 = 4, 2 * (w + h), (1 - iou) * w * h
    r2 = (b2 + math.sqrt(b2 ** 2 - 4 * a2 * c2)) / 2
    a3, b3, c3 = 4 * iou, -2 * iou * (w + h), (iou - 1) * w * h
    r3 = (b3 + math.sqrt(b3 ** 2 - 4 * a3 * c3)) / 2
    return max(0.0, min(r1, r2, r3))


def cibles(cadres, h, w):
    """Carte de chaleur (h/4, w/4), tailles (2, h/4, w/4) en px / 16 et masque des centres."""
    H, W = h // PAS, w // PAS
    chaleur = np.zeros((H, W), np.float32)
    taille = np.zeros((2, H, W), np.float32)
    masque = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    for cx, cy, bw, bh in cadres:
        x, y = cx / PAS, cy / PAS
        ix, iy = int(x), int(y)
        if not (0 <= ix < W and 0 <= iy < H):
            continue
        r = max(0, int(rayon(bw / PAS, bh / PAS)))
        s = (2 * r + 1) / 6
        g = np.exp(-((xx - ix) ** 2 + (yy - iy) ** 2) / (2 * s * s))
        np.maximum(chaleur, g, out=chaleur)
        taille[:, iy, ix] = bw / 16, bh / 16
        masque[iy, ix] = 1
    return chaleur, taille, masque


def augmenter(img, cadres, rng):
    """Découpe carrée, retournements, rotation de 90°, inversion, contraste."""
    h, w = img.shape
    y0, x0 = rng.integers(0, h - DECOUPE + 1), rng.integers(0, w - DECOUPE + 1)
    img = img[y0:y0 + DECOUPE, x0:x0 + DECOUPE].copy()
    b = cadres.copy()
    b[:, 0] -= x0
    b[:, 1] -= y0
    b = b[(b[:, 0] >= 0) & (b[:, 0] < DECOUPE) & (b[:, 1] >= 0) & (b[:, 1] < DECOUPE)]
    if rng.random() < 0.5:
        img, b[:, 0] = img[:, ::-1], DECOUPE - 1 - b[:, 0]
    if rng.random() < 0.5:
        img, b[:, 1] = img[::-1], DECOUPE - 1 - b[:, 1]
    if rng.random() < 0.5:                                  # transposition (avec les retournements : 8 cas)
        img, b = img.T, b[:, [1, 0, 3, 2]]
    if rng.random() < 0.3:
        img = -img
    img = img * rng.uniform(0.7, 1.3) + rng.normal(0, 0.1)
    return np.ascontiguousarray(img), b


# --------------------------------------------------------------------------------------------- réseau

def bloc(e, s):
    return nn.Sequential(nn.Conv2d(e, s, 3, padding=1, bias=False), nn.BatchNorm2d(s), nn.ReLU(inplace=True),
                         nn.Conv2d(s, s, 3, padding=1, bias=False), nn.BatchNorm2d(s), nn.ReLU(inplace=True))


class ReseauCentres(nn.Module):
    """Petit U-Net (pas 1 → 16 → retour à 4) ; têtes : chaleur des centres (1) et taille du cadre droit (2)."""

    def __init__(self, c=24):
        super().__init__()
        self.e1, self.e2, self.e3, self.e4, self.e5 = bloc(1, c), bloc(c, 2 * c), bloc(2 * c, 4 * c), \
            bloc(4 * c, 6 * c), bloc(6 * c, 8 * c)
        self.d4, self.d3 = bloc(8 * c + 6 * c, 6 * c), bloc(6 * c + 4 * c, 4 * c)
        self.chaleur = nn.Sequential(nn.Conv2d(4 * c, 4 * c, 3, padding=1), nn.ReLU(inplace=True),
                                     nn.Conv2d(4 * c, 1, 1))
        self.taille = nn.Sequential(nn.Conv2d(4 * c, 4 * c, 3, padding=1), nn.ReLU(inplace=True),
                                    nn.Conv2d(4 * c, 2, 1))
        self.chaleur[-1].bias.data.fill_(-2.19)                 # a priori 0,1 (CenterNet)

    def forward(self, x):
        x1 = self.e1(x)                                         # 1
        x2 = self.e2(F.max_pool2d(x1, 2))                       # 1/2
        x3 = self.e3(F.max_pool2d(x2, 2))                       # 1/4
        x4 = self.e4(F.max_pool2d(x3, 2))                       # 1/8
        x5 = self.e5(F.max_pool2d(x4, 2))                       # 1/16
        y = self.d4(torch.cat([F.interpolate(x5, scale_factor=2), x4], 1))
        y = self.d3(torch.cat([F.interpolate(y, scale_factor=2), x3], 1))
        return self.chaleur(y), self.taille(y)


def perte_focale(logits, cible, a=2, b=4):
    p = torch.sigmoid(logits).clamp(1e-4, 1 - 1e-4)
    pos = cible.eq(1).float()
    l_pos = -((1 - p) ** a) * torch.log(p) * pos
    l_neg = -((1 - cible) ** b) * (p ** a) * torch.log(1 - p) * (1 - pos)
    return (l_pos.sum() + l_neg.sum()) / pos.sum().clamp(min=1)


# --------------------------------------------------------------------------------------------- décodage

def decoder(chaleur_logits, taille, seuil=SEUIL_CENTRE, max_n=2000):
    """Sorties du réseau (une image) → tableau (N, 5) : cx, cy, w, h (px de l'image), score."""
    p = torch.sigmoid(chaleur_logits)[0, 0]
    pic = F.max_pool2d(p[None, None], 3, 1, 1)[0, 0]
    garde = (p == pic) & (p >= seuil)
    ys, xs = torch.nonzero(garde, as_tuple=True)
    s = p[ys, xs]
    if len(s) > max_n:
        s, i = s.topk(max_n)
        ys, xs = ys[i], xs[i]
    w, h = taille[0, 0, ys, xs] * 16, taille[0, 1, ys, xs] * 16
    return torch.stack([(xs.float() + 0.5) * PAS, (ys.float() + 0.5) * PAS, w, h, s], 1).numpy()


def predire(modele, img, seuil=SEUIL_CENTRE):
    """Image (H, W) quelconque (niveaux de gris ou températures) → détections (N, 5)."""
    x = standardiser(np.asarray(img, dtype=np.float32))
    h, w = x.shape
    ph, pw = (-h) % 16, (-w) % 16
    t = torch.from_numpy(np.pad(x, ((0, ph), (0, pw)), mode="reflect"))[None, None]
    modele.eval()
    with torch.no_grad():
        c, s = modele(t)
    d = decoder(c, s, seuil)
    return d[(d[:, 0] < w) & (d[:, 1] < h)]


def iou_cadres(a, b):
    """IoU entre cadres (N, 4) et (M, 4) cx, cy, w, h → (N, M)."""
    a1, a2 = a[:, None, :2] - a[:, None, 2:4] / 2, a[:, None, :2] + a[:, None, 2:4] / 2
    b1, b2 = b[None, :, :2] - b[None, :, 2:4] / 2, b[None, :, :2] + b[None, :, 2:4] / 2
    inter = np.clip(np.minimum(a2, b2) - np.maximum(a1, b1), 0, None).prod(2)
    return inter / (a[:, None, 2] * a[:, None, 3] + b[None, :, 2] * b[None, :, 3] - inter + 1e-9)


def evaluer(modele, jeu, seuil=SEUIL_CENTRE, iou_min=0.5):
    """Appariement glouton par score, IoU ≥ 0,5 → précision, rappel, F1 ; erreur médiane de centre (px)."""
    vp = fp = fn = 0
    ecarts = []
    for img, gt in jeu:
        d = predire(modele, img, seuil)
        d = d[np.argsort(-d[:, 4])]
        pris = np.zeros(len(gt), bool)
        m = iou_cadres(d[:, :4], gt) if len(d) and len(gt) else np.zeros((len(d), len(gt)))
        for i in range(len(d)):
            j = int(np.argmax(np.where(pris, -1, m[i]))) if len(gt) else -1
            if j >= 0 and not pris[j] and m[i, j] >= iou_min:
                pris[j] = True
                vp += 1
                ecarts.append(float(np.hypot(*(d[i, :2] - gt[j, :2]))))
            else:
                fp += 1
        fn += int((~pris).sum())
    p, r = vp / max(vp + fp, 1), vp / max(vp + fn, 1)
    return {"precision": round(p, 4), "rappel": round(r, 4), "f1": round(2 * p * r / max(p + r, 1e-9), 4),
            "vrais": vp, "faux_positifs": fp, "manques": fn,
            "ecart_centre_px": round(float(np.median(ecarts)), 2) if ecarts else None}


# --------------------------------------------------------------------------------------------- entraînement

def entrainer(dossier, epochs, lot=8, graine=0):
    torch.manual_seed(graine)
    rng = np.random.default_rng(graine)
    train, val = charger(dossier, "train"), charger(dossier, "val")
    modele = ReseauCentres()
    opt = torch.optim.AdamW(modele.parameters(), lr=2e-3, weight_decay=1e-4)
    pas_par_epoch = 4 * len(train) // lot                    # 4 découpes par image et par époque
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 2e-3, total_steps=epochs * pas_par_epoch)
    meilleur, etat, hist, debut = -1.0, None, [], 1
    reprise = SORTIE / "detector_reprise.pt"
    if reprise.is_file():
        r = torch.load(reprise, weights_only=True)
        modele.load_state_dict(r["modele"])
        opt.load_state_dict(r["opt"])
        sched.load_state_dict(r["sched"])
        meilleur, etat, hist, debut = r["meilleur"], r["etat"], r["historique"], r["epoch"] + 1
        rng = np.random.default_rng(graine + debut)
        print(f"reprise après l'époque {r['epoch']}", flush=True)
    SORTIE.mkdir(exist_ok=True)
    for ep in range(debut, epochs + 1):
        modele.train()
        t0, cumul = time.time(), 0.0
        for _ in range(pas_par_epoch):
            xs, cs, ts, ms = [], [], [], []
            for i in rng.integers(0, len(train), lot):
                img, b = augmenter(*train[i], rng)
                c, t, m = cibles(b, DECOUPE, DECOUPE)
                xs.append(img)
                cs.append(c)
                ts.append(t)
                ms.append(m)
            x = torch.from_numpy(np.stack(xs))[:, None]
            c, t, m = (torch.from_numpy(np.stack(v)) for v in (cs, ts, ms))
            pc, pt = modele(x)
            l_t = (F.l1_loss(pt, t, reduction="none") * m[:, None]).sum() / m.sum().clamp(min=1)
            perte = perte_focale(pc[:, 0], c) + 0.1 * l_t
            opt.zero_grad()
            perte.backward()
            opt.step()
            sched.step()
            cumul += perte.item()
        ligne = {"epoch": ep, "perte": round(cumul / pas_par_epoch, 4), "duree_s": round(time.time() - t0, 1)}
        if ep % 5 == 0 or ep == epochs:
            ligne["val"] = evaluer(modele, val)
            if ligne["val"]["f1"] > meilleur:
                meilleur, etat = ligne["val"]["f1"], {k: v.clone() for k, v in modele.state_dict().items()}
        hist.append(ligne)
        print(json.dumps(ligne, ensure_ascii=False), flush=True)
        if ep % 5 == 0:                                       # reprise possible après un arrêt
            torch.save({"epoch": ep, "modele": modele.state_dict(), "opt": opt.state_dict(),
                        "sched": sched.state_dict(), "meilleur": meilleur, "etat": etat, "historique": hist},
                       reprise)
    MODELES.mkdir(exist_ok=True)
    chemin = MODELES / "detector.pt"
    torch.save({"etat": etat, "canaux": 24, "pas": PAS, "seuil": SEUIL_CENTRE, "historique": hist,
                "entree": "niveaux de gris ou températures, standardisés par image",
                "donnees": "Zenodo 16420123 (CC BY 4.0)"}, chemin)
    reprise.unlink(missing_ok=True)
    return chemin


def charger_modele(chemin=MODELES / "detector.pt"):
    ck = torch.load(chemin, weights_only=True)
    m = ReseauCentres(ck.get("canaux", 24))
    m.load_state_dict(ck["etat"])
    m.eval()
    return m


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--donnees", type=Path, default=DONNEES)
    a.add_argument("--epochs", type=int, default=60)
    a.add_argument("--eval-only", type=Path)
    o = a.parse_args()
    torch.set_num_threads(os.cpu_count() or 4)
    chemin = o.eval_only or entrainer(o.donnees, o.epochs)
    modele = charger_modele(chemin)
    res = {p: evaluer(modele, charger(o.donnees, p)) for p in ("val", "test")}
    SORTIE.mkdir(exist_ok=True)
    (SORTIE / "detector_report.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
