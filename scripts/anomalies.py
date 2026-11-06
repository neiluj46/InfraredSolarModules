"""Classement d'un module à partir de sa matrice de températures (°C) : seuil physique, puis classifieur.

Le classifieur (models/classifier.pt) voit des vignettes standardisées, donc sans amplitude : sur le jeu DTU
(06/11/2026, REPRISE.md), il signalait 68 à 86 % des modules uniformes (écart < 2 K) comme défectueux. On ne le
consulte donc que si l'écart interne du module atteint `SEUIL_K` :

    écart interne = centile 99,5 − médiane des températures du module

(le centile 99,5 ignore quelques pixels isolés, mais garde une cellule chaude : 1/60 du module ≈ 1,7 %).
En dessous du seuil : `no_anomaly`, motif « écart < seuil » ; les défauts qui ne chauffent pas (fissures, PID,
verre fissuré, ≤ 2 K selon DTU) ne sont pas visibles en thermographie et ne sont pas signalés.

Ne couvre pas le module entièrement chaud (`offline_module`) : son écart interne est faible, il se juge contre
les modules voisins (étape 4, règle à venir).
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
