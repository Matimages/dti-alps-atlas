"""Etapa 3: ROIs esféricas en la grilla del template JHU-ICBM-FA-1mm (182×218×182, 1 mm).

Centros en vóxeles JHU (i, j, k); en mm, x = 90 − i, y = −126 + j, z = −72 + k:
- L-SCR (116,110,99), R-SCR (64,110,99), L-SLF (128,110,99): Liu et al. 2024 (PMC11272201),
  coinciden con alps.sh y con ROIs_JHU_ALPS/*.nii.gz de gbarisano/alps.
- R-SLF (52,110,99): el paper dice 51, pero alps.sh y el archivo ROIs_JHU_ALPS/R_SLF.nii.gz usan 52
  (simétrico con L-SLF respecto de i = 90). Decidido con el autor: manda el archivo del repo.
Radio 2.5 mm (diámetro 5 mm): Liu et al. ("spheres with 5mm diameter") y alps.sh (rois=2.5).
Se incluye todo vóxel cuyo centro está a ≤ 2.5 mm del centro de la esfera: son 81 vóxeles, idéntico
vóxel a vóxel a los archivos del repo (lo verifica tests/test_rois.py).
SCR = fibras de proyección; SLF = fibras de asociación.
"""
import numpy as np

CENTROS = {
    "L_SCR": (116, 110, 99),
    "R_SCR": (64, 110, 99),
    "L_SLF": (128, 110, 99),
    "R_SLF": (52, 110, 99),
}
RADIO_MM = 2.5
FORMA_TEMPLATE = (182, 218, 182)


def esferas(forma=FORMA_TEMPLATE, tam_voxel=(1.0, 1.0, 1.0), centros=CENTROS, radio=RADIO_MM):
    """Devuelve {nombre: máscara booleana} con una esfera por ROI."""
    ii, jj, kk = np.indices(forma)
    sx, sy, sz = tam_voxel
    salida = {}
    for nombre, (ci, cj, ck) in centros.items():
        dist2 = ((ii - ci) * sx) ** 2 + ((jj - cj) * sy) ** 2 + ((kk - ck) * sz) ** 2
        salida[nombre] = dist2 <= radio ** 2
    return salida
