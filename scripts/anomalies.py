"""Anomalies d'un module à partir de sa matrice de températures (°C).

- `decrire` (décision du rapport, option A du 06/11/2026) : seuil physique puis **forme** de l'anomalie
  (point chaud, cellules chaudes, diode possible, sous-chaîne chaude), pas sa cause ;
- `modules_chauds` : module entier plus chaud que ses voisins (hors service) ;
- `classer` : avis du classifieur entraîné, derrière le même seuil (informatif).

Le classifieur (models/classifier.pt) voit des vignettes standardisées, donc sans amplitude : sur le jeu DTU
(06/11/2026, REPRISE.md), il signalait 68 à 86 % des modules uniformes (écart < 2 K) comme défectueux. On ne le
consulte donc que si l'écart interne du module atteint `SEUIL_K` :

    écart interne = centile 99,5 − médiane des températures du module

(le centile 99,5 ignore quelques pixels isolés, mais garde une cellule chaude : 1/60 du module ≈ 1,7 %).
En dessous du seuil : `no_anomaly`, motif « écart < seuil » ; les défauts qui ne chauffent pas (fissures, PID,
verre fissuré, ≤ 2 K selon DTU) ne sont pas visibles en thermographie et ne sont pas signalés.

Le module entièrement chaud a un écart interne faible : il se juge contre ses voisins (`modules_chauds`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_classifier import (CLASSES, HAUTEUR, LARGEUR, MODELES, ReseauModule, probas,  # noqa: E402
                              regrouper, standardiser)

SEUIL_K = 3.0          # validé sur DTU (fissures, PID, verre : ≤ 3 % au-dessus) ; à confirmer sur de vrais vols
CENTILE = 99.5


def ecart_interne(t):
    """Centile 99,5 − médiane (K) des pixels finis d'un module."""
    ok = np.asarray(t, dtype=np.float64)
    ok = ok[np.isfinite(ok)]
    return float(np.percentile(ok, CENTILE) - np.median(ok))


def vignette(t):
    """Matrice d'un module en portrait (h > l) → 40 × 24 par moyenne de blocs ; un module en paysage est tourné."""
    t = np.asarray(t, dtype=np.float32)
    if t.shape[1] > t.shape[0]:
        t = np.rot90(t)
    t = np.where(np.isfinite(t), t, np.nanmedian(t))
    return np.asarray(Image.fromarray(np.ascontiguousarray(t), mode="F").resize((LARGEUR, HAUTEUR), Image.BOX))


def charger_modele(chemin=MODELES / "classifier.pt"):
    ck = torch.load(chemin, weights_only=True)
    modele = ReseauModule(len(ck["fines"]))
    modele.load_state_dict(ck["etat"])
    modele.eval()
    return modele, ck["fines"]


def classer(modules, modele=None, seuil=SEUIL_K):
    """Liste de matrices de modules → liste de {classe, confiance, ecart_K, motif, classe_ia, classe_fine}.
    `modele` : résultat de `charger_modele()` (chargé à chaque appel sinon).
    `classe_ia` : avis du classifieur même sous le seuil (pour comparaison), `classe` : décision finale."""
    modele, fines = modele or charger_modele()
    if not modules:
        return []
    ecarts = [ecart_interne(t) for t in modules]
    x = torch.from_numpy(standardiser(np.stack([vignette(t) for t in modules]))).unsqueeze(1)
    pf = probas(modele, x)
    pg = regrouper(pf)
    out = []
    for e, a, b in zip(ecarts, pg, pf):
        ia = CLASSES[int(a.argmax())]
        r = {"ecart_K": round(e, 2), "classe_ia": ia, "confiance_ia": round(float(a.max()), 3),
             "classe_fine": fines[int(b.argmax())]}
        if e < seuil:
            r.update(classe="no_anomaly", confiance=None, motif=f"écart {e:.1f} K < {seuil:g} K")
        else:
            r.update(classe=ia, confiance=r["confiance_ia"], motif="classifieur")
        out.append(r)
    return out


# --------------------------------------------------------------------------------------------- forme (option A)
# Décidé le 06/11/2026 : en infrarouge seul, une diode court-circuitée et une salissure donnent toutes deux des
# cellules chaudes (jeu DTU) ; le rapport décrit donc la **forme** de l'anomalie, la cause est à confirmer
# (photo couleur, test de diode, courbe I-V). Suppose un module en trois sous-chaînes dans le sens de la largeur
# (portrait), cas de la plupart des modules 60, 72, 120 et 144 cellules.

FORMES = {
    "sain": "aucune anomalie visible en thermographie",
    "point_chaud": "point chaud (une cellule ou moins)",
    "cellules_chaudes": "cellules chaudes multiples",
    "diode_possible": "cellules chaudes multiples dans une même sous-chaîne : diode possible, à vérifier",
    "sous_chaine_chaude": "sous-chaîne entière chaude et uniforme : diode activée",
    "module_chaud": "module entier plus chaud que ses voisins : module hors service",
}
AIRE_CELLULE = 0.025   # part du module : une cellule fait 1/60 (1,7 %) à 1/72 ; au-delà, plusieurs cellules
PART_TIERS = 0.9       # part de l'aire chaude dans un seul tiers pour « même sous-chaîne »
COUVERTURE_TIERS = 0.6  # part d'un tiers au-dessus du seuil pour « sous-chaîne entière »


def _portrait(t):
    t = np.asarray(t, dtype=np.float64)
    t = np.rot90(t) if t.shape[1] > t.shape[0] else t
    return np.where(np.isfinite(t), t, np.nanmedian(t))


def decrire(t, seuil=SEUIL_K):
    """Matrice d'un module (°C) → {forme, libelle, ecart_K, aire_chaude, tiers (part de l'aire chaude par tiers),
    zones}. Ne juge que l'intérieur du module : « module_chaud » vient de `modules_chauds`."""
    from scipy import ndimage

    t = _portrait(t)
    med = float(np.median(t))
    ecart = float(np.percentile(t, CENTILE) - med)
    res = {"ecart_K": round(ecart, 2), "aire_chaude": 0.0, "tiers": None, "zones": 0}
    if ecart < seuil:
        return dict(res, forme="sain", libelle=FORMES["sain"])
    l = t.shape[1]
    bornes = [0, round(l / 3), round(2 * l / 3), l]
    tiers = [t[:, bornes[i]:bornes[i + 1]] for i in range(3)]
    # sous-chaîne entière : un tiers majoritairement au-dessus des deux autres + seuil
    for i, ti in enumerate(tiers):
        autres = np.concatenate([tiers[j].ravel() for j in range(3) if j != i])
        ref = float(np.median(autres))
        if np.mean(ti > ref + seuil) >= COUVERTURE_TIERS:
            return dict(res, forme="sous_chaine_chaude", libelle=FORMES["sous_chaine_chaude"],
                        aire_chaude=round(float(np.mean(t > ref + seuil)), 3),
                        tiers=[1.0 if j == i else 0.0 for j in range(3)], zones=1)
    chaud = t > med + max(seuil, ecart / 3)
    etiq, n = ndimage.label(chaud)
    tailles = ndimage.sum(chaud, etiq, range(1, n + 1)) if n else np.array([])
    aire = float(chaud.mean())
    par_tiers = [float(chaud[:, bornes[i]:bornes[i + 1]].sum()) for i in range(3)]
    parts = [round(x / max(sum(par_tiers), 1), 2) for x in par_tiers]
    zones = int((tailles >= 0.002 * t.size).sum()) or 1
    res.update(aire_chaude=round(aire, 3), tiers=parts, zones=zones)
    if aire <= AIRE_CELLULE and zones == 1:
        forme = "point_chaud"
    elif max(parts) >= PART_TIERS:
        forme = "diode_possible"
    else:
        forme = "cellules_chaudes"
    return dict(res, forme=forme, libelle=FORMES[forme])


def modules_chauds(moyennes, seuil=SEUIL_K):
    """Moyennes (°C) des modules d'une même photo ou rangée → indices des modules plus chauds que la médiane des
    autres de `seuil` K au moins (module hors service). Il faut au moins 3 modules. Non validé sur données réelles
    (DTU n'a que des modules isolés)."""
    m = np.asarray(moyennes, dtype=np.float64)
    if m.size < 3:
        return []
    return [i for i in range(m.size) if m[i] - np.median(np.delete(m, i)) >= seuil]
