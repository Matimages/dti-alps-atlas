"""Etapa 4: registro afín del FA del sujeto al template JHU-ICBM-FA-1mm.

Fuente: gbarisano/alps hace `flirt -in dti_FA -ref JHU-ICBM-FA-1mm -dof 12 -cost corratio -bins 256
-searchrx/y/z -90 90` y luego aplica esa matriz al tensor con `flirt -applyxfm` (sin -interp, por lo
tanto trilineal y sin reorientar). Liu et al. 2024 lo describen como "automatically rigid and affine transformation".

Equivalente en DIPY: dipy.align.affine_registration con el pipeline centro de masa → traslación →
rígido → afín (12 gdl). SUPUESTO: DIPY solo ofrece información mutua (nbins=32), no correlation ratio, y
parte del centro de masa en vez de la búsqueda angular de ±90°. Los parámetros (level_iters, sigmas,
factors) son los del tutorial de registro afín de DIPY.
Los mapas (Dxx, Dyy, Dzz, color-FA) se llevan al template con la misma matriz e interpolación lineal.
"""
import os
from pathlib import Path

import nibabel as nib
import numpy as np
from dipy.align import affine_registration
from dipy.align.imaffine import AffineMap

TEMPLATE_DEFECTO = Path(__file__).resolve().parents[1] / "templates" / "JHU-ICBM-FA-1mm.nii.gz"
AFFINE_JHU = np.array([[-1, 0, 0, 90], [0, 1, 0, -126], [0, 0, 1, -72], [0, 0, 0, 1]], dtype=float)


def cargar_template(ruta=None):
    """Carga el FA del template (ruta explícita, variable DTI_ALPS_TEMPLATE o templates/) y verifica la grilla."""
    ruta = Path(ruta or os.environ.get("DTI_ALPS_TEMPLATE") or TEMPLATE_DEFECTO)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el template {ruta}. Ver README (JHU-ICBM-FA-1mm.nii.gz de FSL).")
    img = nib.load(str(ruta))
    if img.shape != (182, 218, 182) or not np.allclose(img.affine, AFFINE_JHU):
        raise ValueError(f"{ruta} no tiene la grilla de JHU-ICBM-FA-1mm (182×218×182, 1 mm).")
    return img.get_fdata(dtype="float32"), img.affine


def registrar(fa, affine_fa, template, affine_template):
    """Registra el FA al template. Devuelve un AffineMap que lleva mapas nativos a la grilla del template."""
    _, matriz = affine_registration(
        fa, template, moving_affine=affine_fa, static_affine=affine_template,
        pipeline=["center_of_mass", "translation", "rigid", "affine"],
        nbins=32, level_iters=[10000, 1000, 100], sigmas=[3.0, 1.0, 0.0], factors=[4, 2, 1],
    )
    return AffineMap(matriz, domain_grid_shape=template.shape, domain_grid2world=affine_template,
                     codomain_grid_shape=fa.shape, codomain_grid2world=affine_fa)


def al_template(mapa_afin, imagen):
    """Lleva un mapa 3D (o RGB 3D+3) al template con interpolación lineal."""
    if imagen.ndim == 4:
        return np.stack([mapa_afin.transform(imagen[..., c], interpolation="linear")
                         for c in range(imagen.shape[3])], axis=-1)
    return mapa_afin.transform(imagen, interpolation="linear")
