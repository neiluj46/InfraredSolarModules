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
- OrthoStudio essai : worktree ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm (main + D.1 à D.6, NON fusionnée),
  instance 8001 (lancement : voir CLAUDE.md ; ORTHOSTUDIO_PROJECTS=~/OrthoStudio_essais/projets
  ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db ; journal ~/OrthoStudio_essais/8001.log).
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermique PV).

Lis d'abord : ~/OrthoStudio_test/CLAUDE.md (encadré « Priorités et attentes » en tête),
~/OrthoStudio_test/docs/detection_volumes_proposition.md (plan D.1 à D.7 et comptes rendus D.1 à D.6), puis
git log -8. Ne refais pas ce qui est fait.

Fait le 07/11/2026 — détection automatique des volumes (PRIORITÉ N° 1), branche d'essai, poussée :
- D.1 paquet cubature/ (volume, relief, batiment, fosse) ; D.2 moteur cubature/detection.py (deux échelles, arbres
  retirés par MNT + orthophoto, isolement, contour non fermé, exclusions, plans d'eau, alertes) ; D.3 essai
  Wietrznia sur DELLODM (fosse retrouvée, IoU 0,90 avec le contour manuel, 59 s, 3 Go ; carte
  ~/OrthoStudio_essais/projets/carriere_wietrznia/volumes/detection/carte_d3.png) ; D.4 service
  orthostudio/volumes_auto_service.py + routes /api/projects/{pid}/volumes_auto… (propositions.geojson, valider →
  mesures + cubatures, validation tout ou rien, par usage et marge) ; D.5 écran static/js/volumes_auto.js en tête
  de l'onglet Volumes (cocher, renommer, retoucher, valider) ; D.6 même écran en mode Lac (emprise du lever +10 m,
  contour de crête à marge 0).
- Fosse auto de Wietrznia cubée : 396 293 m³ (contour manuel du 05/11 : 366 715 m³, 8 % d'écart).
- Projet 5 de 8001 : détection D.3 injectée (calcul 1 de volumes_auto) ; mesures 16 à 21 créées par les essais.
- Chaque étape relue par un agent (sans droit d'écriture) avant commit : continuer ainsi.

PROCHAINE ÉTAPE : D.7 (feu vert déjà donné le 07/11, « on enchaîne sur le D7 ») — rapport et export QGIS :
contours retenus (mesures créées par la détection, propositions à exclure ou non) et volumes dans la section
Volumes du rapport (report_volumes.py) et dans l'export QGIS (export_qgis.py : couches des propositions et des
contours validés). Regarder d'abord ce que font déjà report_volumes.py et export_qgis.py pour les calculs Volumes
et Lac ; poser les questions métier utiles (faut-il les propositions non validées ? les objets exclus ?) avant de
coder si ce n'est pas évident ; puis tests, essai dans 8001 (projet 5), relecture par un agent, docs, commit.
Ensuite, à me proposer : fusion de la branche d'essai dans main (mon accord), puis les autres priorités.

Autres priorités (après la détection, attendre mon feu vert) :
2. Vue 3D de l'export QGIS « vraiment horrible » (l'import marche) : me demander les détails, puis corriger.
3. Tuiles 3D d'ODM (case « Modèle 3D », option 3d-tiles) : jamais vues sur un vrai traitement.
4. Plus tard : moteur GPU (MNS / nuage dense, multi-blocs), doublon vision/jaunisse.py, export QGIS étape 3.
5. En attente du drone thermique ou d'une base de R-JPEG : vrai vol thermique, SDK DJI sur DELLODM.

À faire par moi (vérifier au début : empreintes du code identiques, curl http://127.0.0.1:8001/api/calcul/test et
/api/calcul/gpu/test → code_identique) :
- Mettre DELLODM à jour sur la branche d'essai (empreinte changée depuis D.1) : pousser la branche, puis là-bas
  « cd ~/OrthoStudio && sudo bash scripts/installer_calcul_distant.sh » et « … --gpu ». Tant que ce n'est pas fait,
  calculs « sur DELLODM » refusés depuis 8001 → « Ce PC ».
- Production : jeton à saisir dans Réglages → « Service de calcul des onglets ».
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
