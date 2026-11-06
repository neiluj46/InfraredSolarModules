# Prompt de reprise — thermographie PV + OrthoStudio (à coller dans Claude Code après /clear)

Version courte à coller :

```
Lis ~/InfraredSolarModules/PROMPT_REPRISE.md (bloc « Prompt complet ») et suis-le.
```

## Prompt complet

```
Rôle : agent développeur sur deux dépôts à moi, en local sur mon PC Linux (AEX). Tout en français :
échanges, code, commits. Je pilote souvent depuis mon téléphone : rapports courts, lisibles sur mobile.

Dépôts :
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermographie PV).
- OrthoStudio (mon logiciel) : worktree d'essai ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm.
  Instance d'essai port 8001 SEULEMENT (lancement : voir CLAUDE.md, ORTHOSTUDIO_PROJECTS=
  ~/OrthoStudio_essais/projets ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db). JAMAIS la production
  (port 8000, /home/aex/TEST ).

Commence par lire ~/InfraredSolarModules/REPRISE.md (état détaillé, résultats chiffrés, « À faire »),
~/OrthoStudio_test/CLAUDE.md et ~/OrthoStudio_test/docs/reprise_session_2026-11-06.md, puis git log -8
des deux dépôts. Ne refais pas ce qui est fait.

État au 06/11/2026 (tout est poussé) :
- Chaîne complète écrite et testée, mais JAMAIS essayée sur un vrai vol (je n'ai pas encore de R-JPEG
  au-dessus de panneaux) : R-JPEG DJI → températures (scripts/extract_data.py : réglages de la photo par
  défaut, --exact = émissivité 0,85 + température réfléchie mesurée) → modules détectés (détecteur maison
  PyTorch, scripts/train_detector.py + detecteur.py ; Ultralytics écarté : AGPL) → forme de l'anomalie
  (anomalies.py : seuil ΔT ≥ 3 K, point chaud / cellules chaudes / diode possible / sous-chaîne chaude /
  module hors service) → polygones au sol (export_orthostudio.py) → output/orthostudio_report.geojson.
- OrthoStudio : onglet Thermique, section « Anomalies PV importées » (thermique_pv.py, thermique_pv.js) ;
  section « Anomalies PV » du rapport PDF et feuille Excel. Démo FICTIVE importée dans le projet 4 (8001).
- Calculs lourds sur DELLODM (192.168.1.125, RTX 2080, Docker) : scripts/entrainer_dellodm.sh.

Prochaine tâche : le PLAN DE CALEPINAGE (REPRISE.md, « À faire » n° 6) : plan des modules de la centrale
avec un identifiant par module, pour indiquer ses anomalies au client. Avant tout choix structurant,
pose-moi les questions métier listées dans REPRISE.md (plan existant du client ? numérotation ? chaînes /
onduleurs ? source des modules ? livrables ?). Si je manque d'expérience, cherche sur internet, choisis le
plus réaliste et justifie-le de façon critique et détaillée (contre-recherches, chiffres, risques) avant de
commencer. Autres points ouverts : calage des positions sur l'orthophoto (1 à 3 m d'erreur sans RTK), essai
sur un vrai vol (photos à déposer dans ~/InfraredSolarModules/data/raw_rjpegs/), essai de distance sur cible.

Règles :
- Arrêt et rapport court à la fin de chaque point, puis attendre mon feu vert.
- Aucun traitement NodeODM sans mon accord. Calculs lourds (entraînements…) sur DELLODM, pas sur AEX.
- DELLODM : SSH par clé uniquement (ssh -o BatchMode=yes odm@192.168.1.125), JAMAIS par mot de passe.
  La clé d'AEX a une phrase secrète : si l'agent SSH est vide (ssh-add -l), demande-moi de lancer ssh-add.
- Jamais de binaire, de photo DJI ni de données tierces dans un dépôt (données dans ~/donnees_externes/,
  data/ non versionné). Demander avant de télécharger un jeu ou un modèle .pt tiers.
- Mettre à jour REPRISE.md, CLAUDE.md et docs/reprise_*.md à chaque étape. Commits en français, push
  régulier : git -c 'credential.helper=!/home/aex/.local/bin/gh auth git-credential' push
- Agents (sous-tâches) autorisés si utile.
```

Notes :
- Environnement : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` ; SDK DJI :
  `scripts/install_dji_sdk.sh <zip officiel DJI>`.
- Données hors dépôt : `~/donnees_externes/` (DTU, Zenodo 16420123, images sans panneau `negatifs_dji/`).
