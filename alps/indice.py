"""Etapa 5a: medias de difusividad en las ROIs e índice ALPS.

Fuentes:
- Media en la ROI = promedio de todos los vóxeles de la máscara, como `fslstats <mapa> -k <roi> -m` en alps.sh.
- Índice (Taoka et al. 2017; alps.sh; Liu et al. 2024):
    ALPS_h = mean(Dxx_proy, Dxx_asoc) / mean(Dyy_proy, Dzz_asoc)   para h = L, R
    ALPS   = mean(ALPS_L, ALPS_R)
  Proyección = SCR, asociación = SLF. Los nombres de las claves siguen el CSV de alps.sh.
"""
import numpy as np


def medias_en_rois(dxx, dyy, dzz, rois):
    """Medias en las ROIs, con los nombres de alps.sh (x_proj_L, x_assoc_L, y_proj_L, z_assoc_L, ...)."""
    v = {}
    for h in ("L", "R"):
        proy, asoc = rois[f"{h}_SCR"], rois[f"{h}_SLF"]
        v[f"x_proj_{h}"] = float(np.mean(dxx[proy]))
        v[f"x_assoc_{h}"] = float(np.mean(dxx[asoc]))
        v[f"y_proj_{h}"] = float(np.mean(dyy[proy]))
        v[f"z_assoc_{h}"] = float(np.mean(dzz[asoc]))
    return v


def indice_alps(v):
    """Devuelve {alps_L, alps_R, alps} a partir de las medias de medias_en_rois."""
    r = {}
    for h in ("L", "R"):
        r[f"alps_{h}"] = ((v[f"x_proj_{h}"] + v[f"x_assoc_{h}"]) / 2) / ((v[f"y_proj_{h}"] + v[f"z_assoc_{h}"]) / 2)
    r["alps"] = (r["alps_L"] + r["alps_R"]) / 2
    return r
