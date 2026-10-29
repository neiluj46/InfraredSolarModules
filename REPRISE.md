# Pipeline thermique PV — état et reprise en local

Objectif : R-JPEG DJI (Mavic 2 EA, Mavic 3T, Matrice 30T / 4T) → températures par pixel →
anomalies PV par IA → `output/orthostudio_report.geojson` importable dans OrthoStudio.

Branche : `ccr-f0a48b31-r292tn`. Travail fait en session cloud les 28-29/10/2026.

## Installation en local

```bash
git clone https://github.com/neiluj46/InfraredSolarModules.git
cd InfraredSolarModules
git checkout ccr-f0a48b31-r292tn
./scripts/install_dji_sdk.sh                 # SDK DJI v1.7 + compilation de dji_irp (Linux x64, gcc)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Fait

### Étape 1 — DJI Thermal SDK (`dji_sdk/`, `scripts/install_dji_sdk.sh`)
- dji.com / djicdn.com inaccessibles depuis le cloud ; paquet PyPI `dji-thermal-sdk` = Windows seul.
- Bibliothèques Linux x64 du **TSDK v1.7 (20241205)** prises sur le miroir GitHub
  `SanNianYiSi/thermal_parser` (commit figé `b513647`, SHA-256 vérifiés par le script).
- Le miroir n'a ni `dji_irp` ni en-têtes : `dji_sdk/src/dji_irp.c` (écrit ici) + `dirp_api_min.h`
  (reconstitué depuis les symboles de libdirp.so). Options compatibles avec l'exemple DJI :
  ```bash
  dji_sdk/bin/dji_irp -s photo.JPG -a measure -o t.raw [--measurefmt float32|int16]
                      [--distance m] [--humidity %] [--emissivity e] [--reflection °C]
  dji_sdk/bin/dji_irp -s photo.JPG -a extract -o raw.raw   # RAW 16 bits
  dji_sdk/bin/dji_irp -s photo.JPG -a info                 # JSON : taille, versions, paramètres
  ```
  Sortie `measure` : tableau ligne par ligne, float32 °C (défaut) ou int16 en 0,1 °C.
- Binaires DJI **non versionnés** (licence DJI) : `.gitignore`, réinstallés par le script.
- R-JPEG d'exemple dans `dji_sdk/samples/` : M2EA, M3T, M3TD, M30T, M4T, H20T, H30T (44 photos).
  Données radiométriques intactes, mais **XMP et GPS retirés** par l'auteur du miroir ; les `.txt`
  (dumps exiftool d'origine, UTF-16 pour M2EA / H20T) gardent GPS et nacelle des 5 M3T.

**⚠ Jamais exécuté** : la session cloud a refusé de lancer les bibliothèques DJI venues d'un miroir
non officiel. Première chose à faire en local :
```bash
dji_sdk/bin/dji_irp -s dji_sdk/samples/M3T/DJI_0001_R.JPG -a info
dji_sdk/bin/dji_irp -s dji_sdk/samples/M3T/DJI_0001_R.JPG -a measure -o /tmp/t.raw
python3 -c "import numpy as n; t=n.fromfile('/tmp/t.raw',n.float32).reshape(512,640); print(t.min(),t.mean(),t.max())"
```
À essayer sur les 4 modèles. M2EA : le réglage des paramètres de mesure est probablement refusé
(code −12, `thermal_parser` a un mode spécial) → garder ceux de l'image.

### Classifieur de l'état des modules (`scripts/train_classifier.py`)
Choix d'architecture : **deux étages** (détecteur de modules, puis classifieur par module), car la
seule grosse base ouverte (InfraredSolarModules, Raptor Maps, 20 000 vignettes 24 × 40, 12 classes,
`2020-02-14_InfraredSolarModules.zip` du dépôt) est un jeu de classification, et un polygone par
module donne un meilleur compte rendu OrthoStudio (ΔT contre les modules sains voisins, IEC TS 62446-3).

- Petit CNN PyTorch (3 blocs, 40 × 24 natif, standardisation par vignette, retournements et ±2 px,
  perte pondérée), entraîné sur les 12 classes, probabilités regroupées en 6 classes du projet :
  `no_anomaly`, `hotspot` (Cell, Cell-Multi, Hot-Spot, Hot-Spot-Multi), `bypass_diode` (Diode,
  Diode-Multi), `offline_module`, `obstruction` (Shadowing, Vegetation, Soiling), `cracking`.
- YOLO11n-cls d'Ultralytics essayé d'abord et abandonné : recadrage aléatoire et RandAugment
  coupent le défaut des vignettes (validation 30-64 %, instable).
- Modèle : `models/classifier.pt` (versionné, 3 Mo ; `torch.load(..., weights_only=True)`, clés
  `etat`, `fines`, `regroupement`, `classes`, `entree`, `historique`).
  Réentraîner : `.venv/bin/python scripts/train_classifier.py` (40 époques, ~20 min sur 4 cœurs).
- Test (2 002 vignettes jamais vues, proportions réelles) — `output/classifier_report.md` :
  6 classes 82,6 % (F1 macro 75,2 %), 12 classes 80,6 % ; anomalies classées saines 6,9 %,
  modules sains signalés 10 %.

  | Classe | Rappel | Précision |
  |---|---:|---:|
  | bypass_diode | 93,5 % | 96,9 % |
  | no_anomaly | 90,0 % | 92,9 % |
  | hotspot | 77,1 % | 71,3 % |
  | obstruction | 70,3 % | 70,8 % |
  | cracking | 64,9 % | 67,8 % |
  | offline_module | 57,8 % | 50,0 % |

- **Module hors service → règle sur les températures, pas l'IA** : la standardisation par vignette
  rend un module chaud partout identique à un module sain. Règle prévue : moyenne du module >
  moyenne des voisins + seuil ; plusieurs modules voisins d'une rangée = `string_failure`.
- **PID** : aucune base ouverte ne l'étiquette → règle plus tard (damier, extrémité de chaîne).
- Écart de domaine : vignettes 8 bits d'autres centrales ; à mesurer sur des modules découpés dans
  de vrais R-JPEG (portrait 40 × 24, même standardisation).

## Bases de données repérées

| Base | Usage | Accès |
|---|---|---|
| InfraredSolarModules (Raptor Maps) | classifieur (fait) | dans le dépôt |
| Zenodo 16420123 « Thermal PV Panel Detection and Fault Detection Dataset for UAV-Based Inspection » | **détecteur de modules** (prochaine étape) | zenodo.org |
| Kaggle `pkdarabi/solarpanel` (2 723 images, 7 772 boîtes YOLO, 8 classes : hotspot simple / multiple, diode simple / multiple, sous-chaîne court-circuitée simple / multiple, chaîne ouverte, polarité inversée) | détection directe, la plus proche de tes classes | kaggle.com |
| THED-PV (Zenodo 17404247, Scientific Data 2025, CC-BY 4.0) | redressement géométrique (homographie) pour l'export | zenodo.org |
| Mendeley 82vzccxb6y (277 images, Zenmuse XT / Matrice 100) | validation sur données réelles | data.mendeley.com |
| DTU, EPJ Photovoltaics 2025 (radiométrique, vraies diodes en défaut) | validation | voir l'article |
| Modèle YOLOv9 pré-entraîné `P-Darabi/SolarPanelsDefectDetector` (MIT, 8 classes ci-dessus) | comparaison ; `.pt` = pickle, à charger en connaissance de cause | GitHub |

Volumes des jeux Zenodo non vérifiés (Zenodo inaccessible depuis le cloud).

## À faire

1. Valider `dji_irp` sur les exemples M2EA, M3T, M30T, M4T (voir ci-dessus).
2. Étape 2 `scripts/extract_data.py` : `dji_irp -a measure` → matrice float32 ; EXIF / XMP
   (lat, lon, altitudes absolue et relative, nacelle yaw / pitch / roll, cap du drone) →
   `data/processed/metadata_db.json`. Tester sur **tes propres photos** (les exemples n'ont plus de GPS).
   Questions ouvertes : émissivité par défaut des panneaux (0,85 verre ?) ou celle de la photo ;
   M2EA = paramètres de l'image.
3. Détecteur de modules (Ultralytics YOLO, jeu Zenodo 16420123), puis `scripts/train_thermal.py`.
4. `scripts/analyze_anomalies.py` : T_max, T_mean, ΔT par boîte sur la matrice ; règle module hors
   service / chaîne.
5. `scripts/export_orthostudio.py` : projection des boîtes (sol plan, pose de la nacelle ; voir aussi
   `georef/` d'OrthoStudio : `rotation_dji`, `footprint`, conventions de cap par modèle) →
   `output/orthostudio_report.geojson`.

## Arborescence

```
data/raw_rjpegs/     R-JPEG à traiter (non versionnés)
data/processed/      metadata_db.json, matrices (non versionnés)
dji_sdk/src/         dji_irp.c, dirp_api_min.h (versionnés)
dji_sdk/lib|bin|samples/   installés par scripts/install_dji_sdk.sh
models/classifier.pt classifieur des modules
output/              rapports, GeoJSON
scripts/             install_dji_sdk.sh, train_classifier.py
```
