"""Validation du classifieur (models/classifier.pt) sur le jeu DTU (« DTU PV plant - Drone Infrared Thermography
Dataset: Influence of Irradiance and Altitude », doi 10.11583/DTU.29665346.v1, CC BY 4.0).

    .venv/bin/python scripts/valider_dtu.py ~/donnees_externes/dtu_irt_pv/extrait/"IRT DATASET"

Le jeu : 43 modules aux défauts connus (EL, courbes I-V), photographiés au Mavic 3T à 8, 10, 14, 20 m et sous
200 à > 800 W/m² ; chaque image est un module redressé en températures (.raw float32, 605 × 363, portrait).
Pas de module sain : on ne mesure que la détection et la classe, pas les fausses alertes.

Chaque image est ramenée à 40 × 24 (moyenne par blocs, comme une vignette vue de haut) puis standardisée
comme à l'entraînement ; la décision finale passe par le seuil d'écart de `anomalies.py` (ΔT ≥ 3 K). Écrit output/validation_dtu.md et output/validation_dtu.json (non versionnés).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anomalies import FORMES, SEUIL_K, charger_modele, classer, decrire  # noqa: E402
from train_classifier import SORTIE  # noqa: E402

FORME = (605, 363)
# dossier DTU → (libellé, classe attendue du projet, visible en IR d'après DTU / IEA PVPS 2025)
ATTENDU = {
    "01_Cell Cracks": ("fissures de cellules", "cracking", False),
    "02_Cell Interconnects": ("interconnexions", "hotspot", True),
    "03_PID": ("PID", None, False),
    "04_Glass Cracks": ("verre fissuré", "cracking", False),
    "05_Short-circuited Bypass Diode": ("diode court-circuitée", "bypass_diode", True),
    "06_Soiling 1": ("salissures 1", "obstruction", True),
    "07_Soiling 2": ("salissures 2", "obstruction", True),
}


def conditions(nom):
    """« T10_14m_600_APV771 » → (14, '600') ; altitude ou éclairement inconnu → None."""
    alt = re.search(r"(\d+)m", nom)
    ecl = re.search(r"_(abv800|\d{3})(?:_|$| )", nom)
    return (int(alt.group(1)) if alt else None, ecl.group(1) if ecl else None)


def charger(racine):
    lignes = []
    for f in sorted(Path(racine).glob("*/Module */IRT/*.raw")):
        t = np.fromfile(f, "<f4")
        if t.size != FORME[0] * FORME[1]:
            continue
        t = t.reshape(FORME)
        defaut, module = f.parts[-4], f.parts[-3]
        alt, ecl = conditions(f.stem)
        lignes.append({"fichier": str(f.relative_to(racine)), "defaut": defaut, "module": module,
                       "altitude": alt, "eclairement": ecl, "dT_p99": round(float(np.percentile(t, 99.5)
                       - np.median(t)), 2), "t": t})
    return lignes


def main(racine):
    modele = charger_modele()
    lignes = []
    for l in charger(racine):          # par module, pour ne pas garder 640 matrices pleines en mémoire
        t = l.pop("t")
        l["forme"] = decrire(t)["forme"]
        r = classer([t], modele)[0]
        l.update(classe=r["classe"], confiance=r["confiance"], classe_ia=r["classe_ia"],
                 classe_fine=r["classe_fine"], ecart_K=r["ecart_K"])
        lignes.append(l)

    par_defaut = defaultdict(list)
    for l in lignes:
        par_defaut[l["defaut"]].append(l)
    out = ["# Classifieur sur le jeu DTU (Mavic 3T, 43 modules)", "",
           f"{len(lignes)} images. « Signalé » = classe ≠ no_anomaly ; « IA seule » sans le seuil, « final » avec "
           f"le seuil ΔT ≥ {SEUIL_K:g} K. ΔT = centile 99,5 − médiane du module.",
           "", "| Défaut (DTU) | Images | Attendu | Signalé IA seule | Signalé final | Bonne classe final | "
           "ΔT médian | Classes finales |", "|---|---:|---|---:|---:|---:|---:|---|"]
    resume = {}
    for d, ls in sorted(par_defaut.items()):
        lib, cible, _ = ATTENDU.get(d, (d, None, None))
        n = len(ls)
        bon = sum(l["classe"] == cible for l in ls) if cible else None
        vue = sum(l["classe"] != "no_anomaly" for l in ls)
        vue_ia = sum(l["classe_ia"] != "no_anomaly" for l in ls)
        dt = float(np.median([l["dT_p99"] for l in ls]))
        top = ", ".join(f"{c} {k}" for c, k in Counter(l["classe"] for l in ls).most_common())
        resume[d] = {"images": n, "attendu": cible, "bonne_classe": bon, "signale": vue, "signale_ia": vue_ia,
                     "dT_median": dt}
        out.append(f"| {lib} | {n} | {cible or '—'} | {100 * vue_ia / n:.0f} % | {100 * vue / n:.0f} % | "
                   f"{'—' if bon is None else f'{100 * bon / n:.0f} %'} | {dt:.1f} K | {top} |")

    def tableau(cle, titre, ordre):
        out.extend(["", f"## Diodes et salissures selon {titre} (bonne classe)", "",
                    "| " + titre + " | " + " | ".join(map(str, ordre)) + " |", "|---|" + "---:|" * len(ordre)])
        for d in ("05_Short-circuited Bypass Diode", "06_Soiling 1", "07_Soiling 2"):
            cible = ATTENDU[d][1]
            cases = []
            for v in ordre:
                ls = [l for l in par_defaut.get(d, []) if l[cle] == v]
                cases.append(f"{sum(l['classe'] == cible for l in ls)}/{len(ls)}" if ls else "—")
            out.append(f"| {ATTENDU[d][0]} | " + " | ".join(cases) + " |")

    formes = [f for f in FORMES if f != "module_chaud"]
    out.extend(["", "## Forme de l'anomalie (`decrire`, option A : forme et non cause)", "",
                "| Défaut (DTU) | " + " | ".join(formes) + " |", "|---|" + "---:|" * len(formes)])
    for d, ls in sorted(par_defaut.items()):
        c = Counter(l["forme"] for l in ls)
        out.append(f"| {ATTENDU.get(d, (d,))[0]} | " + " | ".join(f"{100 * c[f] / len(ls):.0f} %" for f in formes) + " |")
        resume[d]["formes"] = dict(c)
    tableau("altitude", "altitude (m)", sorted({l["altitude"] for l in lignes if l["altitude"]}))
    tableau("eclairement", "éclairement (W/m²)", ["200", "400", "600", "800", "abv800"])
    SORTIE.mkdir(exist_ok=True)
    (SORTIE / "validation_dtu.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (SORTIE / "validation_dtu.json").write_text(json.dumps({"resume": resume, "images": lignes},
                                                           ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser())
