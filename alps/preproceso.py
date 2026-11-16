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
- Figura QC (qc_eddy.png): muestra el DWI original y la salida de eddy (dwi.sz.corrected.nii.gz) en el mismo volumen y
  corte, junto con su diferencia. DSI Studio borra el NIfTI intermedio que le pasó a eddy; se usa el original, que tiene
  los mismos datos, y ambos se llevan a orientación RAS con nibabel antes de compararlos. Se elige el corte outlier más
  extremo del reporte de eddy (`.eddy_outlier_report`) o, si no hay outliers, el volumen con más movimiento
  (`.eddy_movement_rms`).
"""
import os
import re
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

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


def figura_eddy(carpeta, ruta, original):
    """DWI original y corregido por eddy, y su diferencia, en un mismo volumen y corte. Devuelve la ruta."""
    c = Path(carpeta)
    corregido = nib.load(str(c / "dwi.sz.corrected.nii.gz"))
    antes = nib.as_closest_canonical(nib.load(str(original)))  # RAS
    despues = nib.as_closest_canonical(corregido)
    if antes.shape != despues.shape:
        raise ValueError(f"El DWI original {antes.shape} y el corregido {despues.shape} no tienen la misma grilla.")
    reporte = (c / "dwi.sz.corrected.eddy_outlier_report").read_text()
    outliers = [(abs(float(m[3])), int(m[1]), int(m[2]), float(m[3]))
                for m in re.finditer(r"Slice (\d+) in scan (\d+) .*?mean (\S+) standard", reporte)]
    if outliers:
        _, k, v, de = max(outliers)
        motivo = f"Corte outlier más extremo según eddy ({de:.1f} DE; no se reemplaza)"
    else:
        v = int(np.loadtxt(c / "dwi.sz.corrected.eddy_movement_rms")[:, 0].argmax())
        k = antes.shape[2] // 2
        motivo = "Volumen con más movimiento, corte central"
    k_ras = antes.shape[2] - 1 - k if nib.aff2axcodes(corregido.affine)[2] == "I" else k  # índice de eddy → RAS
    a = np.asarray(antes.dataobj[:, :, k_ras, v], dtype=float)
    d = np.asarray(despues.dataobj[:, :, k_ras, v], dtype=float)
    tope = np.percentile(a[a > 0], 99) if np.any(a > 0) else 1
    paneles = [("Original (antes de eddy)", a, tope), ("Corregido por eddy", d, tope),
               ("|Corregido − Original|", np.abs(d - a), tope / 2)]
    fig, ejes = plt.subplots(1, 3, figsize=(12, 4.6), facecolor="black")
    for ax, (rotulo, imagen, maximo) in zip(ejes, paneles):
        # RAS con i invertido: la derecha del paciente queda a la izquierda (radiológica); anterior arriba
        ax.imshow(imagen[::-1].T, origin="lower", cmap="gray", vmin=0, vmax=maximo)
        ax.set_title(rotulo, color="white", fontsize=11)
        ax.set_axis_off()
        ax.text(0.02, 0.5, "R", color="w", transform=ax.transAxes, va="center")
        ax.text(0.94, 0.5, "L", color="w", transform=ax.transAxes, va="center")
    fig.suptitle(f"Volumen {v}, corte {k} (numeración de eddy, desde 0). Convención radiológica.\n{motivo}",
                 color="white", fontsize=11)
    fig.tight_layout()
    fig.savefig(ruta, dpi=100, facecolor="black")
    plt.close(fig)
    return ruta
