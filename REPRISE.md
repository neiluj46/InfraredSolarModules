# Pipeline thermique PV — état et reprise en local

Objectif : R-JPEG DJI (Mavic 2 EA, Mavic 3T, Matrice 30T / 4T) → températures par pixel →
anomalies PV par IA → `output/orthostudio_report.geojson` importable dans OrthoStudio.

Branche : `ccr-f0a48b31-r292tn`. Travail fait en session cloud les 28-29/10/2026.

## Installation en local

```bash
git clone https://github.com/neiluj46/InfraredSolarModules.git
cd InfraredSolarModules
git checkout ccr-f0a48b31-r292tn
./scripts/install_dji_sdk.sh ~/Téléchargements/dji_thermal_sdk_v1.9_20260526.zip   # zip OFFICIEL DJI (dji.com) + compilation de dji_irp
# secours : ./scripts/install_dji_sdk.sh --miroir  (miroir GitHub non officiel)
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

**Validé en local le 29/10/2026** avec le **zip officiel DJI TSDK v1.9 (20260526)** (source par défaut
du script ; le miroir v1.7 reste en secours, `--miroir`) : `dji_irp -a measure` OK sur les 10 modèles
d'exemple du zip (H20N, H20T, H30T, M2EA, M30T, M3T, M3TD, M4T, M5T, XTS). L'en-tête officiel
`dirp_api.h` est copié dans `dji_sdk/lib/` (comparaison avec `dirp_api_min.h` à faire). Les exemples
officiels n'ont pas de GPS non plus : **photos réelles nécessaires** pour les métadonnées.
M2EA : le réglage des paramètres de mesure est probablement refusé (code −12, `thermal_parser` a un
mode spécial) → garder ceux de l'image (à confirmer).

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
| DTU, EPJ Photovoltaics 2025 (radiométrique, M3T, 8-20 m, EL et I-V ; doi 10.11583/DTU.29665346.v1, CC BY 4.0, 643 Mo) | validation du classifieur | téléchargé dans `~/donnees_externes/dtu_irt_pv/` |
| Modèle YOLOv9 pré-entraîné `P-Darabi/SolarPanelsDefectDetector` (MIT, 8 classes ci-dessus) | comparaison ; `.pt` = pickle, à charger en connaissance de cause | GitHub |

Volumes des jeux Zenodo non vérifiés (Zenodo inaccessible depuis le cloud).

### Vérification de l'en-tête (06/11/2026)
`dirp_api_min.h` comparé au `dirp_api.h` officiel du SDK v1.9 (`dji_sdk/lib/`, non versionné) :
- **Écart corrigé** : `dirp_measurement_params_t` a un 5ᵉ champ `ambient_temp` en v1.9 ; sans lui,
  `dirp_get_measurement_params` écrivait 4 octets au-delà de la structure (pile de `dji_irp`).
- `dirp_resolution_t` en `int32_t` (comme l'officiel), codes d'erreur −15, −16, −32, −64 ajoutés.
- `-a info` donne aussi `ambient_temp` et `measurement_ranges` (plages acceptées par le modèle,
  `dirp_get_measurement_params_range`, déclarée faible : absente d'une v1.7, la clé vaut `null`).
- Plages relevées sur les exemples : distance max **25 m** (M2EA, M3T, M30T, H20T/N, XTS) ou 300 m
  (M4T, H30T, M5T), 1000 m (M3TD) ; une distance hors plage est refusée (−3), pas bornée.
- Effet mesuré (M3T, DJI_0001) : émissivité 0,95 → 0,85 et distance 5 → 25 m : max 50,6 → 58,5 °C,
  moyenne 32,3 → 34,6 °C.
- Avec la v1.9, le M2EA (et H20T, XTS) **accepte** le réglage de l'émissivité : plus de −12 attendu.

### Réglages de mesure (06/11/2026, décidés avec l'utilisateur)
Deux modes dans `scripts/extract_data.py` :
- **par défaut : réglages de la photo** (ε, distance, humidité, T réfléchie du pilote ; souvent 0,95 / 5 m /
  50 % / 25 °C). Mêmes chiffres que DJI Pilot et OrthoStudio. Les anomalies se jugent sur des **écarts**
  avec les modules voisins.
- **`--exact --reflexion <°C>` : températures exactes** : ε 0,85 (verre ; ZAE Bayern, Buerhop : 0,82 au
  maximum en vue perpendiculaire, chute au-delà de ~40°) **et** T réfléchie mesurée sur place (aluminium
  froissé), obligatoire.

Calcul de Planck (8-14 µm, verre ε 0,85, vrai écart 20 K) :

| Ciel reflété | ε 0,95 / Tr 25 | ε 0,85 / Tr 25 | ε 0,85 / Tr = ciel |
|---|---|---|---|
| −30 °C | 19,1 K | 21,1 K | 20,0 K |
| −10 °C | 18,8 K | 20,7 K | 20,0 K |
| +10 °C | 18,5 K | 20,3 K | 20,0 K |

Vrai 55 °C sous ciel à −30 °C : 46,8 / 49,1 / 55,0 °C. Donc 0,85 seule n'apporte rien : soit la photo,
soit 0,85 + T réfléchie.

**Distance** : celle de la photo, même en mode exact. La correction DJI à 25 m multiplie les écarts par
1,29 (M4T ; 1,66 à 50 m, 2,09 à 100 m), 1,19 (H30T), 1,16 (M3T), 1,01 (M30T). Sur le M4T, elle est
indépendante de l'humidité (20-90 %) : ce n'est pas un modèle d'atmosphère (absorption réelle : 1 à 3 %
sur 25 m). Essai de terrain à prévoir : cible de température connue (bouillotte + thermomètre de contact)
à 5, 15, 25, 40 m.

Sur les exemples (`dji_sdk/samples`), le mode exact (Tr −20 °C) monte les médianes de +5 à +15 °C ; le
M5T `DJI_0004/0005` est saturé à −20 °C (bas de gamme de mesure).

Limites connues : fissures de cellules (≤ 1 K), PID (2 K) et verre fissuré (2,7 K) sont à peine au-dessus
d'un module sain (1,5 K) selon DTU : classe « fissures » = suspicion, à confirmer par EL. Conditions IEC TS
62446-3 : > 600 W/m², vent < 28 km/h, ≤ 3 cm/px (≈ 22 m en M3T). Sans RTK, 1 à 3 m d'erreur de position :
caler les anomalies sur l'orthophoto couleur.

Sources : Raptor Maps (M3T, ε 0,95), Sitemark (IEC 62446-3), Buerhop / PV Tech, DTU IEA PVPS 2025,
EPJ Photovoltaics 2025 (DTU).

### Validation du classifieur sur le jeu DTU (06/11/2026, `scripts/valider_dtu.py`)
640 images de 43 modules aux défauts connus (Mavic 3T, 8-20 m, 200 à > 800 W/m², modules redressés en
températures). Rapport : `output/validation_dtu.md` (non versionné). Aucun module sain dans le jeu.

| Défaut | Images | Bonne classe | Anomalie vue (IA) | ΔT médian | ΔT > 3 K |
|---|---:|---:|---:|---:|---:|
| fissures de cellules | 128 | 0 % | 68 % | 0,9 K | 0 % |
| interconnexions | 128 | 39 % (hotspot) | 86 % | 1,3 K | 0 % |
| PID | 96 | — | 80 % | 1,1 K | 3 % |
| verre fissuré | 32 | 0 % | 84 % | 1,6 K | 3 % |
| diode court-circuitée | 112 | 0 % | 100 % | 24,5 K | 93 % |
| salissures (2 séries) | 144 | 44 % | 94 % | 3,2-6,1 K | 50 % |

Constats :
- **Fausses alertes sur des modules uniformes** : la standardisation par vignette amplifie le bruit d'un
  module à 1 K d'écart jusqu'à en faire un « défaut » (confiance médiane 0,44). Correctif prévu à l'étape 4 :
  **seuil physique ΔT ≥ 3 K avant le classifieur** (à valider sur de vrais vols) ; fissures / PID / verre
  restent alors « non visibles en IR », ce qui est la réponse honnête.
- **Diode court-circuitée vue (93 % > 3 K) mais mal classée** (corrigé le 06/11 après examen des images :
  ce n'est pas la boîte de jonction) : la signature DTU est **plusieurs cellules chaudes**, confinées dans un
  tiers de la largeur (une sous-chaîne) sur 4 modules sur 7, sur deux tiers pour les 3 autres. Les salissures
  donnent aussi des cellules chaudes (jusqu'à 53 K), confinées dans un tiers sur 1 module sur 7 : la cause ne se
  distingue pas en infrarouge seul sur ces données (photo couleur, test des diodes ou courbe I-V).
- Salissures : invisibles à 200 W/m² (ΔT 2 K), visibles au-delà de 600 W/m² (5-16 K) : conditions IEC.
- Le jeu DTU ne sert qu'au test (trop petit pour l'entraînement, une seule centrale) ; le détecteur de
  modules n'est pas testé (images déjà découpées).


**Seuil ajouté (`scripts/anomalies.py`, `classer`)** : classifieur consulté seulement si l'écart interne
(centile 99,5 − médiane) ≥ 3 K. Sur DTU, modules signalés, sans seuil puis avec :

| Défaut | IA seule | Avec seuil | Bonne classe |
|---|---:|---:|---:|
| fissures de cellules | 68 % | 0 % | — |
| interconnexions | 86 % | 1 % | — |
| PID | 80 % | 3 % | — |
| verre fissuré | 84 % | 3 % | — |
| diode court-circuitée | 100 % | 93 % | 0 % |
| salissures (2 séries) | 94 % | 50 % | 15 % |

Les salissures non signalées sont surtout les images à 200 W/m² (hors conditions IEC). Reste : classe des
diodes et des salissures (même signature : cellules chaudes) ; module entier chaud (`offline_module`) contre les voisins.
Tests : `tests/test_anomalies.py` (5).


**Forme plutôt que cause (option A, décidée le 06/11/2026, `anomalies.decrire`)** : sain (écart < 3 K),
point chaud (une zone ≤ 2,5 % du module), cellules chaudes multiples, **diode possible** (≥ 90 % de l'aire
chaude dans un tiers de la largeur = une sous-chaîne), **sous-chaîne chaude** (≥ 60 % d'un tiers au-dessus des
deux autres + 3 K = diode activée) ; `modules_chauds` : moyenne ≥ médiane des voisins + 3 K (hors service, non
validé : pas de voisins dans DTU). Cause à confirmer : photo couleur, test de diode, courbe I-V.

| DTU | sain | point chaud | cellules chaudes | diode possible | sous-chaîne |
|---|---:|---:|---:|---:|---:|
| fissures, interconnexions, PID, verre | 97-100 % | 0-3 % | 0 % | 0 % | 0 % |
| diode court-circuitée | 7 % | 9 % | 39 % | **45 %** | 0 % |
| salissures 1 / 2 | 50 % | 18 / 0 % | 19 / 44 % | 12 / 6 % | 0 % |

Contrôle géométrique sur Raptor Maps (vignettes 8 bits, sans températures : cadre de 3 px rogné, écart ramené
à 10) : « Diode » → sous-chaîne chaude 83 % (Diode-Multi 81 %). Mais une cellule seule (« Cell ») n'y sort en
point chaud que dans 5 % des cas : à 24 × 40 px, une cellule et son halo dépassent 2,5 % du module. Le
décompte des cellules dépend de la résolution (≈ 3 cm/px conseillé) ; seuils non réglés sur ces données.
Hypothèse : trois sous-chaînes dans la largeur en portrait (modules 60 / 72 / 120 / 144 cellules), à vérifier
sur les centrales. Le module doit être découpé sans le fond autour (le détecteur devra rogner).

### Étape 3 — détecteur de modules (06/11/2026, `scripts/train_detector.py`, `scripts/detecteur.py`)
Choix (avec l'utilisateur) : réseau **maison**, PyTorch seul (BSD), entraîné de zéro, aucun poids tiers.
Ultralytics YOLO écarté : AGPL, licence payante revendiquée même en usage interne.
- Données : Zenodo 16420123 (CC BY 4.0, Mavic 3T, 235 / 83 / 35 images, 26 678 modules), hors dépôt dans
  `~/donnees_externes/zenodo_pv_detection/` (AEX) et `~/infrared/donnees/` (DELLODM).
- Les rangées sont inclinées mais les annotations sont des cadres **droits** : détection par **centres**
  (CenterNet ; centre du cadre droit = centre du module), petit U-Net 2,1 M paramètres, sortie au pas de 4.
  Inclinaison : angles quadruplés des gradients autour du centre ; rectangle incliné déduit du cadre droit
  (vers 45° : proportions médianes des modules de la photo).
- Entrée bornée aux centiles 1-99 puis standardisée ; **défauts simulés** à l'entraînement (points chauds,
  zones chaudes, taches froides) : sans eux, un point chaud de +12 K faisait perdre son module au détecteur.
- **Entraînement sur DELLODM** (RTX 2080, Docker `pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime`, 12 Go) :
  `scripts/entrainer_dellodm.sh [epochs|suivre|rapatrier]`, 6 s par époque (160 s sur AEX), 60 époques ≈ 7 min.
  Poids : `models/detector.pt` (8,6 Mo, non versionné : `models/` est ignoré), sur AEX et DELLODM.
- **Images sans panneau** (exemples du SDK DJI en températures, `~/donnees_externes/negatifs_dji/`, 31 pour
  l'entraînement ×3, 23 pour l'évaluation ; licence DJI, hors dépôt) : sans elles, le détecteur voyait des
  « modules » partout sur un toit ou une ville (≈ 31 par image : climatiseurs, bords de toit) ; avec elles,
  0,22 par image jamais vue (max 4). Le filtre de cohérence (voisins alignés, même taille) n'en retirait
  qu'un tiers et coûtait 3 points de rappel : abandonné. Modèle gardé : dernière époque (le meilleur F1
  gardait un modèle du début, à 9 fausses détections par image sans panneau).
- Résultats (test, 35 images, 2 363 modules, IoU ≥ 0,5) : précision 95,2 %, rappel 84,9 %, F1 0,90 ;
  **modules entiers : 98,4 % trouvés** (98,8 % avec un point chaud collé) ; 90 % des manqués et 75 % des faux positifs sont des modules coupés par
  le bord de l'image, écartés de l'analyse (`complet`). Erreur médiane du centre : 2 px.
- `detecteur.analyser(t)` : matrice de températures → modules entiers, forme de l'anomalie, module chaud.
  Test de bout en bout sur une image Zenodo en pseudo-températures (`tests/test_detecteur.py`).
- Limites : une seule centrale d'entraînement (modules en paysage, deux rangées par table) ; JPEG convertis,
  pas de R-JPEG : à vérifier sur tes vols. Seuil de score 0,3 (0,4 : précision 96,6 %, rappel 84 %).

### Étape 5 — export vers OrthoStudio (06/11/2026, `scripts/export_orthostudio.py`)
`R-JPEG → températures → modules (detecteur.analyser) → coins projetés au sol → fusion des vues →
output/orthostudio_report.geojson` (WGS 84 ; propriétés `forme`, `libelle`, `anomalie`, `confirmee`, `T_max`,
`T_mean`, `dT`, `dT_voisins`, `photo`, `vues`, `vues_anomalie`, `largeur_m`, `focale` ; `metadata.photos` :
journal par photo avec ses alertes). Par défaut seuls les modules en anomalie (`--tous` : tous).
- Projection : sténopé sans distorsion, `rotation_dji` reprise d'OrthoStudio (test d'égalité avec
  `georef/camera.py`), sol plan à `RelativeAltitude − --hauteur-modules` sous la caméra.
- Focale : DFOV officiel DJI (M3T / M3TD / M30T 61°, M4T 45°, H30T 45,2°), sinon focale équivalente 35 mm
  rapportée à la diagonale (juste pour les caméras « 52 mm », 57° au lieu de 61° pour les « 40 mm »).
- Fusion : même module si centres à moins d'une demi-largeur ; vue la plus centrale gardée ; anomalie vue sur
  une seule des photos où le module apparaît → `confirmee: false` (reflet possible).
- Tests : `tests/test_export_orthostudio.py` (orientation, échelle, oblique, WGS 84, fusion, GeoJSON, chaîne
  complète sur les exemples DJI). **Non vérifié sur un vrai vol** : les exemples DJI n'ont ni XMP (nacelle,
  hauteur) ni panneaux ; sans RTK, 1 à 3 m d'erreur (plus que la largeur d'un module) : calage sur
  l'orthophoto d'OrthoStudio reste à faire.
- **Import dans OrthoStudio** ✅ (06/11, branche `ccr-0037e643-x5jvxm`, f4c918c) : onglet Thermique, section
  « Anomalies PV importées » (`orthostudio/thermique_pv.py`, `static/js/thermique_pv.js`) ; section « Anomalies PV »
  du rapport PDF et feuille Excel (af00d2a).

## À faire

1. ✅ `dji_irp` validé sur les 10 modèles d'exemple (SDK officiel v1.9), en-tête vérifié (ci-dessus).
2. ✅ Étape 2 `scripts/extract_data.py` (06/11) : `dji_irp -a measure` → matrice float32 ; EXIF / XMP /
   MakerNote (lat, lon, altitudes, nacelle, attitude du drone) → `data/processed/metadata_db.json` ; JPEG
   visibles marqués `radiometrique: false`. Tests : `tests/test_extract_data.py` (9, sur les exemples DJI).
   **Reste** : tester GPS / altitudes / nacelle sur de vraies photos (pas encore de données) ; essai de
   distance sur le terrain. Jeu DTU (CC BY 4.0, 643 Mo) téléchargé hors dépôt dans
   `~/donnees_externes/dtu_irt_pv/` pour valider le classifieur (images .raw sans métadonnées).
   ✅ Classifieur validé sur DTU, seuil ΔT ≥ 3 K, rapport par forme (`scripts/anomalies.py`).
3. ✅ Détecteur de modules maison (ci-dessus). Reste : essai sur de vrais R-JPEG.
4. ✅ Remplacé par `detecteur.analyser` (T_max, T_moyenne, ΔT interne, écart aux voisins, module chaud).
5. ✅ `scripts/export_orthostudio.py` et import OrthoStudio (ci-dessus). Reste : vrai vol, calage sur l'orthophoto,
   rapport PDF fait.
   Ancienne note : projection des boîtes (sol plan, pose de la nacelle ; voir aussi
   `georef/` d'OrthoStudio : `rotation_dji`, `footprint`, conventions de cap par modèle) →
   `output/orthostudio_report.geojson`.

6. **Plan de calepinage** (demandé le 06/11/2026 ; décisions et étapes C.1 à C.5 dans
   `~/OrthoStudio_test/docs/calepinage_proposition.md` : numérotation générée + import client, module + table,
   modules saisis sur l'orthophoto couleur, livrables PDF / CSV / Excel / GeoJSON / DXF ; **C.1 ✅** modèle et
   numérotation, `orthostudio/calepinage.py` d'OrthoStudio ; **C.2 ✅** API et écran de saisie dans l'onglet
   Thermique ; **C.3 ✅** recalage des modules thermiques sur le plan et identifiant de module de chaque anomalie
   (exporter avec `--tous` pour que le recalage tranche) ; **C.4a ✅** (07/11) colonne « Module » + statut dans le rapport PDF / Excel ; suite C.4b planche PDF du plan, C.4c exports, C.5 import client) : plan des modules de la centrale avec un
   identifiant par module (ex. zone / rangée / table / ligne / colonne), pour **indiquer ses anomalies au
   client** (« rangée 12, table 3, module L2-C14 ») dans le rapport et sur le terrain.
   Dépend du calage des positions sur l'orthophoto (1 à 3 m d'erreur sans RTK = plus qu'un module).
   Questions métier à poser AVANT de concevoir :
   - le client a-t-il déjà un plan / une numérotation (PDF, DWG / DXF, tableur des chaînes) à reprendre, ou
     faut-il en générer une ? Sens de numérotation (nord → sud, ouest → est, depuis l'entrée ?) ;
   - niveau de détail : module seul, ou aussi chaîne (string) et onduleur / boîte de jonction ?
   - source des modules : orthophoto couleur d'OrthoStudio (plus nette, sans reflets) ou mosaïque des
     détections thermiques ; regroupement en tables par alignement ;
   - livrables : planche PDF (vue d'ensemble + zooms par zone) dans le rapport, colonne « identifiant » dans
     le tableau des anomalies, export pour le client (GeoJSON, DXF, CSV ?).

## Arborescence

```
data/raw_rjpegs/     R-JPEG à traiter (non versionnés)
data/processed/      metadata_db.json, matrices (non versionnés)
dji_sdk/src/         dji_irp.c, dirp_api_min.h (versionnés)
dji_sdk/lib|bin|samples/   installés par scripts/install_dji_sdk.sh
models/classifier.pt classifieur des modules
output/              rapports, GeoJSON
scripts/             install_dji_sdk.sh, extract_data.py, anomalies.py, detecteur.py, train_detector.py, export_orthostudio.py,
                     entrainer_dellodm.sh, train_classifier.py, valider_dtu.py
tests/               pytest (sautés sans SDK installé)
```
