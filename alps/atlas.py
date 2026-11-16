"""Paso 4 (en discusión): atlas candidatos para que los neurorradiólogos dibujen las ROIs.

Acordado en la reunión con la prof. Chabert (2026-11-03): los neurorradiólogos confirmarán el atlas y dibujarán las ROIs
sobre él. Esta figura sirve para proponerles uno. Muestra el corte axial de las ROIs de Liu (z = +27 mm, k = 99) en:
- JHU-ICBM-FA 1 mm (FSL, data/atlases/JHU): el template de Liu et al. 2024. Es solo FA, en escala de grises.
- FSL HCP1065 1 mm (FSL, data/standard/FSL_HCP1065_FA_1mm y _V1_1mm): FA y dirección principal de difusión (V1) promedio
  de 1065 sujetos del Human Connectome Project. Permite el color-FA |V1|·FA (rojo = izquierda-derecha,
  verde = antero-posterior, azul = cráneo-caudal; Pajevic & Pierpaoli 1999, Magn Reson Med 42:526-40). Es la
  codificación con la que los neurorradiólogos ubicaron las ROIs en Marín et al. 2025 (azul = proyección,
  verde = asociación).
Los dos están en la misma grilla MNI de 1 mm (182×218×182, x = 90 − i), verificado con FSL 6.0.7.23. Las esferas son las
ROIs de Liu (alps/rois.py) y sirven solo como referencia de ubicación.
"""
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

from . import rois

K_ROIS = 99


def _fsl(relativa):
    ruta = Path(os.environ.get("FSLDIR", "")) / relativa
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {relativa}: hace falta FSL instalado y la variable FSLDIR.")
    return nib.load(str(ruta))


def figura_candidatos(ruta):
    jhu = _fsl("data/atlases/JHU/JHU-ICBM-FA-1mm.nii.gz")
    fa = _fsl("data/standard/FSL_HCP1065_FA_1mm.nii.gz")
    v1 = _fsl("data/standard/FSL_HCP1065_V1_1mm.nii.gz")
    if not (np.allclose(jhu.affine, fa.affine) and np.allclose(fa.affine, v1.affine)):
        raise ValueError("Los templates no comparten la grilla MNI de 1 mm.")
    k = K_ROIS
    color = np.clip(np.abs(v1.dataobj[:, :, k, :]) * np.asarray(fa.dataobj[:, :, k])[..., None], 0, 1)
    paneles = [("JHU-ICBM-FA 1 mm (template de Liu): solo FA", np.asarray(jhu.dataobj[:, :, k]), "gray"),
               ("FSL HCP1065 1 mm: color-FA (dirección de las fibras)", color, None)]
    esferas = rois.esferas(jhu.shape)
    fig, ejes = plt.subplots(1, 2, figsize=(12, 6.5))
    for ax, (titulo, imagen, cmap) in zip(ejes, paneles):
        imagen = imagen.transpose(1, 0, 2) if imagen.ndim == 3 else imagen.T  # filas = j (A-P), columnas = i
        imagen = np.clip(imagen / np.percentile(imagen, 99.5), 0, 1)  # solo brillo, para verlo en pantalla
        ax.imshow(imagen, origin="lower", cmap=cmap, vmin=0, vmax=1, interpolation="nearest")
        for nombre, m in esferas.items():
            ax.contour(m[:, :, k].T, levels=[0.5], colors="white" if "SCR" in nombre else "yellow", linewidths=1.2)
            ci, cj, _ = np.argwhere(m).mean(axis=0)
            ax.text(ci, cj + 5, nombre.replace("_", "-"), color="white", ha="center", fontsize=8)
        ax.set_xlim(35, 147)
        ax.set_ylim(60, 160)
        ax.set_title(titulo, fontsize=11, color="white")
        ax.set_axis_off()
        ax.text(0.02, 0.5, "R", color="w", fontsize=14, transform=ax.transAxes, va="center")
        ax.text(0.95, 0.5, "L", color="w", fontsize=14, transform=ax.transAxes, va="center")
    fig.suptitle(f"Atlas candidatos: corte axial z = +{k - 72} mm (cuerpo de los ventrículos laterales), convención "
                 "radiológica.\nContornos: ROIs de Liu et al. 2024 (blanco = proyección, SCR; amarillo = asociación, SLF).",
                 color="white")
    fig.tight_layout()
    fig.savefig(ruta, dpi=110, facecolor="black")
    plt.close(fig)
    return ruta
