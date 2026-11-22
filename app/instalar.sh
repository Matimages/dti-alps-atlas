#!/bin/bash
# Instala lo mínimo para correr la app (macOS Apple Silicon o Intel, o Linux) dentro de <repo>/herramientas/.
# No usa sudo ni toca nada fuera de esa carpeta. Uso: bash app/instalar.sh   (una sola vez)
#
# Qué instala y de dónde:
# - micromamba (gestor de entornos conda en un solo archivo): https://mamba.readthedocs.io/
# - Un entorno con Python 3.12 y las librerías de requirements.txt (pip), más solo las partes de FSL que se usan,
#   desde el canal conda oficial de FSL (https://fsl.fmrib.ox.ac.uk/fsl/docs/install/conda.html):
#   fsl-eddy (eddy_cpu), fsl-bet2 (máscara), fsl-data_standard (atlas HCP1065) y fsl-data_atlases (JHU, comparación).
#   Licencia FSL: uso académico no comercial.
# - DSI Studio, release 2026.7.25 (https://github.com/frankyeh/DSI-Studio/releases). Licencia propia, uso académico.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
H="$REPO/herramientas"
DSI_VERSION="2026.7.25"
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  PLAT=osx-arm64; DSI_ZIP=dsi_studio_macos-14-arm64_qt6.zip ;;
  Darwin-x86_64) PLAT=osx-64;    DSI_ZIP=dsi_studio_macos-15-intel_qt6.zip ;;
  Linux-x86_64)  PLAT=linux-64;  DSI_ZIP=dsi_studio_linux_universal_cpu.zip ;;
  *) echo "Sistema no soportado: $(uname -s) $(uname -m)"; exit 1 ;;
esac
mkdir -p "$H"
echo "== 1/4 micromamba ($PLAT)"
if [ ! -x "$H/bin/micromamba" ]; then
  curl -Ls "https://micro.mamba.pm/api/micromamba/$PLAT/latest" | tar -xj -C "$H" bin/micromamba
fi
export MAMBA_ROOT_PREFIX="$H/mamba"

echo "== 2/4 Entorno con Python y FSL (eddy, bet2, atlas)"
if [ ! -x "$H/entorno/bin/python" ]; then
  "$H/bin/micromamba" create -y -p "$H/entorno" \
    -c https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public/ -c conda-forge \
    python=3.12 fsl-eddy fsl-bet2 fsl-data_standard fsl-data_atlases
  "$H/bin/micromamba" clean -a -y >/dev/null  # borra la caché de descargas
fi

echo "== 3/4 Librerías de Python"
"$H/entorno/bin/python" -m pip install -q --no-cache-dir -r "$REPO/requirements.txt"

echo "== 4/4 DSI Studio $DSI_VERSION"
if [ ! -d "$H/dsi_studio" ]; then
  curl -L -o "$H/$DSI_ZIP" "https://github.com/frankyeh/DSI-Studio/releases/download/$DSI_VERSION/$DSI_ZIP"
  mkdir -p "$H/dsi_studio"
  if command -v unzip >/dev/null; then  # macOS trae unzip (respeta los enlaces dentro del .app)
    (cd "$H/dsi_studio" && unzip -q "$H/$DSI_ZIP")
  else
    "$H/entorno/bin/python" -m zipfile -e "$H/$DSI_ZIP" "$H/dsi_studio"
  fi
  rm "$H/$DSI_ZIP"
  [ "$(uname -s)" = Darwin ] && xattr -dr com.apple.quarantine "$H/dsi_studio" || true
fi
DSI="$(find "$H/dsi_studio" -type f -path '*Contents/MacOS/dsi_studio' | head -1)"
[ -n "$DSI" ] || DSI="$(find "$H/dsi_studio" -type f -name dsi_studio | head -1)"
chmod +x "$DSI"
[ -f "$(dirname "$DSI")/AppRun" ] && chmod +x "$(dirname "$DSI")/AppRun"

cat > "$H/config.sh" <<EOF
export FSLDIR="$H/entorno"
export FSLOUTPUTTYPE=NIFTI_GZ
export DTI_ALPS_DSI_STUDIO="$DSI"
export PATH="$H/entorno/bin:\$PATH"
EOF

echo "== Verificación"
. "$H/config.sh"
ls "$FSLDIR/bin/eddy_cpu" "$FSLDIR/bin/bet2" "$FSLDIR/data/standard/FSL_HCP1065_FA_1mm.nii.gz"
QT_QPA_PLATFORM=offscreen "$DSI" --version | head -1
(cd "$REPO" && "$H/entorno/bin/python" -m pytest -q tests | tail -1)
echo "Listo. Para abrir la app: doble clic en app/abrir_app.command (macOS) o bash app/abrir_app.command"
