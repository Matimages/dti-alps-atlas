"""Etapa 2a: denoising MP-PCA y corrección de Gibbs.

Fuente: el pipeline FSL de Liu et al. 2024 (PMC11272201) aplica "MP-PCA denoising" y "Gibbs-unringing"
con MRtrix3 (dwidenoise, mrdegibbs), en ese orden, antes de ajustar el tensor. gbarisano/alps lo hace
por defecto (denoise=1).
Equivalentes en DIPY:
- mppca con patch_radius=2, es decir, ventana 5×5×5, el default de dwidenoise. Se aplica a toda la
  imagen, sin máscara, igual que dwidenoise por defecto.
- gibbs_removal con slice_axis=2 (cortes axiales) y n_points=3: defaults de DIPY. SUPUESTO: equivalen a mrdegibbs.
No se corrige movimiento ni eddy: queda como limitación documentada (fuera de alcance).

Paralelización (solo cambia el tiempo, no el resultado): mppca de DIPY recorre los vóxeles en un bucle
de un solo núcleo. Cada vóxel de salida depende solo de los datos a ≤ 2·radio = 4 vóxeles de distancia.
Por eso el volumen se parte en bloques a lo largo de x con 4 vóxeles de margen por lado; cada núcleo
procesa un bloque y se conserva solo su parte central. El resultado es idéntico bit a bit al de una
sola llamada (tests/test_preproceso.py).
"""
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from dipy.denoise.gibbs import gibbs_removal
from dipy.denoise.localpca import mppca

RADIO_PCA = 2
MARGEN = 2 * RADIO_PCA


def _mppca_bloque(bloque):
    return mppca(bloque, patch_radius=RADIO_PCA)


def mppca_paralelo(datos, n_procesos=None):
    """MP-PCA por bloques en x, uno por núcleo; mismo resultado que mppca(datos, patch_radius=2)."""
    nx = datos.shape[0]
    n = max(1, min(n_procesos or os.cpu_count() or 1, nx // (2 * RADIO_PCA + 1)))
    bordes = np.linspace(0, nx, n + 1).astype(int)
    bloques = [(max(a - MARGEN, 0), min(b + MARGEN, nx), a, b) for a, b in zip(bordes[:-1], bordes[1:])]
    # Los procesos hijos heredan el entorno: 1 hilo de BLAS cada uno, para que no compitan por los núcleos.
    previo = os.environ.get("OPENBLAS_NUM_THREADS")
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    try:
        with ProcessPoolExecutor(n) as ex:
            resultados = list(ex.map(_mppca_bloque, [datos[i0:i1] for i0, i1, _, _ in bloques]))
    finally:
        if previo is None:
            del os.environ["OPENBLAS_NUM_THREADS"]
        else:
            os.environ["OPENBLAS_NUM_THREADS"] = previo
    return np.concatenate([r[a - i0:b - i0] for (i0, _, a, b), r in zip(bloques, resultados)], axis=0)


def preprocesar(datos):
    """Devuelve el DWI 4D después de MP-PCA y luego Gibbs."""
    sin_ruido = mppca_paralelo(datos)
    # num_processes=None usa todos los núcleos; el resultado es el mismo, solo cambia el tiempo.
    return gibbs_removal(sin_ruido, slice_axis=2, n_points=3, inplace=False, num_processes=None)
