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
~/OrthoStudio_test/CLAUDE.md, ~/OrthoStudio_test/docs/calepinage_proposition.md (décisions, avancement, risques)
et ~/OrthoStudio_test/docs/reprise_session_2026-11-06.md, puis git log -8 des deux dépôts. Ne refais pas ce qui
est fait.

État au 06/11/2026 au soir (tout est poussé) :
- Chaîne thermique complète écrite et testée, mais JAMAIS essayée sur un vrai vol (pas encore de R-JPEG au-dessus
  de panneaux) : R-JPEG DJI → températures (scripts/extract_data.py) → modules détectés (détecteur maison PyTorch)
  → forme de l'anomalie (anomalies.py, seuil ΔT ≥ 3 K) → polygones au sol (export_orthostudio.py, option --tous
  pour garder les modules sains) → import dans l'onglet Thermique d'OrthoStudio, section du rapport PDF / Excel.
- PLAN DE CALEPINAGE (OrthoStudio, onglet Thermique), décisions prises avec moi : numérotation générée
  [zone-]R01-T03-L2-C14 (ordre de lecture nord en haut) + import client plus tard ; module + table (chaîne /
  onduleur = champs client) ; tables saisies sur l'orthophoto couleur ; livrables PDF + identifiant dans le
  tableau, CSV / Excel, GeoJSON / DXF.
  ✅ C.1 orthostudio/calepinage.py (grille, rangées, numérotation, répéter) ;
  ✅ C.2 API + écran static/js/calepinage.js (saisie 3 clics, répéter, retirer des modules, inversions) ;
  ✅ C.3 orthostudio/calepinage_recalage.py (recalage Hough + Kabsch des modules thermiques sur le plan,
     sûr / ambigu / hors plan, décalage manuel) + bloc « Rattacher les anomalies au plan ».
  Seuils d'ambiguïté prudents, réglés sur synthèse seulement.
- Démo FICTIVE dans le projet 4 de l'instance 8001 (rapport PV + plan d'une table 3 × 12 décalé de 1,5 / −1,2 m).
- Calculs lourds sur DELLODM (192.168.1.125, RTX 2080, Docker) : scripts/entrainer_dellodm.sh.

Calepinage C.4 LIVRABLES fait le 07/11 (docs/calepinage_proposition.md) : C.4a colonne « Module » + statut dans la
section « Anomalies PV » du rapport et l'Excel ; C.4b planche du plan dans le rapport (vue d'ensemble + zooms par
rangée) ; C.4c exports GeoJSON / DXF Lambert 93 du plan et CSV / Excel des anomalies (onglet Thermique).
C.5 ✅ (07/11) import CSV du client (identifiant;id_client;chaine;onduleur) : calepinage terminé.
Points ouverts : essai sur un vrai vol (photos à déposer dans
~/InfraredSolarModules/data/raw_rjpegs/, exporter avec --tous) pour régler les seuils du recalage ; essai de
distance sur cible ; les tables ne se déplacent pas, pas d'annulation dans l'écran de saisie.

Règles :
- Arrêt et rapport court à la fin de chaque point, puis attendre mon feu vert.
- Aucun traitement NodeODM sans mon accord. Calculs lourds (entraînements…) sur DELLODM, pas sur AEX.
- DELLODM : SSH par clé uniquement (ssh -o BatchMode=yes odm@192.168.1.125), JAMAIS par mot de passe.
  La clé d'AEX a une phrase secrète : si l'agent SSH est vide (ssh-add -l), demande-moi de lancer ssh-add.
- Jamais de binaire, de photo DJI ni de données tierces dans un dépôt (données dans ~/donnees_externes/,
  data/ non versionné). Demander avant de télécharger un jeu ou un modèle .pt tiers.
- Mettre à jour REPRISE.md, CLAUDE.md, docs/calepinage_proposition.md et docs/reprise_*.md à chaque étape. Commits en français, push
  régulier : git -c 'credential.helper=!/home/aex/.local/bin/gh auth git-credential' push
- Agents (sous-tâches) autorisés si utile.
- Instance 8001 : ne pas l'arrêter avec pkill -f "orthostudio --port 8001" (le motif tue aussi le shell de
  l'agent) ; viser le PID, relancer avec setsid nohup, recharger la page (location.reload) après un changement JS.
```

Notes :
- Environnement : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` ; SDK DJI :
  `scripts/install_dji_sdk.sh <zip officiel DJI>`.
- Données hors dépôt : `~/donnees_externes/` (DTU, Zenodo 16420123, images sans panneau `negatifs_dji/`).
