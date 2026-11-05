"""Paso 2: corrección de corrientes de Foucault (eddy) y de movimiento con FSL eddy, llamado desde DSI Studio.

Reemplaza al denoising MP-PCA y a la corrección de Gibbs. Lo pidió la prof. Chabert en la reunión del 2026-11-03:
a 1.5T la relación señal-ruido es más baja que a 3T, donde se validó Liu et al. 2024, y el denoising podría
eliminar información. Marín et al. 2025 hicieron esta misma corrección con DSI Studio + EDDY.

- `dsi_studio --action=rec --cmd=eddy+save_src=<salida>` (https://dsi-studio.labsolver.org/doc/cli_t2.html):
  DSI Studio escribe el DWI y los gradientes en el formato de FSL, corre `eddy` y recarga el DWI corregido junto con
  los bvecs rotados (`.eddy_rotated_bvecs`), y guarda un nuevo .sz. Fuente: libs/dsi/image_model.cpp de
  github.com/frankyeh/DSI-Studio (funciones run_eddy y load_topup_eddy_result).
- FSL eddy (Andersson & Sotiropoulos 2016; https://fsl.fmrib.ox.ac.uk/fsl/docs/diffusion/eddy/users_guide/index.html),
  FSL 6.0.7.23. Requiere FSL instalado y la variable FSLDIR (Linux o macOS; en Windows, solo vía WSL).
- Sin imagen con codificación de fase inversa no hay TOPUP. DSI Studio pasa a eddy `--acqp` = "0 -1 0 0.05"
  (fase antero-posterior, readout 0.05 s) y la máscara de su U-Net. SUPUESTO: la fase es AP. ds001378 no trae el JSON
  que lo diría. Según el FAQ de eddy, un readout de 0.05 s sirve si no se conoce.
- Argumentos fijos de DSI Studio: --data_is_shelled --verbose. Por lo tanto quedan los defaults de eddy:
  --slm=none, --repol=False (no reemplaza cortes outlier), sin slice-to-volume (--mporder=0) y --nthr=1 (un solo hilo;
  ~45 min por sujeto). La guía de eddy recomienda considerar `--slm=linear` cuando hay pocas direcciones (aquí 15).
  Verificado en <sujeto>/dwi.sz.corrected.eddy_values_of_all_input_parameters.
"""
import os
import shutil
from pathlib import Path

from . import dsi_studio


def corregir(src, carpeta):
    """Corre eddy sobre el .sz y devuelve la ruta del .sz corregido (dwi_eddy.sz)."""
    if not (os.environ.get("FSLDIR") or shutil.which("eddy")):
        raise FileNotFoundError("No se encontró FSL (eddy): instálalo (https://fsl.fmrib.ox.ac.uk/fsl/docs/install/) "
                                "y deja definida la variable FSLDIR.")
    salida = Path(carpeta) / "dwi_eddy.sz"
    # --action=rec siempre termina reconstruyendo: se pide DTI (lo más rápido) y ese .fz se descarta,
    # porque el tensor se calcula en el paso 3 a partir de dwi_eddy.sz.
    descarte = Path(carpeta) / "descartar.fz"
    dsi_studio.correr("rec", carpeta, source=Path(src).resolve(), cmd=f"eddy+save_src={salida.name}",
                      method=1, output=descarte.name, overwrite=1)
    descarte.unlink(missing_ok=True)
    if not salida.exists():
        raise RuntimeError("DSI Studio terminó sin escribir el DWI corregido; revisa dsi_studio.log.")
    return salida
