#!/usr/bin/env bash
# Installe le DJI Thermal SDK v1.7 (20241205, Linux x64) dans dji_sdk/ et compile dji_irp.
#
# Les bibliothèques viennent du miroir GitHub SanNianYiSi/thermal_parser (commit figé,
# empreintes SHA-256 vérifiées) : le site de DJI (dji.com, djicdn.com) n'est pas toujours
# joignable. Les bibliothèques restent la propriété de DJI (licence du TSDK) : elles ne
# sont pas versionnées dans ce dépôt (voir .gitignore).
#
# Résultat :
#   dji_sdk/lib/       libdirp.so et ses greffons (libv_*.so, libMicro*.so, libexif.so.12)
#   dji_sdk/bin/dji_irp
#   dji_sdk/samples/   R-JPEG d'exemple (M2EA, M3T, M30T, M4T, H20T...)
set -euo pipefail

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
SDK="$RACINE/dji_sdk"
DEPOT="https://github.com/SanNianYiSi/thermal_parser.git"
COMMIT="b513647ef2318ba99dd2e2a543fa0fb071fd9579"
VERSION="dji_thermal_sdk_v1.7_20241205"
MODELES="M2EA M3T M3TD M30T M4T H20T H30T"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
    echo "Seul Linux x86_64 est pris en charge par ce script." >&2
    exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Téléchargement de $VERSION (thermal_parser@${COMMIT:0:7})..."
git -c advice.detachedHead=false clone -q --filter=blob:none --no-checkout "$DEPOT" "$TMP/tp"
git -C "$TMP/tp" sparse-checkout set --no-cone \
    "/plugins/$VERSION/linux/release_x64/" \
    $(for m in $MODELES; do echo "/images/$m/"; done)
git -C "$TMP/tp" checkout -q "$COMMIT"

SRC="$TMP/tp/plugins/$VERSION/linux/release_x64"
(cd "$SRC" && sha256sum -c --quiet - <<'EOF'
aec6c8697909216aa8f7a30cc2534af89a2792d1017cb4db28d4db8ab4281d89  libMicroIA_Release_x64.so
928df2e97d6b19ea63638aa2a88fbd1de6b1d2413959cab216b1154ae977948d  libMicroJPEG_Release_x64.so
91ad6a25132aa6dab191689b56c8d1ae9f0c8d0f23e072ae5d6a085dd41f2015  libMicroTA_Release_x64.so
dfa37d7a7fbe5b0ee487216f5d0d117279c7491ffd34e306ba145b7536ab44dc  libdirp.so
ad48ee4e2d5ed7b8ced4e94defd41e2937d9bb341d23ec5679208f20d02c41ef  libexif.so.12
41dcd211aae5b2160db0578093bbb302171b4837694b425c2198c7b845cebe1b  libv_dirp.so
6b99cad0ad4abeba02389ac99baf5ddc119cbdf606a87f6926bbad45a856547c  libv_girp.so
468724e53331f2a71c33cd503393b56c45f8c0e798b09e886e565ffc318b9b68  libv_hirp.so
cc5b430271e7b18f2b416c6ccdb34b84e713181954cb6ad9351fce85ee4adddc  libv_iirp.so
7f87352274fcee0063c3cd577cf852b63cc643954d2910f6754cc1c57dff83b7  libv_list.ini
EOF
)
echo "Empreintes SHA-256 vérifiées."

rm -rf "$SDK/lib" "$SDK/bin" "$SDK/samples"
mkdir -p "$SDK/lib" "$SDK/bin" "$SDK/samples"
cp "$SRC"/* "$SDK/lib/"
for m in $MODELES; do
    [[ -d "$TMP/tp/images/$m" ]] && cp -r "$TMP/tp/images/$m" "$SDK/samples/"
done
echo "$VERSION (linux/release_x64) depuis $DEPOT@$COMMIT" > "$SDK/lib/VERSION.txt"

echo "Compilation de dji_irp..."
gcc -O2 -Wall -o "$SDK/bin/dji_irp.bin" "$SDK/src/dji_irp.c" \
    -I"$SDK/src" -L"$SDK/lib" -ldirp -Wl,-rpath,'$ORIGIN/../lib'

# libdirp charge ses greffons (libv_*.so) par dlopen : LD_LIBRARY_PATH doit pointer sur lib/.
cat > "$SDK/bin/dji_irp" <<'EOF'
#!/usr/bin/env bash
ICI="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
export LD_LIBRARY_PATH="$ICI/../lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$ICI/dji_irp.bin" "$@"
EOF
chmod +x "$SDK/bin/dji_irp"

echo "Installé : $SDK/bin/dji_irp"
"$SDK/bin/dji_irp" -s "$SDK/samples/M3T/DJI_0001_R.JPG" -a info
