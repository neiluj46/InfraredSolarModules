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
  accord explicite (fusions comprises). main = 36ee2e0 (08/11 soir), identique à la branche d'essai.
- OrthoStudio essai : worktree ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm (= main), instance 8001 (lancement :
  voir CLAUDE.md ; ORTHOSTUDIO_PROJECTS=~/OrthoStudio_essais/projets ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db ;
  journal ~/OrthoStudio_essais/8001.log).
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermique PV, ce prompt).

Lis d'abord : ~/OrthoStudio_test/CLAUDE.md (encadré « Priorités et attentes » en tête), docs/lidar_hd_ign.md et
docs/export_qgis_modules.md (derniers travaux), puis git log -8. Ne refais pas ce qui est fait.

Au démarrage, vérifier (et me le dire en une ligne) :
- instances : ss -ltnp | grep -E ":800[01]" ; 8001 est à relancer après chaque redémarrage du PC (commande dans
  CLAUDE.md, setsid nohup, journal ~/OrthoStudio_essais/8001.log) ; 8000 (production) : me demander avant.
- DELLODM : ssh-add -l ; curl http://127.0.0.1:8001/api/calcul/test et /api/calcul/gpu/test → code_identique.
- réseau : ip route get 192.168.1.125 (wlp2s0 = Wi‑Fi, état normal ; enp3s0f1 = câble, gros transferts seulement).

État au 08/11/2026 soir (tout commité, poussé et fusionné dans main ; sauvegarde sur DELLODM) :
- Fait et fusionné : détection automatique des volumes (D.1 à D.7), vue 3D de l'export QGIS, export QGIS de tous
  les modules (Q.1 à Q.6 : agro, biomasse, points terrain, vigne, verger, dégâts, jaunisses et frelons avec photos,
  thermique + anomalies PV + calepinage, photos géoréférencées avec option « Copier les photos de drone »), point 5
  LiDAR HD de l'IGN (extrait COPC de l'emprise, vue 3D superposée au drone avec décalage vertical, surcouche de tuiles
  sur la carte, couches COPC et tuiles en ligne dans l'export) et orthophoto pleine résolution des mosaïques de
  photos à l'export (option cochée, jamais bloquante).
  Mes décisions pour l'export : résultats en coordonnées (jamais les algorithmes), tout ce qui est détecté (auto et
  main), jaunisses / frelons = orthophotos + points GPS + photos, thermique = ortho + défauts + calepinage, plans de
  vol non ; objectif : le client voit son projet chez lui avec QGIS (gratuit).
- Tests : suite DELLODM 663 verts sur 36ee2e0 ; 13 échecs connus (pdftotext / geopandas absents du conteneur)
  rejoués verts sur AEX ; 2 tests instables en -n 8 (test_biomasse_carte::test_api_parcours,
  test_detection_corrections::test_api_reglage_manuel_et_corrections).
- Essais réels dans 8001 : 2 test2 (photos, mosaïque ; ses photos de ~/Images ont été retirées par moi le 08/11 :
  export sans photos), 3 redon et 6 Plan 3d Maison (LiDAR HD téléchargé : décalage −54,8 m « approché » à Redon,
  −18,4 m à la maison), 4 fd 50m (calepinage de démonstration, rattachement à relancer), 11 VM et 12 Bois (vigne).
  Vue 3D avec le LiDAR : pas encore essayée par moi dans le navigateur.
- DELLODM : code_identique = false (code des services plus ancien) → installateur à relancer par moi (sudo, SANS
  --token). Ma base de photos : ~/BD Photos sur DELLODM (53 Go, BASE D, BN FE, CLients), à utiliser pour les essais.
- Sauvegarde du 08/11 : DELLODM ~/sauvegardes/2026-11-08/ (git bundle des deux dépôts, essais.db, CLAUDE.md, ce
  prompt, mémoire de Claude).

TOUT CE QUI RESTE À FAIRE (dans l'ordre proposé ; attendre mon feu vert pour chaque point) :
3. Moi : installateur DELLODM (sudo, SANS --token) ; production 8000 (./run.sh dans /home/aex/TEST , jeton dans
   Réglages → « Service de calcul des onglets ») ; réexporter vers QGIS les projets exportés avant le 08/11.
   Essayer dans 8001 : vue 3D + LiDAR HD, surcouche LiDAR de la carte, case « orthophoto pleine résolution ».
6. Tuiles 3D d'ODM (case « Modèle 3D », option 3d-tiles) : jamais vues sur un vrai traitement (traitement NodeODM :
   mon accord).
7. Plus tard : moteur GPU (MNS / nuage dense, multi-blocs), doublon vision/jaunisse.py ; détection : couche
   d'emprise des levers du Lac dans QGIS ; LiDAR HD : DOM (UTM) non gérés, recalage du drone sur l'IGN (pas
   seulement l'affichage) ; mosaïque multispectrale : orthophoto pleine résolution (aujourd'hui RVB seulement).
8. En attente du drone thermique ou d'une base de R-JPEG : vrai vol thermique (recalage du calepinage), SDK DJI sur
   DELLODM.
9. Réseau : Wi‑Fi par défaut ; câble Ethernet d'AEX branché seulement pour les très gros transferts.

PROCHAINE ÉTAPE : mes essais (point 3), puis point 6 (tuiles 3D d'ODM) après mon feu vert.
Répondre TOUJOURS en français, même après un long travail (rappel du 08/11).

Règles :
- Arrêt et rapport court à la fin de chaque point, puis attendre mon feu vert.
- DELLODM : « traite au max sur dellodm » (accord général du 07/11 soir) : détections, recalculs et suite de tests
  sur DELLODM (copie ~/essais_d1/code, conteneur orthostudio-calcul, pytest -n 8 en ~70 s : commande dans
  CLAUDE.md ; rejouer sur AEX les fichiers qui demandent pdftotext, geopandas, pycolmap, trimesh, node, RAF20).
  Aucun traitement NodeODM (photogrammétrie) sans mon accord.
- DELLODM (192.168.1.125, RTX 2080) : SSH par clé uniquement (ssh -o BatchMode=yes odm@192.168.1.125), JAMAIS par
  mot de passe. Si ssh-add -l est vide, demande-moi de lancer ssh-add. Les commandes sudo là-bas, c'est moi.
- Si besoin, des agents, et te faire superviser (relecture par un agent avant chaque commit) ; vérifier en ligne
  quand des références existent. Pour tester, prends des projets déjà traités (gagner du temps).
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
