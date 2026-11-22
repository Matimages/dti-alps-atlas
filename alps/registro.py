"""Pasos 3 a 5: FA del sujeto, registro afín al atlas y DWI llevado al atlas con los bvecs rotados.

Atlas: FSL HCP1065 1 mm (FA promedio de 1065 sujetos del Human Connectome Project, en $FSLDIR/data/standard), en la
misma grilla MNI de 1 mm que JHU-ICBM-FA-1mm (182×218×182, x = 90 − i). Lo eligió la prof. Chabert (reunión del
2026-11-17), por la figura en color-FA con las ROIs de Liu.

Orden (decisión de la prof. Chabert): primero se registra y después se calcula el tensor en el atlas. Así Dxx, Dyy y Dzz
quedan en los ejes del atlas y no en los de la cabeza de cada sujeto. Liu et al. 2024 (alps.sh) calcula el tensor en el
sujeto y lleva los mapas al template sin reorientarlos; esa es la alternativa descartada.

3. FA del sujeto, solo para registrar: tensor por mínimos cuadrados (DIPY TensorModel OLS, como dtifit sin --wls de
   alps.sh) dentro de la máscara de bet2 del paso 2.
4. Registro afín (12 gdl) FA del sujeto → FA del atlas, con dipy.align.affine_registration (centro de masa →
   traslación → rígido → afín). alps.sh usa `flirt -dof 12`. SUPUESTO: información mutua (nbins=32) con los parámetros
   del tutorial de DIPY; DIPY no tiene correlation ratio.
5. Cada volumen del DWI corregido se lleva a la grilla del atlas con esa matriz (interpolación lineal). Los bvecs se
   rotan con la parte rotacional de la matriz, obtenida por descomposición polar (estrategia de "finite strain":
   Alexander et al. 2001, IEEE TMI 20:1131-9). La matriz b debe rotarse cuando se rota la imagen (Leemans & Jones 2009,
   Magn Reson Med 61:1336-49).
   Convención de bvecs de FSL: están en los ejes de vóxel y la componente x va invertida si el determinante del affine es
   positivo (documentación de MRtrix3, "Diffusion gradient scheme handling").
"""
import os
from pathlib import Path

import nibabel as nib
import numpy as np
from dipy.align import affine_registration
from dipy.align.imaffine import AffineMap
from dipy.core.gradients import gradient_table
from dipy.reconst.dti import TensorModel

ATLAS_RELATIVO = "data/standard/FSL_HCP1065_FA_1mm.nii.gz"
AFFINE_MNI = np.array([[-1, 0, 0, 90], [0, 1, 0, -126], [0, 0, 1, -72], [0, 0, 0, 1]], dtype=float)
FORMA_MNI = (182, 218, 182)


def cargar_template(ruta=None):
    """FA del atlas (ruta explícita, variable DTI_ALPS_TEMPLATE o el HCP1065 de FSL). Verifica la grilla MNI 1 mm."""
    ruta = Path(ruta or os.environ.get("DTI_ALPS_TEMPLATE") or Path(os.environ.get("FSLDIR", "")) / ATLAS_RELATIVO)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el atlas {ruta}: hace falta FSL (data/standard) y la variable FSLDIR.")
    img = nib.load(str(ruta))
    if img.shape != FORMA_MNI or not np.allclose(img.affine, AFFINE_MNI):
        raise ValueError(f"{ruta} no tiene la grilla MNI de 1 mm (182×218×182).")
    return img.get_fdata(dtype="float32"), img.affine


def fa_nativo(nifti, bval, bvec, mascara):
    """FA del sujeto (DIPY, OLS) dentro de la máscara; solo se usa para el registro."""
    img = nib.load(str(nifti))
    gtab = gradient_table(np.loadtxt(bval, ndmin=1), bvecs=np.loadtxt(bvec, ndmin=2).T)
    ajuste = TensorModel(gtab, fit_method="OLS").fit(img.get_fdata(dtype="float32"),
                                                     mask=nib.load(str(mascara)).get_fdata() > 0)
    return np.clip(np.nan_to_num(ajuste.fa), 0, 1), img.affine


def registrar(fa, affine_fa, template, affine_template):
    """Registra el FA al template. Devuelve un AffineMap que lleva imágenes del sujeto a la grilla del template."""
    _, matriz = affine_registration(
        fa, template, moving_affine=affine_fa, static_affine=affine_template,
        pipeline=["center_of_mass", "translation", "rigid", "affine"],
        nbins=32, level_iters=[10000, 1000, 100], sigmas=[3.0, 1.0, 0.0], factors=[4, 2, 1],
    )
    return AffineMap(matriz, domain_grid_shape=template.shape, domain_grid2world=affine_template,
                     codomain_grid_shape=fa.shape, codomain_grid2world=affine_fa)


def _rotacion(matriz):
    """Parte rotacional (ortogonal) de una matriz 3×3 por descomposición polar."""
    u, _, vt = np.linalg.svd(matriz[:3, :3])
    return u @ vt


def bvecs_al_atlas(bvecs, affine_sujeto, matriz_registro, affine_atlas):
    """Rota bvecs de FSL (3×N) del sujeto al atlas.

    FSL → mundo del sujeto → (rotación inversa del registro) → mundo del atlas → FSL del atlas.
    La matriz del registro (DIPY) lleva puntos del atlas al sujeto, así que una dirección del sujeto pasa al atlas con la
    transpuesta de su rotación.
    """
    g = np.array(bvecs, dtype=float)
    if np.linalg.det(affine_sujeto[:3, :3]) > 0:
        g[0] = -g[0]
    g = _rotacion(matriz_registro).T @ (_rotacion(affine_sujeto) @ g)
    g = _rotacion(affine_atlas).T @ g
    if np.linalg.det(affine_atlas[:3, :3]) > 0:
        g[0] = -g[0]
    return g


def dwi_al_atlas(nifti, bvec, mapa_afin, salida_nifti, salida_bvec):
    """Lleva cada volumen del DWI a la grilla del atlas y escribe los bvecs rotados. Devuelve las dos rutas."""
    img = nib.load(str(nifti))
    volumenes = [mapa_afin.transform(np.asarray(img.dataobj[..., v], dtype=np.float32), interpolation="linear")
                 for v in range(img.shape[3])]
    nib.save(nib.Nifti1Image(np.stack(volumenes, -1).astype(np.float32), mapa_afin.domain_grid2world),
             str(salida_nifti))
    rotados = bvecs_al_atlas(np.loadtxt(bvec, ndmin=2), img.affine, mapa_afin.affine, mapa_afin.domain_grid2world)
    np.savetxt(salida_bvec, rotados, fmt="%.6f")
    return Path(salida_nifti), Path(salida_bvec)
