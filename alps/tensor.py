"""Paso 6: tensor DTI con DSI Studio sobre el DWI ya llevado al atlas, y exportación de los mapas a NIfTI.

- `dsi_studio --action=src` con el DWI en el atlas y los bvecs rotados (paso 5), y luego `--action=rec --method=1`
  (1 = DTI; https://dsi-studio.labsolver.org/doc/cli_t2.html), con el tensor como salida adicional. Así lo hacen
  Marín et al. 2025 y la tesis previa, que piden "tensor" para obtener txx, tyy y tzz. `--make_isotropic=0` para que
  DSI Studio no remuestree: los mapas tienen que quedar en la grilla de 1 mm del atlas, donde están las ROIs. El resto
  queda en los defaults de DSI Studio; se registra en dsi_studio.log.
- Los mapas exportados se reordenan a la orientación del atlas con nibabel (DSI Studio puede exportar en LPS) y se
  verifica que la grilla resultante sea la del atlas.
- `dsi_studio --action=exp --export=fa,md,txx,tyy,tzz` (https://dsi-studio.labsolver.org/doc/cli_exp.html):
  cada mapa queda en <archivo .fz>.<métrica>.nii.gz.
- txx, tyy y tzz son Dxx, Dyy y Dzz, los elementos diagonales del tensor en los ejes de la imagen. Son las mismas filas que
  exportaron los neurorradiólogos desde DSI Studio (`utilidad_directa/Archive 4`) y las que usa el índice ALPS (Taoka 2017).
- Para la figura QC se exportan también txy, txz y tyz. Con el tensor completo se calcula el color-FA = |V1|·FA, donde V1 es
  el autovector del mayor autovalor (Pajevic & Pierpaoli 1999, Magn Reson Med 42:526-40). Rojo = izquierda-derecha,
  verde = antero-posterior, azul = cráneo-caudal. Es la codificación con la que los neurorradiólogos ubican las fibras
  de proyección (azul) y de asociación (verde) (Marín et al. 2025). Solo se usa para mirar; no entra en ningún cálculo.
"""
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

from . import dsi_studio, entrada

METRICAS = ("fa", "md", "txx", "tyy", "tzz")
FUERA_DIAGONAL = ("txy", "txz", "tyz")  # solo para el color-FA de la figura QC


def reconstruir_dti(nifti, bval, bvec, carpeta, affine_atlas, forma_atlas):
    """Tensor con DSI Studio y mapas en la grilla del atlas. Devuelve {métrica: ruta NIfTI} (METRICAS y FUERA_DIAGONAL)."""
    c = Path(carpeta)
    # DSI Studio busca el .bval y el .bvec con el mismo nombre del NIfTI y avisa si no están, aunque se le pasen.
    base = entrada._quitar_ext(Path(nifti))
    for origen, ext in ((bval, ".bval"), (bvec, ".bvec")):
        if Path(origen).resolve() != base.with_suffix(ext).resolve():
            shutil.copyfile(origen, base.with_suffix(ext))
    entrada.crear_src(nifti, base.with_suffix(".bval"), base.with_suffix(".bvec"), c, nombre="dwi_atlas.sz")
    fz = c / "dti.fz"
    dsi_studio.correr("rec", c, source=(c / "dwi_atlas.sz").resolve(), method=1, other_output="md,tensor",
                      make_isotropic=0, output=fz.name, overwrite=1)
    dsi_studio.correr("exp", c, source=fz.name, export=",".join(METRICAS + FUERA_DIAGONAL))
    rutas = {m: c / f"{fz.name}.{m}.nii.gz" for m in METRICAS + FUERA_DIAGONAL}
    for ruta in rutas.values():
        a_grilla(ruta, affine_atlas, forma_atlas)
    return rutas


def a_grilla(ruta, affine, forma):
    """Reordena un NIfTI exportado por DSI Studio a la orientación de la grilla dada y lo reescribe."""
    img = nib.load(str(ruta))
    cambio = nib.orientations.ornt_transform(nib.io_orientation(img.affine), nib.io_orientation(affine))
    img = img.as_reoriented(cambio)
    if img.shape[:3] != tuple(forma) or not np.allclose(img.affine, affine, atol=1e-3):
        raise ValueError(f"{Path(ruta).name} no quedó en la grilla del atlas: {img.shape}, {np.round(img.affine, 3)}")
    nib.save(nib.Nifti1Image(np.asarray(img.dataobj, dtype=np.float32), affine), str(ruta))


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
