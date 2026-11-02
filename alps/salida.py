"""Etapa 5b: salidas (CSV, NIfTI y figura QC).

- CSV: mismas columnas que alps.stat/alps.csv de gbarisano/alps, sin `scanner` (no está disponible
  cuando la entrada es NIfTI). Difusividades en mm²/s.
- NIfTI, en el espacio del template: ROIs en un solo archivo con etiquetas 1-4 (orden de alps.sh: L-SCR, R-SCR,
  L-SLF, R-SLF) y FA registrado, para revisar el registro en un visor.
- Figura QC: corte axial k = 99 (altura de las ROIs) del color-FA llevado al template, con los contornos
  de las ROIs. Convención radiológica: la derecha del paciente queda a la izquierda de la imagen. En la grilla
  JHU, i = 0 es x = +90 mm (derecha), así que basta con dibujar i creciendo hacia la derecha.
"""
import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

COLUMNAS = ["id", "x_proj_L", "x_assoc_L", "y_proj_L", "z_assoc_L",
            "x_proj_R", "x_assoc_R", "y_proj_R", "z_assoc_R", "alps_L", "alps_R", "alps"]
ETIQUETAS = {"L_SCR": 1, "R_SCR": 2, "L_SLF": 3, "R_SLF": 4}
COLORES = {"L_SCR": "white", "R_SCR": "white", "L_SLF": "yellow", "R_SLF": "yellow"}


def guardar_csv(fila, ruta):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerow({c: fila[c] for c in COLUMNAS})


def guardar_nifti(rois, fa_template, affine, ruta_rois, ruta_fa):
    etiquetas = np.zeros(fa_template.shape, dtype=np.uint8)
    for nombre, valor in ETIQUETAS.items():
        etiquetas[rois[nombre]] = valor
    nib.save(nib.Nifti1Image(etiquetas, affine), str(ruta_rois))
    nib.save(nib.Nifti1Image(fa_template.astype(np.float32), affine), str(ruta_fa))


def figura_qc(color_fa_template, rois, resultado, ruta, titulo="", k=99):
    """Corte axial del color-FA con las ROIs: vista completa + ampliación de la zona de las ROIs."""
    rgb = np.clip(color_fa_template[:, :, k, :], 0, 1).transpose(1, 0, 2)  # filas = j (A-P), columnas = i
    fig, ejes = plt.subplots(1, 2, figsize=(12, 6.5))
    for ax, (i0, i1, j0, j1) in zip(ejes, [(0, 182, 0, 218), (35, 145, 75, 145)]):
        ax.imshow(rgb, origin="lower", interpolation="nearest")
        for nombre, m in rois.items():
            ax.contour(m[:, :, k].T, levels=[0.5], colors=COLORES[nombre], linewidths=1.2)
        ax.set_xlim(i0, i1)
        ax.set_ylim(j0, j1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.02, 0.5, "R", color="w", fontsize=16, transform=ax.transAxes, va="center")
        ax.text(0.95, 0.5, "L", color="w", fontsize=16, transform=ax.transAxes, va="center")
    for nombre, m in rois.items():
        ci, cj, _ = np.argwhere(m).mean(axis=0)
        ejes[1].text(ci, cj + 4, nombre.replace("_", "-"), color=COLORES[nombre], ha="center", fontsize=9)
    fig.suptitle(f"{titulo}  ALPS L = {resultado['alps_L']:.3f}   R = {resultado['alps_R']:.3f}   "
                 f"media = {resultado['alps']:.3f}\nColor-FA en JHU-ICBM-FA 1 mm, corte axial z = {k - 72} mm "
                 f"(convención radiológica). Blanco: proyección (SCR). Amarillo: asociación (SLF).")
    fig.tight_layout()
    fig.savefig(ruta, dpi=110)
    plt.close(fig)
