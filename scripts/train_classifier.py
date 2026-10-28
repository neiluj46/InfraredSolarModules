"""Classifieur de l'état d'un module photovoltaïque (vignette infrarouge).

Deuxième étage du pipeline : un détecteur isole chaque module dans l'image thermique,
ce classifieur dit ce qu'il a. Entraîné sur InfraredSolarModules (Raptor Maps, 20 000
vignettes 24 × 40 px, 12 classes), regroupées vers les classes du projet :

    no_anomaly      No-Anomaly
    hotspot         Cell, Cell-Multi, Hot-Spot, Hot-Spot-Multi
    bypass_diode    Diode, Diode-Multi
    offline_module  Offline-Module (module entier chaud ; plusieurs modules voisins
                    d'une même rangée = string_failure, déduit après classement)
    obstruction     Shadowing, Vegetation, Soiling (pas un défaut du module, mais à
                    distinguer pour éviter les fausses alertes)
    cracking        Cracking

Aucune base ouverte n'étiquette le PID : il sera traité par une règle plus tard.

Utilisation :
    .venv/bin/python scripts/train_classifier.py              # prépare, entraîne, évalue
    .venv/bin/python scripts/train_classifier.py --epochs 50 --cap-sain 3000
    .venv/bin/python scripts/train_classifier.py --eval-only models/classifier.pt
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import zipfile
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
ARCHIVE = RACINE / "2020-02-14_InfraredSolarModules.zip"
DONNEES = RACINE / "data" / "classif"
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
CLASSES = sorted(set(REGROUPEMENT.values()))
PARTS = {"train": 0.8, "val": 0.1, "test": 0.1}


def preparer(cap_sain: int | None, graine: int = 0) -> dict:
    """Extrait l'archive en dossiers train/val/test/<classe>/ (découpage stratifié
    sur la classe d'origine). cap_sain limite les modules sains de train seulement :
    val et test gardent la proportion réelle."""
    if DONNEES.exists():
        shutil.rmtree(DONNEES)
    with zipfile.ZipFile(ARCHIVE) as z:
        meta = json.loads(z.read("InfraredSolarModules/module_metadata.json"))
        par_classe: dict[str, list[str]] = {}
        for num, m in meta.items():
            par_classe.setdefault(m["anomaly_class"], []).append(num)

        rng = random.Random(graine)
        comptes: dict[str, Counter] = {p: Counter() for p in PARTS}
        origine: dict[str, dict[str, str]] = {p: {} for p in PARTS}
        for classe, nums in sorted(par_classe.items()):
            nums.sort(key=int)
            rng.shuffle(nums)
            n_val = round(len(nums) * PARTS["val"])
            n_test = round(len(nums) * PARTS["test"])
            decoupe = {
                "val": nums[:n_val],
                "test": nums[n_val:n_val + n_test],
                "train": nums[n_val + n_test:],
            }
            if cap_sain and classe == "No-Anomaly":
                decoupe["train"] = decoupe["train"][:cap_sain]
            cible = REGROUPEMENT[classe]
            for part, liste in decoupe.items():
                dossier = DONNEES / part / cible
                dossier.mkdir(parents=True, exist_ok=True)
                for num in liste:
                    nom = f"{num}.jpg"
                    (dossier / nom).write_bytes(z.read(f"InfraredSolarModules/{meta[num]['image_filepath']}"))
                    origine[part][nom] = classe
                comptes[part][cible] += len(liste)

    (DONNEES / "origine.json").write_text(json.dumps(origine))
    return {p: dict(sorted(c.items())) for p, c in comptes.items()}


def entrainer(epochs: int, imgsz: int, batch: int, modele: str) -> Path:
    from ultralytics import YOLO

    # Sans poids pré-entraînés : architecture seule, aucun fichier téléchargé.
    yolo = YOLO(modele)
    yolo.train(
        data=str(DONNEES),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device="cpu",
        workers=4,
        project=str(RACINE / "runs"),
        name="classifier",
        exist_ok=True,
        seed=0,
        deterministic=True,
        # Une vignette retournée reste un module valide ; l'effacement aléatoire
        # pourrait effacer le point chaud et fausser l'étiquette.
        fliplr=0.5,
        flipud=0.5,
        erasing=0.0,
        plots=True,
        verbose=False,
    )
    meilleur = Path(yolo.trainer.best)
    MODELES.mkdir(exist_ok=True)
    cible = MODELES / "classifier.pt"
    shutil.copy(meilleur, cible)
    return cible


def evaluer(poids: Path, imgsz: int) -> dict:
    from sklearn.metrics import classification_report, confusion_matrix
    from ultralytics import YOLO

    yolo = YOLO(str(poids))
    noms = yolo.names
    origine = json.loads((DONNEES / "origine.json").read_text())["test"]
    vrai, predit, orig = [], [], []
    for classe in CLASSES:
        images = sorted((DONNEES / "test" / classe).glob("*.jpg"))
        for i in range(0, len(images), 256):
            lot = images[i:i + 256]
            for chemin, r in zip(lot, yolo.predict([str(p) for p in lot], imgsz=imgsz, device="cpu", verbose=False)):
                vrai.append(classe)
                predit.append(noms[int(r.probs.top1)])
                orig.append(origine[chemin.name])

    rapport = classification_report(vrai, predit, labels=CLASSES, output_dict=True, zero_division=0)
    matrice = confusion_matrix(vrai, predit, labels=CLASSES).tolist()
    # Rappel par classe d'origine : quelles sous-classes le modèle rate-t-il ?
    rappel_origine = {}
    for c in sorted(set(orig)):
        idx = [k for k, o in enumerate(orig) if o == c]
        ok = sum(predit[k] == REGROUPEMENT[c] for k in idx)
        rappel_origine[c] = {"n": len(idx), "rappel": round(ok / len(idx), 3)}
    # Une anomalie classée saine est l'erreur la plus coûteuse pour une inspection.
    anomalies = [k for k, v in enumerate(vrai) if v != "no_anomaly"]
    ratees = sum(predit[k] == "no_anomaly" for k in anomalies)
    sains = [k for k, v in enumerate(vrai) if v == "no_anomaly"]
    fausses = sum(predit[k] != "no_anomaly" for k in sains)
    return {
        "poids": str(poids.relative_to(RACINE)),
        "n_test": len(vrai),
        "exactitude": round(rapport["accuracy"], 4),
        "f1_macro": round(rapport["macro avg"]["f1-score"], 4),
        "anomalie_vs_sain": {
            "anomalies_ratees": ratees,
            "taux_anomalies_ratees": round(ratees / len(anomalies), 4),
            "fausses_alertes": fausses,
            "taux_fausses_alertes": round(fausses / len(sains), 4),
        },
        "par_classe": {
            c: {k: round(rapport[c][k], 3) for k in ("precision", "recall", "f1-score")} | {"n": int(rapport[c]["support"])}
            for c in CLASSES
        },
        "par_classe_origine": rappel_origine,
        "matrice_confusion": {"classes": CLASSES, "lignes_vrai_colonnes_predit": matrice},
    }


def ecrire_rapport(res: dict, comptes: dict | None) -> None:
    SORTIE.mkdir(exist_ok=True)
    (SORTIE / "classifier_report.json").write_text(json.dumps({"comptes": comptes, **res}, indent=2, ensure_ascii=False))
    l = ["# Classifieur de modules — évaluation sur le jeu de test", ""]
    l.append(f"Modèle : `{res['poids']}` · {res['n_test']} vignettes de test (proportions réelles)")
    l.append(f"Exactitude : {res['exactitude']:.1%} · F1 macro : {res['f1_macro']:.1%}")
    a = res["anomalie_vs_sain"]
    l.append(f"Anomalies classées saines : {a['anomalies_ratees']} ({a['taux_anomalies_ratees']:.1%}) · "
             f"modules sains signalés : {a['fausses_alertes']} ({a['taux_fausses_alertes']:.1%})")
    l += ["", "| Classe | n | Précision | Rappel | F1 |", "|---|---:|---:|---:|---:|"]
    for c, v in res["par_classe"].items():
        l.append(f"| {c} | {v['n']} | {v['precision']:.1%} | {v['recall']:.1%} | {v['f1-score']:.1%} |")
    l += ["", "| Classe d'origine | n | Rappel |", "|---|---:|---:|"]
    for c, v in res["par_classe_origine"].items():
        l.append(f"| {c} | {v['n']} | {v['rappel']:.1%} |")
    m = res["matrice_confusion"]
    l += ["", "Matrice de confusion (lignes = vrai, colonnes = prédit)", "",
          "| | " + " | ".join(m["classes"]) + " |", "|---" * (len(m["classes"]) + 1) + "|"]
    for c, ligne in zip(m["classes"], m["lignes_vrai_colonnes_predit"]):
        l.append(f"| {c} | " + " | ".join(map(str, ligne)) + " |")
    (SORTIE / "classifier_report.md").write_text("\n".join(l) + "\n")
    print("\n".join(l))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--imgsz", type=int, default=64)
    p.add_argument("--batch", type=int, default=128)
    p.add_argument("--modele", default="yolo11n-cls.yaml")
    p.add_argument("--cap-sain", type=int, default=3000,
                   help="modules sains gardés dans train (0 = tous)")
    p.add_argument("--eval-only", type=Path, help="évaluer ces poids sans réentraîner")
    a = p.parse_args()

    comptes = None
    if a.eval_only:
        poids = a.eval_only.resolve()
    else:
        comptes = preparer(a.cap_sain or None)
        print("Jeu préparé :", json.dumps(comptes, indent=1))
        poids = entrainer(a.epochs, a.imgsz, a.batch, a.modele)
    ecrire_rapport(evaluer(poids, a.imgsz), comptes)


if __name__ == "__main__":
    main()
