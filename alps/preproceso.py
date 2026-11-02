"""Etapa 2a: denoising MP-PCA y corrección de Gibbs.

Fuente: el pipeline FSL de Liu et al. 2024 (PMC11272201) aplica "MP-PCA denoising" y "Gibbs-unringing"
con MRtrix3 (dwidenoise, mrdegibbs), en ese orden, antes de ajustar el tensor. gbarisano/alps lo hace
por defecto (denoise=1).
Equivalentes en DIPY:
- mppca con patch_radius=2, es decir, ventana 5×5×5, el default de dwidenoise. Se aplica a toda la
  imagen, sin máscara, igual que dwidenoise por defecto.
- gibbs_removal con slice_axis=2 (cortes axiales) y n_points=3: defaults de DIPY. SUPUESTO: equivalen a mrdegibbs.
No se corrige movimiento ni eddy: queda como limitación documentada (fuera de alcance).
"""
from dipy.denoise.gibbs import gibbs_removal
from dipy.denoise.localpca import mppca


def preprocesar(datos):
    """Devuelve el DWI 4D después de MP-PCA y luego Gibbs."""
    sin_ruido = mppca(datos, patch_radius=2)
    # num_processes=None usa todos los núcleos; el resultado es el mismo, solo cambia el tiempo.
    return gibbs_removal(sin_ruido, slice_axis=2, n_points=3, inplace=False, num_processes=None)
