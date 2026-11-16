"""Paso 3: reconstrucción DTI con DSI Studio y exportación de los mapas a NIfTI.

- `dsi_studio --action=rec --method=1` (1 = DTI; https://dsi-studio.labsolver.org/doc/cli_t2.html), con el tensor
  como salida adicional. Así lo hacen Marín et al. 2025 y la tesis previa, que piden "tensor" para obtener txx, tyy y tzz.
  Los demás parámetros (máscara, remuestreo, etc.) quedan en los defaults de DSI Studio; se registran en dsi_studio.log.
- `dsi_studio --action=exp --export=fa,md,txx,tyy,tzz` (https://dsi-studio.labsolver.org/doc/cli_exp.html):
  cada mapa queda en <archivo .fz>.<métrica>.nii.gz.
- txx, tyy y tzz son Dxx, Dyy y Dzz, los elementos diagonales del tensor en los ejes de la imagen. Son las mismas filas que
  exportaron los neurorradiólogos desde DSI Studio (`utilidad_directa/Archive 4`) y las que usa el índice ALPS (Taoka 2017).
- Para la figura QC se exportan también txy, txz y tyz. Con el tensor completo se calcula el color-FA = |V1|·FA, donde V1 es
  el autovector del mayor autovalor (Pajevic & Pierpaoli 1999, Magn Reson Med 42:526-40). Rojo = izquierda-derecha,
  verde = antero-posterior, azul = cráneo-caudal. Es la codificación con la que los neurorradiólogos ubican las fibras
  de proyección (azul) y de asociación (verde) (Marín et al. 2025). Solo se usa para mirar; no entra en ningún cálculo.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

from . import dsi_studio

METRICAS = ("fa", "md", "txx", "tyy", "tzz")
FUERA_DIAGONAL = ("txy", "txz", "tyz")  # solo para el color-FA de la figura QC


def reconstruir_dti(src, carpeta):
    """Reconstruye el DTI desde el .sz y exporta los mapas. Devuelve {métrica: ruta NIfTI} (las de METRICAS)."""
    fz = Path(carpeta) / "dti.fz"
    dsi_studio.correr("rec", carpeta, source=Path(src).resolve(), method=1, other_output="md,tensor",
                      output=fz.name, overwrite=1)
    dsi_studio.correr("exp", carpeta, source=fz.name, export=",".join(METRICAS + FUERA_DIAGONAL))
    return {m: Path(carpeta) / f"{fz.name}.{m}.nii.gz" for m in METRICAS}


def color_fa(t):
    """|V1|·FA a partir de {fa, txx, txy, txz, tyy, tyz, tzz} (arreglos 3D). Devuelve RGB en [0, 1]."""
    filas = [("txx", "txy", "txz"), ("txy", "tyy", "tyz"), ("txz", "tyz", "tzz")]
    tensor = np.stack([np.stack([t[c] for c in fila], -1) for fila in filas], -2)
    rgb = np.zeros(t["fa"].shape + (3,))
    dentro = t["fa"] > 0
    _, vectores = np.linalg.eigh(tensor[dentro])  # autovalores en orden ascendente: la última columna es V1
    rgb[dentro] = np.abs(vectores[:, :, -1]) * t["fa"][dentro, None]
    return np.clip(rgb, 0, 1)


def figura_qc(carpeta, ruta, titulo=""):
    """Color-FA en tres cortes axiales y Dxx, Dyy, Dzz en el corte central, en convención radiológica."""
    img = {m: nib.as_closest_canonical(nib.load(str(Path(carpeta) / f"dti.fz.{m}.nii.gz"))).get_fdata()
           for m in METRICAS + FUERA_DIAGONAL}  # RAS
    rgb = color_fa(img)
    nk = img["fa"].shape[2]
    cortes = [int(nk * f) for f in (0.45, 0.6, 0.75)]
    fig, ejes = plt.subplots(2, 3, figsize=(11, 8), facecolor="black")
    paneles = [(rgb, k, f"Color-FA, corte {k}") for k in cortes] + \
              [(img[m], cortes[1], f"{m.replace('t', 'D', 1)} (corte {cortes[1]})") for m in ("txx", "tyy", "tzz")]
    for ax, (vol, k, rotulo) in zip(ejes.flat, paneles):
        corte = np.swapaxes(vol[::-1, :, k], 0, 1)  # i invertido: la derecha del paciente queda a la izquierda
        tope = 1 if vol.ndim == 4 else np.percentile(vol[vol > 0], 99)
        ax.imshow(np.clip(corte / tope, 0, 1), origin="lower", cmap="gray", vmin=0, vmax=1)
        ax.set_title(rotulo, fontsize=10, color="white")
        ax.set_axis_off()
        ax.text(0.02, 0.5, "R", color="w", transform=ax.transAxes, va="center")
        ax.text(0.94, 0.5, "L", color="w", transform=ax.transAxes, va="center")
    fig.suptitle(f"{titulo}  Mapas DTI de DSI Studio (convención radiológica)\nColor-FA: rojo = izquierda-derecha, "
                 "verde = antero-posterior, azul = cráneo-caudal", color="white")
    fig.tight_layout()
    fig.savefig(ruta, dpi=100, facecolor="black")
    plt.close(fig)
    return ruta
