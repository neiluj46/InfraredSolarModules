# Prompt de reprise — pipeline thermique PV (à coller dans Claude Code, en local)

```
Rôle : agent développeur sur mon dépôt InfraredSolarModules (branche ccr-f0a48b31-r292tn),
en local sur mon PC Linux. Tout en français : code, messages, commits.

Objectif global : R-JPEG thermiques DJI (Mavic 2 EA, Mavic 3T, Matrice 30T / 4T) → matrice
de températures par pixel → anomalies PV détectées par IA → output/orthostudio_report.geojson
(polygones + T_max, T_mean, ΔT) importable dans OrthoStudio (mon logiciel, dépôt neiluj46/orthostudio).

Commence par lire REPRISE.md (état détaillé, résultats, bases de données, suite), puis
git log -8 et scripts/. Ne refais pas ce qui est fait.

Déjà fait :
- Étape 1 : scripts/install_dji_sdk.sh installe le zip OFFICIEL DJI TSDK v1.9 (20260526) dans
  dji_sdk/ et compile dji_sdk/src/dji_irp.c (mon outil : -a measure float32|int16, extract, info,
  --distance --humidity --emissivity --reflection). Validé le 29/10 : measure OK sur les 10 modèles
  d'exemple. Binaires DJI jamais versionnés (licence DJI).
- Classifieur de l'état des modules (scripts/train_classifier.py, models/classifier.pt versionné) :
  petit CNN PyTorch 40 × 24, standardisation par vignette, entraîné sur InfraredSolarModules
  (12 classes → no_anomaly, hotspot, bypass_diode, offline_module, obstruction, cracking).
  Test : 82,6 % (6 classes), bypass_diode 93,5 % de rappel, offline_module faible (57,8 %).
- Décisions : architecture en DEUX étages (détecteur de modules, puis classifieur par module) ;
  module hors service et string_failure par RÈGLE sur les températures (module plus chaud que ses
  voisins ; plusieurs voisins d'une rangée = chaîne), pas par l'IA ; PID : aucune base ouverte,
  règle plus tard. YOLO11n-cls abandonné pour les vignettes (le recadrage coupait le défaut).

À faire maintenant, dans l'ordre (pose-moi les questions avant chaque choix structurant) :
1. Comparer dji_sdk/lib/dirp_api.h (officiel) à dji_sdk/src/dirp_api_min.h ; corriger les écarts
   de signatures ou de structures éventuels.
2. Étape 2 : scripts/extract_data.py
   - temperatures(chemin) → np.ndarray float32 (°C) via dji_irp -a measure (subprocess, fichier
     temporaire), avec les paramètres de mesure facultatifs ; erreur claire si le modèle refuse
     un réglage (M2EA : code −12 attendu → paramètres de l'image).
   - metadonnees(chemin) : modèle, date, lat, lon, altitude absolue et relative, nacelle
     yaw / pitch / roll, cap du drone, taille ; XMP DJI (drone-dji:…) + EXIF (exiftool ou exifread).
   - data/raw_rjpegs/ → data/processed/metadata_db.json (+ matrices .npy si utile).
   - Tests pytest sur dji_sdk/samples/ (températures plausibles, forme 512 × 640 ou 1024 × 1280).
     Les exemples n'ont PAS de GPS : demande-moi de déposer de vraies photos de mes drones dans
     data/raw_rjpegs/ pour tester les métadonnées.
   - Questions à me poser : émissivité par défaut des panneaux (0,85 verre ?) ou celle de la photo ;
     distance = altitude relative ?
3. Règle « module hors service / string_failure » (à partir de la matrice de températures).
4. Détecteur de modules (Ultralytics YOLO) : jeu Zenodo 10.5281/zenodo.16420123 « Thermal PV Panel
   Detection and Fault Detection Dataset for UAV-Based Inspection » (vérifier volume, format,
   licence avant de l'utiliser) → scripts/train_thermal.py. Option : Kaggle pkdarabi/solarpanel
   (8 classes YOLO proches des miennes).
5. scripts/analyze_anomalies.py (T_max, T_mean, ΔT par boîte, ΔT contre les modules sains voisins,
   IEC TS 62446-3) puis scripts/export_orthostudio.py (projection sol plan depuis GPS + pose de la
   nacelle ; reprendre les conventions de georef/ d'OrthoStudio : rotation_dji, footprint, cap par
   modèle) → output/orthostudio_report.geojson.

Règles :
- Ne jamais committer de binaire ni de photo DJI ; données dans data/ (non versionnées).
- Télécharger un jeu ou un modèle .pt d'un tiers : me demander d'abord (un .pt = code exécuté).
- Commits clairs en français, pousser sur ccr-f0a48b31-r292tn ; mettre à jour REPRISE.md à
  chaque étape terminée.
- Attends mon feu vert entre deux étapes.
```

Notes :
- Push en tant qu'`aex` si `git push` demande un identifiant :
  `git -c 'credential.helper=!/home/aex/.local/bin/gh auth git-credential' push` (comme pour OrthoStudio).
- Environnement : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
