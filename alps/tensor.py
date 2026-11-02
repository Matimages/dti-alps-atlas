"""Etapa 2b: máscara cerebral y ajuste del tensor.

- Máscara: median_otsu sobre los volúmenes b0, con los defaults de DIPY (median_radius=4, numpass=4).
  Lo indicó el autor del proyecto; Liu usa bet sobre el b0. SUPUESTO: los defaults sirven para estos datos.
- Ajuste: mínimos cuadrados lineales (fit_method="OLS"), equivalente a `dtifit` sin `--wls`
  de gbarisano/alps (decidido con el autor el 2026-11-02).
- Dxx, Dyy y Dzz son los elementos diagonales del tensor en los ejes de la imagen, como
  `fslroi dti_tensor 0/3/5` en alps.sh. No se reorienta el tensor.
  Unidades: mm²/s, porque los valores b vienen en s/mm².
"""
import numpy as np
from dipy.reconst.dti import TensorModel, color_fa
from dipy.segment.mask import median_otsu


def ajustar_tensor(datos, gtab):
    """Devuelve un dict con mascara, FA, MD, Dxx, Dyy, Dzz y color-FA (RGB), en el espacio nativo."""
    b0s = np.where(gtab.b0s_mask)[0]
    _, mascara = median_otsu(datos, vol_idx=b0s, median_radius=4, numpass=4)
    ajuste = TensorModel(gtab, fit_method="OLS").fit(datos, mask=mascara)
    tensor = ajuste.quadratic_form  # (..., 3, 3)
    fa = np.clip(np.nan_to_num(ajuste.fa), 0, 1)
    return {
        "mascara": mascara,
        "FA": fa,
        "MD": ajuste.md,
        "Dxx": tensor[..., 0, 0],
        "Dyy": tensor[..., 1, 1],
        "Dzz": tensor[..., 2, 2],
        "color_FA": color_fa(fa, ajuste.evecs),
    }
