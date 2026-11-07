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

État au 07/11/2026 (tout est poussé ; 576 tests OrthoStudio réussis) :
- Chaîne thermique complète écrite et testée, mais JAMAIS essayée sur un vrai vol (pas encore de R-JPEG au-dessus
  de panneaux) : R-JPEG DJI → températures (scripts/extract_data.py) → modules détectés (détecteur maison PyTorch,
  F1 0,90) → forme de l'anomalie (anomalies.py, seuil ΔT ≥ 3 K) → polygones au sol (export_orthostudio.py ; option
  --tous pour garder les modules sains, nécessaire au recalage) → import dans l'onglet Thermique d'OrthoStudio.
- PLAN DE CALEPINAGE terminé (OrthoStudio, onglet Thermique, détail : docs/calepinage_proposition.md) :
  ✅ C.1 calepinage.py : tables (3 clics + lignes × colonnes), rangées, numérotation [zone-]R01-T03-L2-C14 ;
  ✅ C.2 API + écran calepinage.js : saisie, répéter, retirer des modules, inversions ;
  ✅ C.3 calepinage_recalage.py : recalage Hough + Kabsch des modules thermiques sur le plan, sûr / ambigu /
     hors plan, décalage manuel ;
  ✅ C.4 livrables : colonne « Module » + statut dans le rapport PDF / Excel (a), planche du plan dans le
     rapport : vue d'ensemble + zooms par rangée, positions recalées (b), exports GeoJSON WGS 84 / DXF R12
     Lambert 93 du plan et CSV / Excel des anomalies (c) — calepinage_export.py ;
  ✅ C.5 calepinage_client.py : import CSV identifiant;id_client;chaine;onduleur + modèle à remplir ; dans le
     rapport, « Module » garde l'identifiant généré et « Réf. client » / « Chaîne / onduleur » s'ajoutent (décision
     validée le 07/11).
- Démo FICTIVE dans le projet 4 (« fd 50m ») de l'instance 8001 : rapport PV, plan d'une table 3 × 12 décalé de
  1,5 / −1,2 m (recalage « ambigu », attendu), références client FICTIF-001… importées.

Points ouverts (aucune tâche imposée : attendre mes consignes) :
1. Essai sur un vrai vol : R-JPEG dans ~/InfraredSolarModules/data/raw_rjpegs/, export avec --tous, puis
   régler les seuils du recalage (ECART_MIN = 5 modules, 1 %, MARGE_BORD 20 %) — réglés sur synthèse seulement.
2. Essai de distance sur cible (températures) ; DXF à ouvrir dans AutoCAD / Covadis (relu par GDAL seulement).
3. Limites connues : tables non déplaçables, pas d'annulation dans la saisie ; rattachement à relancer à la main
   si le plan change (alerte dans le rapport) ; références client attachées à l'identifiant généré (changer la
   numérotation les déplace) ; zooms de la planche limités à 12 ; pas de planche du plan seul ; import DXF du
   plan client non fait.
4. Un test instable hors calepinage dans la suite OrthoStudio (1 échec isolé le 07/11, réussi à la relance, non
   identifié).
- Calculs lourds sur DELLODM (192.168.1.125, RTX 2080, Docker) : scripts/entrainer_dellodm.sh. Le 07/11 j'en avais
  besoin pour autre chose : demander avant tout calcul dessus.

Règles :
- Arrêt et rapport court à la fin de chaque point, puis attendre mon feu vert.
- Aucun traitement NodeODM sans mon accord. Calculs lourds (entraînements…) sur DELLODM, pas sur AEX.
- DELLODM : SSH par clé uniquement (ssh -o BatchMode=yes odm@192.168.1.125), JAMAIS par mot de passe.
  La clé d'AEX a une phrase secrète : si l'agent SSH est vide (ssh-add -l), demande-moi de lancer ssh-add.
- Jamais de binaire, de photo DJI ni de données tierces dans un dépôt (données dans ~/donnees_externes/,
  data/ non versionné). Demander avant de télécharger un jeu ou un modèle .pt tiers.
- Mettre à jour REPRISE.md, CLAUDE.md, docs/calepinage_proposition.md et docs/reprise_*.md à chaque
  étape. Commits en français, push régulier : git -c 'credential.helper=!/home/aex/.local/bin/gh auth git-credential' push
- Agents (sous-tâches) autorisés si utile.
- Instance 8001 : ne pas l'arrêter avec pkill -f "orthostudio --port 8001" (le motif tue aussi le shell de
  l'agent) ; viser le PID, relancer avec setsid nohup, recharger la page (location.reload) après un changement JS.
```

Notes :
- Environnement : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` ; SDK DJI :
  `scripts/install_dji_sdk.sh <zip officiel DJI>`.
- Données hors dépôt : `~/donnees_externes/` (DTU, Zenodo 16420123, images sans panneau `negatifs_dji/`).
