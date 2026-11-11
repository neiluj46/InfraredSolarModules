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
  accord explicite (fusions comprises). main = 2d82491 (audit du 11/11 fusionné le 11/11) ; la branche d'essai a 0a771e8 en plus (point 7 du 11/11, non fusionné).
- OrthoStudio essai : worktree ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm (= 2d82491, poussée), instance 8001 (lancement :
  voir CLAUDE.md ; ORTHOSTUDIO_PROJECTS=~/OrthoStudio_essais/projets ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db ;
  journal ~/OrthoStudio_essais/8001.log).
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermique PV, ce prompt).

Lis d'abord : ~/OrthoStudio_test/CLAUDE.md (encadré « Priorités et attentes » en tête), docs/audit_2026-11-11.md (audit et
corrections du 11/11, À LIRE EN PREMIER), docs/photos_dellodm.md,
docs/lidar_hd_ign.md et docs/export_qgis_modules.md (derniers travaux), puis git log -8. Ne refais pas ce qui est fait.

Au démarrage, vérifier (et me le dire en une ligne) :
- instances : ss -ltnp | grep -E ":800[01]" ; 8001 est à relancer après chaque redémarrage du PC (commande dans
  CLAUDE.md, setsid nohup, journal ~/OrthoStudio_essais/8001.log) ; 8000 (production) : me demander avant.
- DELLODM : ssh-add -l ; curl http://127.0.0.1:8001/api/calcul/test et /api/calcul/gpu/test → code_identique.
- réseau : ip route get 192.168.1.125 (wlp2s0 = Wi‑Fi, état normal ; enp3s0f1 = câble, gros transferts seulement).

AUDIT DU 11/11/2026 (demande « regarde tout le projet… erreurs, justesse, efficacité » puis « corrige moi tout ça ») :
- 8 audits par agents (détection orthophoto, photos brutes / géoréférencement, volumes / Lac, azote / biomasse,
  thermique / calepinage / vols, cœur / NodeODM, export QGIS / rapports, interface JS), puis corrections par lots,
  chaque lot relu par un agent avant commit : A 2c57d2a (chiffres faux), D ab19423 (pertes de données, NodeODM,
  export, sécurité), 13c8a76 (imports Web Mercator), E b86e6b4 (interface), B 11f1d78 (calepinage, vols),
  C dfda669 (jaunisses, Vision, mosaïque), G 0ae162f (détection orthophoto), H bb08206 (volumes, Lac, retenue),
  a2cfee2 (WeasyPrint rendait PIL tolérant aux photos tronquées), 2d82491 (zonage azote 85× plus rapide).
- Suite AEX : 850 réussis, 0 échec (a2cfee2) ; agro 119 verts après 2d82491. 8001 relancée avec ce code.
  Parcours de l'interface sur 8001 (12 projets × 15 onglets) : aucune erreur JS.
- NON FUSIONNÉ dans main : l'utilisateur a dit « ça me semble bon, on fusionnera plus tard » (11/11).
- DELLODM : services à réinstaller (sudo, SANS --token, par l'utilisateur) après la fusion ; tant que ce n'est pas
  fait, un calcul « sur DELLODM » refuse (empreinte du code différente) → choisir « Ce PC » (vu le 11/11, normal).
- Changements de comportement et choix laissés à l'utilisateur : voir docs/audit_2026-11-11.md (taux de dégâts sur
  parcelle − exclusions, jaunisses sur le plan du feuillage 1,5 m, rangées du calepinage par voisinage, garde
  Host/Origin du serveur local + ORTHOSTUDIO_HOTES ; choix ouverts : facteur d'échelle Lambert-93 du Lac,
  tache_max_m2 des jaunisses, décodage MPO, seuils des jaunisses en cm).

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
- Photos de DELLODM dans l'explorateur (08/11, 7b46b81, fusionné dans main) : rubrique « Autres machines », montage
  SSHFS lecture seule de odm@192.168.1.125:BD Photos (orthostudio/distants.py), ssh-add après chaque démarrage d'AEX ;
  essayé sur Redon2 (179 photos). Mes essais cette semaine.
- Tests : suite DELLODM 682 verts sur 7b46b81 (13 échecs connus rejoués verts sur AEX) ; avant : 663 verts sur 36ee2e0 ; 13 échecs connus (pdftotext / geopandas absents du conteneur)
  rejoués verts sur AEX ; 2 tests instables en -n 8 (test_biomasse_carte::test_api_parcours,
  test_detection_corrections::test_api_reglage_manuel_et_corrections).
- Essais réels dans 8001 : 2 test2 (photos, mosaïque ; ses photos de ~/Images ont été retirées par moi le 08/11 :
  export sans photos), 3 redon et 6 Plan 3d Maison (LiDAR HD téléchargé : décalage −54,8 m « approché » à Redon,
  −18,4 m à la maison), 4 fd 50m (calepinage de démonstration, rattachement à relancer), 11 VM et 12 Bois (vigne).
  Vue 3D avec le LiDAR : pas encore essayée par moi dans le navigateur.
- DELLODM : services réinstallés par moi le 08/11 (code_identique = true) ; à relancer après chaque fusion qui
  touche le code des calculs (sudo, SANS --token). Ma base de photos : ~/BD Photos sur DELLODM (53 Go, BASE D, BN FE, CLients), à utiliser pour les essais.
- Sauvegarde du 08/11 : DELLODM ~/sauvegardes/2026-11-08/ (git bundle des deux dépôts, essais.db, CLAUDE.md, ce
  prompt, mémoire de Claude).

TOUT CE QUI RESTE À FAIRE (dans l'ordre proposé ; attendre mon feu vert pour chaque point) :
0. FAIT le 11/11 (demande « fais tous les points listés ») : audit fusionné dans main (avance rapide 7b46b81 →
   2d82491, poussé sur GitHub et sur DELLODM ~odm/OrthoStudio). Suite DELLODM : 784 verts + 13 échecs connus rejoués
   verts sur AEX (52/52). RESTE (lui) : réinstaller les services DELLODM (sudo, SANS --token ; d'ici là
   code_identique = false → « Ce PC »), production 8000.
3. Moi : installateur DELLODM (sudo, SANS --token) ; production 8000 (./run.sh dans /home/aex/TEST , jeton dans
   Réglages → « Service de calcul des onglets ») ; réexporter vers QGIS les projets exportés avant le 08/11.
   Essayer dans 8001 : vue 3D + LiDAR HD (et la nouvelle case « Altitudes recalées sur l'IGN »), surcouche LiDAR
   de la carte, case « orthophoto pleine résolution ».
6. FAIT le 11/11 : traitement 8 du projet 6 (photos de DELLODM par SSHFS, ultra + Modèle 3D, DELLODM, 973 s) ;
   option partie (journal « 3d_tiles: True »), 3d_tiles/model/ rapatrié (40 Mo, une tuile par niveau), mais tuiles
   d'ODM MAL PLACÉES (enveloppe à 0 m d'altitude, 90 m au sud ; Obj2Tiles local : 89,9 m au-dessus du site, juste)
   → Obj2Tiles reste prioritaire, alerte si repli. Détail : docs/vue_3d_qgis.md. Anciens produits :
   ortho_avant_3dtiles_2026-11-11/. DÉCISION À PRENDRE (lui) : retirer l'option 3d-tiles du traitement ou la garder.
   Pas encore ouvert dans QGIS à l'œil.
7. FAIT le 11/11 par 4 agents (worktrees), relus par 2 agents, branche d'essai 0a771e8 (NON fusionnée) :
   doublon vision/jaunisse.py (délègue au critère de l'onglet, réglage jaunisse.critere) ; couche « Emprise du
   lever » du Lac dans QGIS ; LiDAR HD des DROM (Guadeloupe EPSG:5490, Réunion 2975, Mayotte 4471 ; altitudes du
   WFS) ; recalage vertical du drone sur l'IGN (option par projet, désactivée par défaut, fichiers jamais réécrits,
   coupé si le modèle du drone change) ; orthophoto pleine résolution des mosaïques multispectrales (COG DEFLATE
   16 bits). Suite DELLODM : 792 verts + 13 connus. RESTE : moteur GPU (MNS / nuage dense, multi-blocs).
   Questions ouvertes : seuil 0,5 m du recalage ; recalage par plan (MNS basculé) ; recaler aussi le multispectral ;
   La Désirade (WFS GUAD2008LD contre descriptif IGN 1992 LD). Choix de l'audit toujours ouverts (Lac Lambert-93,
   tache_max_m2, MPO, seuils en cm).
8. En attente du drone thermique ou d'une base de R-JPEG : vrai vol thermique (recalage du calepinage), SDK DJI sur
   DELLODM.
9. Réseau : Wi‑Fi par défaut ; câble Ethernet d'AEX branché seulement pour les très gros transferts.

RANGEMENT D'AEX fait le 08/11 (~/Scripts, ~/Notes, ~/Documents) et WebODM retiré entièrement (projets à refaire dans OrthoStudio) :
~/OrthoStudio_notes/nettoyage_2026-11-08.txt.
PROCHAINE ÉTAPE : essais de l'utilisateur sur 8001 (branche 0a771e8), puis fusion dans main avec son accord, réinstallation DELLODM et 8000 (lui) ; décision sur l'option 3d-tiles ; moteur GPU plus tard.
redémarrage du PC.
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
