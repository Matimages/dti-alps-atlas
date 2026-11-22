#!/bin/bash
# Abre la app en el navegador. En macOS se puede abrir con doble clic. Requiere haber corrido antes app/instalar.sh.
# Tema claro con azul institucional y sin el menú de desarrollador de Streamlit (opciones de `streamlit run`).
REPO="$(cd "$(dirname "$0")/.." && pwd)"
. "$REPO/herramientas/config.sh"
cd "$REPO" && exec "$REPO/herramientas/python/bin/python" -m streamlit run app/app.py \
  --theme.base light --theme.primaryColor "#1F4E79" --theme.backgroundColor "#FFFFFF" \
  --theme.secondaryBackgroundColor "#F1F4F8" --theme.textColor "#1B2733" \
  --client.toolbarMode minimal --browser.gatherUsageStats false
