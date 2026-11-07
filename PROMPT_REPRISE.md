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
- OrthoStudio essai : worktree ~/OrthoStudio_test, branche ccr-0037e643-x5jvxm (= main au 07/11 soir), instance 8001
  (lancement : voir CLAUDE.md ; ORTHOSTUDIO_PROJECTS=~/OrthoStudio_essais/projets
  ORTHOSTUDIO_DB=~/OrthoStudio_essais/essais.db ; journal ~/OrthoStudio_essais/8001.log).
- Branche GPU « M0 » (ccr-1b5af7f6-baowsz, worktree ~/OrthoStudio_m0) : FUSIONNÉE dans main le 07/11, terminée.
- InfraredSolarModules : ~/InfraredSolarModules, branche ccr-f0a48b31-r292tn (thermique PV).

Lis d'abord : ~/OrthoStudio_test/CLAUDE.md (encadré « Priorités et attentes » en tête),
~/OrthoStudio_test/docs/fusion_m1_2026-11-07.md, ~/OrthoStudio_test/docs/m1_proposition.md,
~/OrthoStudio_test/docs/reprise_cubature_relief.md (fin : détection automatique), puis git log -5. Ne refais pas
ce qui est fait.

Fait le 07/11/2026 :
- Essai (QGIS, Lac, 3d-tiles, anomalies PV, calepinage) puis moteur GPU (M1) fusionnés dans main, poussés.
- Moteur « GPU DELLODM » (COLMAP / GLOMAP) à l'écran Traitement : maïs P4M 455 / 455 photos en 1 bloc en 4 min 26
  (ODM rapide : 8 min 38, 4 blocs), écart 10 cm au RTK des photos. Orthophoto RVB seule (pas de MNS / modèle 3D).
  Qualité ODM « gpu » gardée. M0 au processeur sur AEX : non (NodeODM classique sur le terrain).
- DELLODM : service des onglets (port 3100) et service GPU (port 3101, conteneur orthostudio-calcul-gpu), même
  jeton ; mise à jour = « git -C "/home/aex/TEST " push odm@192.168.1.125:OrthoStudio main » puis, sur DELLODM,
  dans ~/OrthoStudio : « sudo bash scripts/installer_calcul_distant.sh » et « … --gpu » (c'est moi). Empreinte du
  code identique exigée (sinon calculs refusés).
- Réseau : câble Ethernet AEX ↔ DELLODM (switch Netgear) = 941 Mbit/s quand il est branché ; Wi‑Fi ≈ 70 Mbit/s.

À faire par moi au 07/11 soir (vérifier au début : empreintes identiques, jeton) :
- DELLODM : « cd ~/OrthoStudio && sudo bash scripts/installer_calcul_distant.sh » (service des onglets 3100 encore
  au code d'avant la fusion ; le service GPU 3101 est déjà à jour, empreinte a144670e391e8373).
- Production : jeton à saisir dans Réglages → « Service de calcul des onglets » (8001 l'a déjà).
- Câble Ethernet d'AEX sans lien depuis midi le 07/11 (Wi‑Fi en attendant).

Prochaine étape (attendre mon feu vert) :
1. PRIORITÉ N° 1 : détection automatique des volumes (tas / fosses des cubages de carrière, Lac), à côté des
   onglets Volumes et Lac. Poser d'abord les questions métier, puis proposer un plan par étapes.
2. Vue 3D de l'export QGIS « vraiment horrible » (l'import marche) : me demander les détails, puis corriger.
3. Tuiles 3D d'ODM (case « Modèle 3D », option 3d-tiles) : jamais vues sur un vrai traitement (court traitement
   sur DELLODM avec mon accord).
4. Plus tard : moteur GPU (MNS / nuage dense, assemblage multi-blocs), paquet cubature/, doublon vision/jaunisse.py,
   export QGIS étape 3.
5. En attente du drone thermique (plusieurs semaines) ou d'une base de R-JPEG : vrai vol thermique, SDK DJI sur
   DELLODM.

Règles :
- Arrêt et rapport court à la fin de chaque point, puis attendre mon feu vert.
- Aucun traitement NodeODM ni calcul lourd sur DELLODM sans mon accord. Calculs lourds sur DELLODM, pas sur AEX.
- DELLODM (192.168.1.125, RTX 2080) : SSH par clé uniquement (ssh -o BatchMode=yes odm@192.168.1.125), JAMAIS par
  mot de passe. Si ssh-add -l est vide, demande-moi de lancer ssh-add. Les commandes sudo là-bas, c'est moi.
- Jamais de binaire, de photo DJI ni de données tierces dans un dépôt. Vols de données : disque
  /run/media/aex/600CD6D775E5D268/DATA/BASE D/ (Emilien, pix4multispectal/Mais…). Vols en sous-dossiers : l'import
  Photos d'OrthoStudio les réunit (sous-dossiers cochés, noms préfixés par le dossier).
- Mettre à jour CLAUDE.md, docs/reprise_*.md (et REPRISE.md pour le thermique) à chaque étape. Commits en
  français, push : git -c 'credential.helper=!/home/aex/.local/bin/gh auth git-credential' push
- Ne jamais recopier un jeton ou un mot de passe dans la conversation.
- Instance 8001 : ne pas l'arrêter avec pkill -f "orthostudio --port 8001" (tue le shell de l'agent) ; viser le
  PID (ss -ltnp | grep :8001), relancer avec setsid nohup, recharger la page après un changement JS.
```

Notes :
- Environnement thermique : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` ; SDK DJI :
  `scripts/install_dji_sdk.sh <zip officiel DJI>`.
- Données hors dépôt : `~/donnees_externes/` (DTU, Zenodo 16420123, images sans panneau `negatifs_dji/`).
