# Prompt de reprise — OrthoStudio + thermographie PV (à coller dans Claude Code après /clear)

Version courte à coller :

```
Lis ~/InfraredSolarModules/PROMPT_REPRISE.md (bloc « Prompt complet ») et suis-le.
```

## Prompt complet

```
Rôle : agent développeur sur mes dépôts, en local sur mon PC Linux (AEX). Tout en français : échanges, code,
commits. Je pilote souvent depuis mon téléphone : rapports courts, lisibles sur mobile.

Dépôts et copies :
- OrthoStudio production : /home/aex/TEST  (espace final), branche main, port 8000. JAMAIS y toucher sans mon
  accord explicite (fusions comprises).
- OrthoStudio essai : worktree ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm (= main au 07/11), instance 8001
  (lancement : voir CLAUDE.md ; ORTHOSTUDIO_PROJECTS=~/OrthoStudio_essais/projets
  ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db).
- OrthoStudio essai GPU « M0 » : worktree ~/OrthoStudio_m0, branche ccr-1b5af7f6-baowsz (main fusionné dedans
  le 07/11, non fusionnée dans main). Sur DELLODM : ~/orthostudio-m0/depot + environnement ~/orthostudio-m0.
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermographie PV).

Lis d'abord : ~/OrthoStudio_test/CLAUDE.md, ~/OrthoStudio_m0/docs/reprise_moteur_gpu.md (section 07/11),
~/OrthoStudio_test/docs/fusion_essai_2026-11-07.md, ~/InfraredSolarModules/REPRISE.md (« À faire »), puis
git log -5 des dépôts. Ne refais pas ce qui est fait.

Fait le 07/11/2026 :
- État des lieux complet d'OrthoStudio ; essai (export QGIS, Lac, 3d-tiles, anomalies PV, calepinage C.1-C.5)
  validé par moi et FUSIONNÉ dans main (avance rapide, 576 tests), poussé ; contourpy installé en production.
- Service de calcul des onglets INSTALLÉ sur DELLODM (conteneur orthostudio-calcul, port 3100, jeton ; dépôt
  ~odm/OrthoStudio mis à jour par « git -C "/home/aex/TEST " push odm@192.168.1.125:OrthoStudio main » puis je
  relance l'installateur avec sudo ; empreinte du code identique vérifiée). Correctif .dockerignore (vols/).
  Il me reste à le régler dans Réglages → « Service de calcul des onglets » (http://192.168.1.125:3100 + jeton).
- Banc GPU M0 sur la RTX 2080 (COLMAP / GLOMAP) : FS (46 photos), P4M RTK « Emilien » (146) et « Maïs » (455,
  = banc du 31/10). Maïs : M0 4 min 23, 455/455 en 1 bloc, 10 cm du RTK des photos ; ODM rapide 8 min 38,
  4 blocs ; ODM « gpu » 21 min, 4 blocs. Alignement GLOMAP sur processeur = 75 % du temps de M0. Orthophotos
  décalées de 0,5 à 1,9 m entre elles : lequel est juste, NON TRANCHÉ.
- Orthophotos des bancs rapatriées (~/OrthoStudio_essais/jeux/banc_m0/<vol>/) et importées dans 8001 :
  projet 8 « Banc M0 — Emilien_P4M_RTK », projet 9 « Banc M0 — Mais_P4M_RTK » (m0_rapide, odm_rapide, odm_gpu).

Prochaine étape (attendre mon feu vert) :
1. Comparer à l'œil les trois orthophotos des projets 8 et 9 sur les traces de pulvérisateur / repères ;
   je dirai laquelle colle. Puis décider : M1 (M0 dans OrthoStudio : paquet photogrammetrie/, choix « Moteur »
   à l'écran Traitement) ou garder ODM ; sort de la qualité ODM « gpu » (plus lente, pas mieux : la retirer ?).
2. Points ouverts ailleurs : vrai vol thermique (data/raw_rjpegs vide) pour régler le recalage du calepinage ;
   tuiles 3d-tiles jamais vues sur un vrai traitement ; vue 3D de l'export QGIS à regarder ; paquet cubature/ ;
   doublon vision/jaunisse.py ; export QGIS étape 3 ; SDK DJI absent de DELLODM (calcul thermique distant).
3. Garder l'instance 8001 et ~/OrthoStudio_essais (oui conseillé).

Règles :
- Arrêt et rapport court à la fin de chaque point, puis attendre mon feu vert.
- Aucun traitement NodeODM ni calcul lourd sur DELLODM sans mon accord. Calculs lourds sur DELLODM, pas sur AEX.
- DELLODM (192.168.1.125, RTX 2080) : SSH par clé uniquement (ssh -o BatchMode=yes odm@192.168.1.125), JAMAIS par
  mot de passe. Si ssh-add -l est vide, demande-moi de lancer ssh-add. Les commandes sudo là-bas, c'est moi.
- Jamais de binaire, de photo DJI ni de données tierces dans un dépôt. Vols de données : disque
  /run/media/aex/600CD6D775E5D268/DATA/BASE D/ (Emilien, pix4multispectal/Mais…), copies sur DELLODM
  ~/vols_banc/ (photos aplaties <sortie>_<nom> : moteur et ODM lisent un seul niveau).
- Mettre à jour CLAUDE.md, docs/reprise_*.md (et REPRISE.md pour le thermique) à chaque étape. Commits en
  français, push : git -c 'credential.helper=!/home/aex/.local/bin/gh auth git-credential' push
- Ne jamais recopier un jeton ou un mot de passe dans la conversation.
- Instance 8001 : ne pas l'arrêter avec pkill -f "orthostudio --port 8001" (tue le shell de l'agent) ; viser le
  PID, relancer avec setsid nohup, recharger la page après un changement JS.
```

Notes :
- Environnement thermique : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` ; SDK DJI :
  `scripts/install_dji_sdk.sh <zip officiel DJI>`.
- Données hors dépôt : `~/donnees_externes/` (DTU, Zenodo 16420123, images sans panneau `negatifs_dji/`).
