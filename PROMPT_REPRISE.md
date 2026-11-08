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
- OrthoStudio essai : worktree ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm (= main depuis la fusion du 08/11, 79bc701),
  instance 8001 (lancement : voir CLAUDE.md ; ORTHOSTUDIO_PROJECTS=~/OrthoStudio_essais/projets
  ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db ; journal ~/OrthoStudio_essais/8001.log).
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermique PV).

Lis d'abord : ~/OrthoStudio_test/CLAUDE.md (encadré « Priorités et attentes » en tête),
~/OrthoStudio_test/docs/vue_3d_qgis.md (export QGIS 3D, 08/11) et docs/detection_volumes_proposition.md, puis
git log -8.
Ne refais pas ce qui est fait.

Au démarrage, vérifier (et me le dire en une ligne) :
- instances : ss -ltnp | grep -E ":800[01]" ; 8001 est à relancer après chaque redémarrage du PC (commande dans
  CLAUDE.md, setsid nohup, journal ~/OrthoStudio_essais/8001.log) ; 8000 (production) : me demander avant.
- DELLODM : ssh-add -l ; curl http://127.0.0.1:8001/api/calcul/test et /api/calcul/gpu/test → code_identique.
- réseau : ip route get 192.168.1.125 (enp3s0f1 = câble, wlp2s0 = Wi‑Fi).

État au 08/11/2026 (tout commité et poussé) :
- Vue 3D de l'export QGIS (ancienne priorité n° 2) TERMINÉE et FUSIONNÉE dans main (79bc701, avance rapide, mon
  accord ; /home/aex/TEST  est à jour sur le disque) : altitudes absolues, vue « OrthoStudio 3D » écrite dans le
  projet (VUE_3D dans orthostudio/export_qgis.py), seule l'orthophoto cochée à l'ouverture, tuiles Obj2Tiles légères
  (-t indispensable, texture 1024 px par tuile, octree). Validé dans QGIS 3.40 sur la maison et la carrière
  Wietrznia (fluide, maillage coché). Compte rendu : ~/OrthoStudio_test/docs/vue_3d_qgis.md.
- Tests : 15 tests de l'export QGIS verts sur AEX (PyQGIS + Obj2Tiles) ; suite complète sur DELLODM PAS relancée
  (clé SSH non chargée ce jour-là).
- Détection automatique des volumes (D.1 à D.7) : faite et fusionnée le 07/11 (ff0c96e).
- Fichiers d'essai laissés dans les exports QGIS de 8001 : maison (Essai_3D_maillage*.qgz,
  donnees/modele_3d/tuiles_2048) ; carrière (Essai_carriere_3.qgz, donnees/modele_3d/tuiles_legeres et
  tuiles_1024) : supprimables.

TOUT CE QUI RESTE À FAIRE (dans l'ordre proposé ; attendre mon feu vert pour chaque point) :
1. Suite complète des tests sur DELLODM sur 79bc701 (ssh-add d'abord), fichiers PyQGIS / geopandas / Obj2Tiles
   rejoués sur AEX.
2. DELLODM : pousser 79bc701 (git push odm@192.168.1.125:OrthoStudio main:refs/heads/maj, puis là-bas
   git merge --ff-only maj) et réinstaller les services (empreinte du code) → code_identique: true.
3. Production (8000) : à relancer par moi (./run.sh dans /home/aex/TEST ), puis jeton dans Réglages → « Service de
   calcul des onglets » ; réexporter vers QGIS les projets dont l'export date d'avant le 08/11.
4. Export QGIS de tous les modules (mon idée du 08/11) : orthophotos, indices, cartes et mesures de chaque onglet
   (agro, biomasse, jaunisses, multispectral, thermique…), pas les scripts de détection, pour que les clients
   visualisent leurs résultats dans QGIS. Faire d'abord l'inventaire de ce qui manque à l'export.
5. Couche LiDAR HD de l'IGN (nuage COPC) dans l'export QGIS, pour comparer au nuage du drone (mon idée du 08/11).
6. Tuiles 3D d'ODM (case « Modèle 3D », option 3d-tiles) : jamais vues sur un vrai traitement ; l'export les
   reconvertit désormais en tuiles légères quand Obj2Tiles est présent.
7. Plus tard : moteur GPU (MNS / nuage dense, multi-blocs), doublon vision/jaunisse.py, export QGIS étape 3 ;
   détection : couche d'emprise des levers du Lac dans QGIS.
8. En attente du drone thermique ou d'une base de R-JPEG : vrai vol thermique, SDK DJI sur DELLODM.
9. Câble Ethernet d'AEX sans lien depuis le 07/11 midi (Wi‑Fi en attendant) : à vérifier par moi.

PROCHAINE ÉTAPE : point 1 (après ssh-add), puis point 2.

Règles :
- Arrêt et rapport court à la fin de chaque point, puis attendre mon feu vert.
- DELLODM : « traite au max sur dellodm » (accord général du 07/11 soir) : détections, recalculs et suite de tests
  sur DELLODM (copie ~/essais_d1/code, conteneur orthostudio-calcul, pytest -n 8 en ~70 s : commande dans
  CLAUDE.md ; rejouer sur AEX les fichiers qui demandent pdftotext, geopandas, pycolmap, trimesh, node, RAF20).
  Aucun traitement NodeODM (photogrammétrie) sans mon accord.
- DELLODM (192.168.1.125, RTX 2080) : SSH par clé uniquement (ssh -o BatchMode=yes odm@192.168.1.125), JAMAIS par
  mot de passe. Si ssh-add -l est vide, demande-moi de lancer ssh-add. Les commandes sudo là-bas, c'est moi.
- Si besoin, des agents, et te faire superviser (relecture par un agent avant chaque commit) ; vérifier en ligne
  quand des références existent.
- Jamais de binaire, de photo DJI ni de données tierces dans un dépôt. Vols de données : disque
  /run/media/aex/600CD6D775E5D268/DATA/BASE D/.
- Mettre à jour CLAUDE.md, docs/ (et REPRISE.md pour le thermique) à chaque étape. Commits en français, push :
  git -c 'credential.helper=!/home/aex/.local/bin/gh auth git-credential' push
- Ne jamais recopier un jeton ou un mot de passe dans la conversation.
- Instance 8001 : ne pas l'arrêter avec pkill -f (tue le shell de l'agent) ; viser le PID (ss -ltnp | grep :8001),
  relancer avec setsid nohup, recharger la page après un changement JS (location.reload()).
```

Notes :
- Environnement thermique : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` ; SDK DJI :
  `scripts/install_dji_sdk.sh <zip officiel DJI>`.
- Données hors dépôt : `~/donnees_externes/` (DTU, Zenodo 16420123, images sans panneau `negatifs_dji/`).
