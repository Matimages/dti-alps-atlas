#!/bin/bash
# Abre la app en el navegador. En macOS se puede abrir con doble clic. Requiere haber corrido antes app/instalar.sh.
REPO="$(cd "$(dirname "$0")/.." && pwd)"
. "$REPO/herramientas/config.sh"
cd "$REPO" && exec "$REPO/herramientas/entorno/bin/python" -m streamlit run app/app.py
