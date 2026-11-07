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
- OrthoStudio essai : worktree ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm (= main depuis la fusion du 07/11),
  instance 8001 (lancement : voir CLAUDE.md ; ORTHOSTUDIO_PROJECTS=~/OrthoStudio_essais/projets
  ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db ; journal ~/OrthoStudio_essais/8001.log).
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermique PV).

Lis d'abord : ~/OrthoStudio_test/CLAUDE.md (encadré « Priorités et attentes » en tête),
~/OrthoStudio_test/docs/detection_volumes_proposition.md (plan D.1 à D.7 et comptes rendus), puis git log -8.
Ne refais pas ce qui est fait.

Au démarrage, vérifier (et me le dire en une ligne) :
- instances : ss -ltnp | grep -E ":800[01]" ; 8001 est à relancer après chaque redémarrage du PC (commande dans
  CLAUDE.md, setsid nohup, journal ~/OrthoStudio_essais/8001.log) ; 8000 (production) : me demander avant.
- DELLODM : ssh-add -l ; curl http://127.0.0.1:8001/api/calcul/test et /api/calcul/gpu/test → code_identique.
- réseau : ip route get 192.168.1.125 (enp3s0f1 = câble, wlp2s0 = Wi‑Fi).

État au 07/11/2026 au soir (tout commité et poussé) :
- Détection automatique des volumes (ancienne PRIORITÉ N° 1) TERMINÉE et FUSIONNÉE dans main (ff0c96e, avance
  rapide, mon accord) : D.1 paquet cubature/ ; D.2 moteur cubature/detection.py ; D.3 essai Wietrznia sur DELLODM
  (IoU 0,90, 59 s) ; D.4 service volumes_auto_service.py + routes /api/projects/{pid}/volumes_auto… ; D.5 écran
  static/js/volumes_auto.js dans l'onglet Volumes ; D.6 mode Lac (emprise +10 m, contour de crête) ; D.7 rapport
  (colonne « Contour » auto / à la main, blocs « Détection automatique » et « Objets validés », origine dans le Lac)
  et export QGIS (couche de toutes les propositions, objets à exclure décochés, champs d'origine).
- Wietrznia (projet 5 de 8001) : fosse auto cubée 396 293 m³ (contour manuel : 366 715 m³, 8 %) ; mesures 16 à 21
  créées par les essais.
- Branches : main = ccr-0037e643-x5jvxm (~/OrthoStudio_test) ; M0 (~/OrthoStudio_m0) déjà fusionnée ; anciennes
  branches locales ccr-ec42f296-1bn5ff et vols-carto3d entièrement contenues dans main.
- Tests : suite complète verte (DELLODM + fichiers rejoués sur AEX) ; rsync vers DELLODM avec --exclude __pycache__.

PROCHAINE ÉTAPE : priorité n° 2 ci-dessous (vue 3D de l'export QGIS), après mon feu vert : me demander d'abord
les détails (projet, nuage / MNS / maillage, relief, texture).

Autres priorités (attendre mon feu vert) :
2. Vue 3D de l'export QGIS « vraiment horrible » (l'import marche) : me demander les détails, puis corriger.
3. Tuiles 3D d'ODM (case « Modèle 3D », option 3d-tiles) : jamais vues sur un vrai traitement.
4. Plus tard : moteur GPU (MNS / nuage dense, multi-blocs), doublon vision/jaunisse.py, export QGIS étape 3 ;
   détection : couche d'emprise des levers du Lac dans QGIS (origine lisible seulement dans les mesures).
5. En attente du drone thermique ou d'une base de R-JPEG : vrai vol thermique, SDK DJI sur DELLODM.

À faire par moi :
- (Fait le 07/11 au soir : DELLODM sur ff0c96e, services réinstallés, code_identique: true. Piège : pousser vers
  DELLODM sur une branche à part — git push odm@192.168.1.125:OrthoStudio main:refs/heads/maj — puis là-bas
  git merge --ff-only maj ; un push direct sur main, branche en cours d'utilisation, est refusé.)
- Production (8000) : à relancer (arrêtée par le redémarrage du PC), puis jeton dans Réglages → « Service de calcul
  des onglets ».
- Câble Ethernet d'AEX sans lien depuis le 07/11 midi (Wi‑Fi en attendant).

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
