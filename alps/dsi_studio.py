"""Llamadas a DSI Studio por línea de comandos.

DSI Studio (F.-C. Yeh; doi:10.1038/s41592-025-02762-8) es la herramienta con la que se hizo el preproceso y la
reconstrucción DTI en Marín et al. 2025 y en la tesis previa. Lo pidió la profesora Chabert en la reunión del 2026-11-03.
- Documentación: https://dsi-studio.labsolver.org/doc/cli_t1.html (src), cli_t2.html (rec) y cli_exp.html (exp).
- Repositorio: https://github.com/frankyeh/DSI-Studio. Versión probada: release 2026.7.25 "Sun" (build del
  2026-10-30), Linux universal CPU. Corre nativo en Linux, macOS (Intel y Apple Silicon) y Windows.
- Ejecutable: variable DTI_ALPS_DSI_STUDIO, o `dsi_studio` en el PATH, o la ruta típica de la app en macOS.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

RUTA_MACOS = "/Applications/dsi_studio.app/Contents/MacOS/dsi_studio"
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def ejecutable():
    for candidato in (os.environ.get("DTI_ALPS_DSI_STUDIO"), shutil.which("dsi_studio"), RUTA_MACOS):
        if candidato and Path(candidato).exists():
            return candidato
    raise FileNotFoundError("No se encontró DSI Studio: instálalo (https://dsi-studio.labsolver.org/download.html) "
                            "e indica el ejecutable en la variable DTI_ALPS_DSI_STUDIO.")


def correr(accion, carpeta, **parametros):
    """Ejecuta `dsi_studio --action=<accion> --clave=valor ...` en `carpeta` y devuelve el log sin colores.

    DSI Studio marca los problemas con "❗" o "❌", pero puede terminar con código 0 (por ejemplo, crea el .sz aunque
    no encuentre el bval/bvec). Por eso cualquier línea con esas marcas se trata como error.
    """
    comando = [ejecutable(), f"--action={accion}"] + [f"--{k}={v}" for k, v in parametros.items()]
    entorno = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}  # sin ventana: solo línea de comandos
    r = subprocess.run(comando, cwd=carpeta, env=entorno, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    log = _ANSI.sub("", r.stdout + r.stderr)
    with open(Path(carpeta) / "dsi_studio.log", "a", encoding="utf-8") as f:
        f.write(" ".join(comando) + "\n" + log + "\n")
    problemas = [linea.strip("│├└─ ") for linea in log.splitlines() if "❗" in linea or "❌" in linea]
    if r.returncode != 0 or problemas:
        raise RuntimeError(f"DSI Studio --action={accion} falló: " + ("; ".join(problemas) or log[-500:]))
    return log
