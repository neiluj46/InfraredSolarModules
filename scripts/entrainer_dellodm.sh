#!/usr/bin/env bash
# Entraîne le détecteur de modules sur DELLODM (RTX 2080, Docker + runtime nvidia), lancé depuis AEX.
#
#   scripts/entrainer_dellodm.sh [epochs]        lance (ou reprend) l'entraînement en arrière-plan
#   scripts/entrainer_dellodm.sh suivre          affiche le journal
#   scripts/entrainer_dellodm.sh rapatrier       copie models/detector.pt et le rapport sur AEX
#
# Accès SSH par clé uniquement (clé d'AEX chargée dans l'agent : ssh-add). Image officielle PyTorch ;
# le conteneur tourne avec l'utilisateur odm (fichiers modifiables ensuite), dépendances dans /travail/.pip.
# Le jeu Zenodo 16420123 est copié une fois dans ~/infrared/donnees (15 Mo).
set -euo pipefail
HOTE=${DELLODM:-odm@192.168.1.125}
IMAGE=pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime
NOM=infrared-detecteur
ICI=$(cd "$(dirname "$0")/.." && pwd)
JEU="donnees/Thermal PV Panel Detection Dataset for UAV Inspection"
SSH=(ssh -o BatchMode=yes "$HOTE")

case "${1:-}" in
  suivre)    exec "${SSH[@]}" "docker logs -f --tail 20 $NOM" ;;
  rapatrier) rsync -a "$HOTE:infrared/models/detector.pt" "$ICI/models/"
             rsync -a "$HOTE:infrared/output/detector_report.json" "$ICI/output/"
             echo "→ $ICI/models/detector.pt" ; exit 0 ;;
esac
EPOCHS=${1:-60}

"${SSH[@]}" 'mkdir -p ~/infrared/scripts ~/infrared/donnees ~/infrared/models ~/infrared/output'
rsync -a "$ICI/scripts/train_detector.py" "$HOTE:infrared/scripts/"
"${SSH[@]}" "test -d ~/infrared/'$JEU'" || \
  rsync -a "$HOME/donnees_externes/zenodo_pv_detection/extrait/" "$HOTE:infrared/donnees/"
"${SSH[@]}" "docker rm -f $NOM >/dev/null 2>&1 || true
  docker run -d --name $NOM --gpus all --user \$(id -u):\$(id -g) -e HOME=/travail/.pip \
    -v ~/infrared:/travail -w /travail $IMAGE \
    bash -c 'pip install -q --user scipy pillow && python scripts/train_detector.py --donnees \"$JEU\" --epochs $EPOCHS'"
echo "Lancé sur $HOTE ($NOM). Journal : $0 suivre"
