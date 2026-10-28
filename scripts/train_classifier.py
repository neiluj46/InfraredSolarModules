"""Classifieur de l'état d'un module photovoltaïque (vignette infrarouge).

Deuxième étage du pipeline : un détecteur isole chaque module dans l'image thermique,
ce classifieur dit ce qu'il a. Entraîné sur InfraredSolarModules (Raptor Maps, 20 000
vignettes 24 × 40 px, 12 classes). Le réseau apprend les 12 classes d'origine ; les
probabilités sont ensuite additionnées vers les classes du projet :

    no_anomaly      No-Anomaly
    hotspot         Cell, Cell-Multi, Hot-Spot, Hot-Spot-Multi
    bypass_diode    Diode, Diode-Multi
    offline_module  Offline-Module (module entier chaud ; plusieurs modules voisins
                    d'une même rangée = string_failure, déduit après classement)
    obstruction     Shadowing, Vegetation, Soiling (pas un défaut du module, mais à
                    distinguer pour éviter les fausses alertes)
    cracking        Cracking

Aucune base ouverte n'étiquette le PID : il sera traité par une règle plus tard.

Entrée du réseau : vignette en portrait, 40 × 24 px, standardisée par image
((x − moyenne) / écart type), pour accepter plus tard une découpe de la matrice de
températures d'un R-JPEG au lieu d'une image 8 bits.

Premier essai (YOLO11n-cls d'Ultralytics, 64 px) abandonné : son recadrage aléatoire
(jusqu'à 50 % de l'image) et RandAugment coupent le point chaud ou le tiers de module
d'une diode ; exactitude de validation instable entre 30 et 64 % après 20 époques.

Utilisation :
    .venv/bin/python scripts/train_classifier.py
    .venv/bin/python scripts/train_classifier.py --epochs 60
    .venv/bin/python scripts/train_classifier.py --eval-only models/classifier.pt
"""
from __future__ import annotations

import argparse
import io
import json
import random
import time
import zipfile
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
ARCHIVE = RACINE / "2020-02-14_InfraredSolarModules.zip"
MODELES = RACINE / "models"
SORTIE = RACINE / "output"

REGROUPEMENT = {
    "No-Anomaly": "no_anomaly",
    "Cell": "hotspot",
    "Cell-Multi": "hotspot",
    "Hot-Spot": "hotspot",
    "Hot-Spot-Multi": "hotspot",
    "Diode": "bypass_diode",
    "Diode-Multi": "bypass_diode",
    "Offline-Module": "offline_module",
    "Shadowing": "obstruction",
    "Vegetation": "obstruction",
    "Soiling": "obstruction",
    "Cracking": "cracking",
}
FINES = sorted(REGROUPEMENT)
CLASSES = sorted(set(REGROUPEMENT.values()))
HAUTEUR, LARGEUR = 40, 24
PARTS = {"val": 0.1, "test": 0.1}


def standardiser(x: np.ndarray) -> np.ndarray:
    """(N, H, W) → même forme, chaque vignette ramenée à moyenne 0, écart type 1."""
    x = x.astype(np.float32)
    m = x.mean(axis=(1, 2), keepdims=True)
    s = x.std(axis=(1, 2), keepdims=True)
    return (x - m) / np.maximum(s, 1e-6)


def charger(graine: int = 0) -> dict:
    """Lit l'archive et découpe en train / val / test, stratifié sur la classe fine."""
    with zipfile.ZipFile(ARCHIVE) as z:
        meta = json.loads(z.read("InfraredSolarModules/module_metadata.json"))
        par_classe: dict[str, list[str]] = {}
        for num, m in meta.items():
            par_classe.setdefault(m["anomaly_class"], []).append(num)
        rng = random.Random(graine)
        parts = {"train": [], "val": [], "test": []}
        for classe in FINES:
            nums = sorted(par_classe[classe], key=int)
            rng.shuffle(nums)
            n_val = round(len(nums) * PARTS["val"])
            n_test = round(len(nums) * PARTS["test"])
            parts["val"] += [(n, classe) for n in nums[:n_val]]
            parts["test"] += [(n, classe) for n in nums[n_val:n_val + n_test]]
            parts["train"] += [(n, classe) for n in nums[n_val + n_test:]]
        donnees = {}
        for part, liste in parts.items():
            images = np.stack([
                np.asarray(Image.open(io.BytesIO(z.read(f"InfraredSolarModules/{meta[n]['image_filepath']}"))).convert("L"))
                for n, _ in liste
            ])
            assert images.shape[1:] == (HAUTEUR, LARGEUR), images.shape
            donnees[part] = (
                torch.from_numpy(standardiser(images)).unsqueeze(1),
                torch.tensor([FINES.index(c) for _, c in liste]),
            )
    return donnees


class ReseauModule(nn.Module):
    """Petit CNN pour vignettes 40 × 24. La couche finale garde la position spatiale
    (aplatissement plutôt que moyenne globale) : une diode de dérivation se lit à la
    position du tiers chaud dans le module."""

    def __init__(self, n_classes: int):
        super().__init__()

        def bloc(e, s):
            return nn.Sequential(
                nn.Conv2d(e, s, 3, padding=1, bias=False), nn.BatchNorm2d(s), nn.ReLU(inplace=True),
                nn.Conv2d(s, s, 3, padding=1, bias=False), nn.BatchNorm2d(s), nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
            )

        self.extraction = nn.Sequential(bloc(1, 32), bloc(32, 64), bloc(64, 128))  # → 128 × 5 × 3
        self.tete = nn.Sequential(
            nn.Flatten(), nn.Dropout(0.3),
            nn.Linear(128 * 5 * 3, 256), nn.ReLU(inplace=True), nn.Dropout(0.3),
            nn.Linear(256, n_classes),
        )

    def forward(self, x):
        return self.tete(self.extraction(x))


def augmenter(x: torch.Tensor) -> torch.Tensor:
    """Retournements (un module retourné reste valide) et décalage de ±2 px.
    Pas de recadrage ni de rotation à 90° : la vignette est toujours en portrait."""
    n = x.shape[0]
    h = torch.rand(n) < 0.5
    v = torch.rand(n) < 0.5
    x = x.clone()
    x[h] = x[h].flip(3)
    x[v] = x[v].flip(2)
    dy, dx = random.randint(-2, 2), random.randint(-2, 2)
    x = F.pad(x, (2, 2, 2, 2), mode="replicate")
    return x[:, :, 2 + dy:2 + dy + HAUTEUR, 2 + dx:2 + dx + LARGEUR]


def probas(modele: nn.Module, x: torch.Tensor, lot: int = 1024) -> torch.Tensor:
    modele.eval()
    with torch.no_grad():
        return torch.cat([F.softmax(modele(x[i:i + lot]), 1) for i in range(0, len(x), lot)])


def regrouper(p: torch.Tensor) -> torch.Tensor:
    """Probabilités fines (N, 12) → classes du projet (N, 6)."""
    g = torch.zeros(p.shape[0], len(CLASSES))
    for i, f in enumerate(FINES):
        g[:, CLASSES.index(REGROUPEMENT[f])] += p[:, i]
    return g


def f1_macro(vrai: np.ndarray, predit: np.ndarray, n: int) -> float:
    f1 = []
    for c in range(n):
        tp = np.sum((predit == c) & (vrai == c))
        p = tp / max(np.sum(predit == c), 1)
        r = tp / max(np.sum(vrai == c), 1)
        f1.append(2 * p * r / max(p + r, 1e-9))
    return float(np.mean(f1))


def entrainer(donnees: dict, epochs: int, lot: int, graine: int = 0) -> Path:
    torch.manual_seed(graine)
    random.seed(graine)
    x, y = donnees["train"]
    xv, yv = donnees["val"]
    # Poids de classe en racine de l'inverse de la fréquence : les classes rares
    # (Diode-Multi 175, Hot-Spot 251) comptent sans écraser les modules sains.
    freq = torch.bincount(y, minlength=len(FINES)).float()
    poids = (freq.sum() / freq).sqrt()
    poids = poids / poids.mean()

    modele = ReseauModule(len(FINES))
    opt = torch.optim.AdamW(modele.parameters(), lr=2e-3, weight_decay=1e-3)
    pas = epochs * ((len(x) + lot - 1) // lot)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-3, total_steps=pas)
    critere = nn.CrossEntropyLoss(weight=poids, label_smoothing=0.05)

    meilleur, etat, historique = -1.0, None, []
    for ep in range(1, epochs + 1):
        t0 = time.time()
        modele.train()
        ordre = torch.randperm(len(x))
        perte = 0.0
        for i in range(0, len(x), lot):
            idx = ordre[i:i + lot]
            opt.zero_grad()
            l = critere(modele(augmenter(x[idx])), y[idx])
            l.backward()
            opt.step()
            sched.step()
            perte += l.item() * len(idx)
        pv = probas(modele, xv)
        fin = f1_macro(yv.numpy(), pv.argmax(1).numpy(), len(FINES))
        yg = np.array([CLASSES.index(REGROUPEMENT[FINES[c]]) for c in yv])
        grp = f1_macro(yg, regrouper(pv).argmax(1).numpy(), len(CLASSES))
        historique.append({"epoque": ep, "perte": round(perte / len(x), 4), "f1_val_12": round(fin, 4), "f1_val_6": round(grp, 4)})
        print(f"époque {ep:3d}  perte {perte / len(x):.3f}  F1 val 12 classes {fin:.3f}  6 classes {grp:.3f}  ({time.time() - t0:.0f} s)", flush=True)
        if grp > meilleur:
            meilleur, etat = grp, {k: v.clone() for k, v in modele.state_dict().items()}

    MODELES.mkdir(exist_ok=True)
    cible = MODELES / "classifier.pt"
    torch.save({
        "etat": etat,
        "fines": FINES,
        "regroupement": REGROUPEMENT,
        "classes": CLASSES,
        "entree": {"hauteur": HAUTEUR, "largeur": LARGEUR, "normalisation": "standardisation par vignette"},
        "historique": historique,
    }, cible)
    return cible


def evaluer(poids: Path, donnees: dict) -> dict:
    ck = torch.load(poids, weights_only=True)
    modele = ReseauModule(len(ck["fines"]))
    modele.load_state_dict(ck["etat"])
    x, y = donnees["test"]
    p = probas(modele, x)
    vrai_f, pred_f = y.numpy(), p.argmax(1).numpy()
    vrai = np.array([CLASSES.index(REGROUPEMENT[FINES[c]]) for c in vrai_f])
    pred = regrouper(p).argmax(1).numpy()

    def metriques(v, q, noms):
        res = {}
        for c, nom in enumerate(noms):
            tp = int(np.sum((q == c) & (v == c)))
            pr = tp / max(int(np.sum(q == c)), 1)
            rc = tp / max(int(np.sum(v == c)), 1)
            res[nom] = {"n": int(np.sum(v == c)), "precision": round(pr, 3), "recall": round(rc, 3),
                        "f1-score": round(2 * pr * rc / max(pr + rc, 1e-9), 3)}
        return res

    sain = CLASSES.index("no_anomaly")
    anomalies, sains = vrai != sain, vrai == sain
    matrice = [[int(np.sum((vrai == i) & (pred == j))) for j in range(len(CLASSES))] for i in range(len(CLASSES))]
    return {
        "poids": str(poids.relative_to(RACINE)),
        "n_test": int(len(vrai)),
        "exactitude": round(float(np.mean(vrai == pred)), 4),
        "f1_macro": round(f1_macro(vrai, pred, len(CLASSES)), 4),
        "exactitude_12_classes": round(float(np.mean(vrai_f == pred_f)), 4),
        "f1_macro_12_classes": round(f1_macro(vrai_f, pred_f, len(FINES)), 4),
        "anomalie_vs_sain": {
            "anomalies_ratees": int(np.sum(anomalies & (pred == sain))),
            "taux_anomalies_ratees": round(float(np.sum(anomalies & (pred == sain)) / anomalies.sum()), 4),
            "fausses_alertes": int(np.sum(sains & (pred != sain))),
            "taux_fausses_alertes": round(float(np.sum(sains & (pred != sain)) / sains.sum()), 4),
        },
        "par_classe": metriques(vrai, pred, CLASSES),
        "par_classe_origine": metriques(vrai_f, pred_f, FINES),
        "matrice_confusion": {"classes": CLASSES, "lignes_vrai_colonnes_predit": matrice},
    }


def ecrire_rapport(res: dict) -> None:
    SORTIE.mkdir(exist_ok=True)
    (SORTIE / "classifier_report.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    l = ["# Classifieur de modules — évaluation sur le jeu de test", ""]
    l.append(f"Modèle : `{res['poids']}` · {res['n_test']} vignettes de test (proportions réelles, jamais vues à l'entraînement)")
    l.append("")
    l.append(f"- 6 classes du projet : exactitude {res['exactitude']:.1%}, F1 macro {res['f1_macro']:.1%}")
    l.append(f"- 12 classes d'origine : exactitude {res['exactitude_12_classes']:.1%}, F1 macro {res['f1_macro_12_classes']:.1%}")
    a = res["anomalie_vs_sain"]
    l.append(f"- Anomalies classées saines : {a['anomalies_ratees']} ({a['taux_anomalies_ratees']:.1%}) · "
             f"modules sains signalés : {a['fausses_alertes']} ({a['taux_fausses_alertes']:.1%})")
    for titre, cle in (("Classe du projet", "par_classe"), ("Classe d'origine", "par_classe_origine")):
        l += ["", f"| {titre} | n | Précision | Rappel | F1 |", "|---|---:|---:|---:|---:|"]
        for c, v in res[cle].items():
            l.append(f"| {c} | {v['n']} | {v['precision']:.1%} | {v['recall']:.1%} | {v['f1-score']:.1%} |")
    m = res["matrice_confusion"]
    l += ["", "Matrice de confusion (lignes = vrai, colonnes = prédit)", "",
          "| | " + " | ".join(m["classes"]) + " |", "|---" * (len(m["classes"]) + 1) + "|"]
    for c, ligne in zip(m["classes"], m["lignes_vrai_colonnes_predit"]):
        l.append(f"| {c} | " + " | ".join(map(str, ligne)) + " |")
    (SORTIE / "classifier_report.md").write_text("\n".join(l) + "\n")
    print("\n".join(l))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--lot", type=int, default=256)
    p.add_argument("--eval-only", type=Path, help="évaluer ces poids sans réentraîner")
    a = p.parse_args()

    torch.set_num_threads(max(torch.get_num_threads(), 1))
    donnees = charger()
    print({k: len(v[1]) for k, v in donnees.items()}, flush=True)
    poids = a.eval_only.resolve() if a.eval_only else entrainer(donnees, a.epochs, a.lot)
    ecrire_rapport(evaluer(poids, donnees))


if __name__ == "__main__":
    main()
