"""Paso 3: reconstrucción DTI con DSI Studio y exportación de los mapas a NIfTI.

- `dsi_studio --action=rec --method=1` (1 = DTI; https://dsi-studio.labsolver.org/doc/cli_t2.html), con el tensor
  como salida adicional. Así lo hacen Marín et al. 2025 y la tesis previa, que piden "tensor" para obtener txx, tyy y tzz.
  Los demás parámetros (máscara, remuestreo, etc.) quedan en los defaults de DSI Studio; se registran en dsi_studio.log.
- `dsi_studio --action=exp --export=fa,md,txx,tyy,tzz` (https://dsi-studio.labsolver.org/doc/cli_exp.html):
  cada mapa queda en <archivo .fz>.<métrica>.nii.gz.
- txx, tyy y tzz son Dxx, Dyy y Dzz, los elementos diagonales del tensor en los ejes de la imagen. Son las mismas filas que
  exportaron los neurorradiólogos desde DSI Studio (`utilidad_directa/Archive 4`) y las que usa el índice ALPS (Taoka 2017).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

from . import dsi_studio

METRICAS = ("fa", "md", "txx", "tyy", "tzz")


def reconstruir_dti(src, carpeta):
    """Reconstruye el DTI desde el .sz y exporta los mapas. Devuelve {métrica: ruta NIfTI}."""
    fz = Path(carpeta) / "dti.fz"
    dsi_studio.correr("rec", carpeta, source=Path(src).resolve(), method=1, other_output="md,tensor",
                      output=fz.name, overwrite=1)
    dsi_studio.correr("exp", carpeta, source=fz.name, export=",".join(METRICAS))
    return {m: Path(carpeta) / f"{fz.name}.{m}.nii.gz" for m in METRICAS}


def figura_qc(mapas, ruta, titulo=""):
    """FA en tres cortes axiales y Dxx, Dyy, Dzz en el corte central, en convención radiológica."""
    img = {m: nib.as_closest_canonical(nib.load(str(p))).get_fdata() for m, p in mapas.items()}  # RAS
    nk = img["fa"].shape[2]
    cortes = [int(nk * f) for f in (0.45, 0.6, 0.75)]
    fig, ejes = plt.subplots(2, 3, figsize=(11, 8))
    paneles = [("fa", k, f"FA, corte {k}") for k in cortes] + \
              [(m, cortes[1], f"{m.replace('t', 'D', 1)} (corte {cortes[1]})") for m in ("txx", "tyy", "tzz")]
    for ax, (m, k, rotulo) in zip(ejes.flat, paneles):
        corte = img[m][::-1, :, k].T  # i invertido: la derecha del paciente queda a la izquierda (radiológica)
        tope = 1 if m == "fa" else np.percentile(img[m][img[m] > 0], 99)
        ax.imshow(corte, origin="lower", cmap="gray", vmin=0, vmax=tope)
        ax.set_title(rotulo, fontsize=10)
        ax.set_axis_off()
        ax.text(0.02, 0.5, "R", color="w", transform=ax.transAxes, va="center")
        ax.text(0.94, 0.5, "L", color="w", transform=ax.transAxes, va="center")
    fig.suptitle(f"{titulo}  Mapas DTI de DSI Studio (convención radiológica)")
    fig.tight_layout()
    fig.savefig(ruta, dpi=100)
    plt.close(fig)
