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
- OrthoStudio essai : worktree ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm (= main depuis la fusion du 08/11 soir,
  dernier commit : compte rendu de la fusion), instance 8001 (lancement : voir CLAUDE.md ; ORTHOSTUDIO_PROJECTS=~/OrthoStudio_essais/projets
  ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db ; journal ~/OrthoStudio_essais/8001.log).
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermique PV).

Lis d'abord : ~/OrthoStudio_test/CLAUDE.md (encadré « Priorités et attentes » en tête),
~/OrthoStudio_test/docs/export_qgis_modules.md (export QGIS de tous les modules : inventaire, mes décisions, Q.1 à
Q.6), puis git log -8.
Ne refais pas ce qui est fait.

Au démarrage, vérifier (et me le dire en une ligne) :
- instances : ss -ltnp | grep -E ":800[01]" ; 8001 est à relancer après chaque redémarrage du PC (commande dans
  CLAUDE.md, setsid nohup, journal ~/OrthoStudio_essais/8001.log) ; 8000 (production) : me demander avant.
- DELLODM : ssh-add -l ; curl http://127.0.0.1:8001/api/calcul/test et /api/calcul/gpu/test → code_identique.
- réseau : ip route get 192.168.1.125 (wlp2s0 = Wi‑Fi, état normal ; enp3s0f1 = câble, gros transferts seulement).

État au 08/11/2026 soir (tout commité et poussé sur la branche d'essai) :
- Points 1 et 2 faits : suite DELLODM sur 79bc701 (620 verts ; échecs = pdftotext / geopandas absents du conteneur,
  rejoués verts sur AEX ; 2 tests instables en -n 8 : test_biomasse_carte::test_api_parcours et
  test_detection_corrections::test_api_reglage_manuel_et_corrections) ; DELLODM sur 79bc701, conteneur 3100
  réinstallé par moi (jeton gardé).
- Point 4 en cours, Export QGIS de tous les modules (docs/export_qgis_modules.md) : Q.1 socle (07d5503), Q.2 agro /
  biomasse / points terrain (bd1083f), Q.3 vigne, verger, dégâts (80600b7, f019574 : noms de groupes lisibles, boîte
  d'export à jour), Q.4 jaunisses et frelons avec photos des suspects copiées et ouvertes dans QGIS (54bbda7),
  Q.5 thermique, anomalies PV par forme, calepinage (tables, modules, anomalies rattachées ; alerte si plan modifié
  après le rattachement) (448e426, essai sur fd 50m de démonstration ; suite DELLODM 641 verts), Q.6 photos
  géoréférencées (empreintes, centres + photo de drone et vignette ; option « Copier les photos de drone ») et aperçu
  GeoTIFF de la mosaïque rapide (dc61f94 ; test2 : 196 photos, 830 Mo ; suite DELLODM 646 verts). Export terminé.
  Mes décisions : résultats en coordonnées (jamais les algorithmes), tout ce qui est détecté (auto et main),
  jaunisses / frelons = orthophotos + points GPS + photos, thermique = ortho + défauts + calepinage, plans de vol non ;
  objectif : le client voit son projet chez lui avec QGIS (gratuit).
- Essais réels dans 8001 : projets 11 « VM derrière bureau (vigne) » et 12 « Bois (vigne) » (orthophotos copiées
  de BASE D/Photos ferme/Photos parcellaire). Bois détecté par moi (181 pieds manquants) et exporté : « ça fonctionne
  bien ». VM : écartement entre pieds à saisir, pas encore détecté. Jaunisses fd, test2, redon (projets 1 à 3)
  réexportées avec photos (~230 Mo chacune). Aucune analyse Frelons réelle dans 8001.
- DELLODM : code_identique = false depuis Q.3 (detection_service.zones modifié) → pousser la branche et relancer
  l'installateur (moi, sudo, SANS --token).
- 30 tests de l'export verts sur AEX (tests/test_export_qgis.py, test_export_qgis_photos.py, PyQGIS) ; suite
  complète sur DELLODM pas relancée depuis Q.2.

TOUT CE QUI RESTE À FAIRE (dans l'ordre proposé ; attendre mon feu vert pour chaque point) :
4. Export QGIS de tous les modules : terminé (Q.1 à Q.6) et fusionné dans main le 08/11 (avance rapide).
   Reste : DELLODM (installateur, moi : sudo, SANS --token), production (point 3).
3. Production (8000) : à relancer par moi (./run.sh dans /home/aex/TEST ), jeton dans Réglages → « Service de
   calcul des onglets » ; réexporter vers QGIS les projets dont l'export date d'avant la fusion.
5. Couche LiDAR HD de l'IGN (nuage COPC) dans l'export QGIS, pour comparer au nuage du drone.
6. Tuiles 3D d'ODM (case « Modèle 3D », option 3d-tiles) : jamais vues sur un vrai traitement.
7. Plus tard : moteur GPU (MNS / nuage dense, multi-blocs), doublon vision/jaunisse.py ; détection : couche
   d'emprise des levers du Lac dans QGIS ; option « export sans photos d'origine » si trop lourd.
8. En attente du drone thermique ou d'une base de R-JPEG : vrai vol thermique, SDK DJI sur DELLODM.
9. Réseau : Wi‑Fi par défaut ; câble Ethernet d'AEX branché seulement pour les très gros transferts.

Données de test sur DELLODM : ~/BD Photos (copie partielle de BASE D par moi, 08/11 ; à utiliser pour gagner du
temps).

PROCHAINE ÉTAPE : installateur DELLODM et production 8000 (moi), puis point 5 (LiDAR HD de l'IGN) après mon feu vert.
Répondre en français (rappel de l'utilisateur du 08/11).

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
