"""Paso 1: entrada del DWI y creación del archivo fuente de DSI Studio (.sz).

Acepta:
- carpeta con DICOM o .zip con DICOM: se convierte a NIfTI + .bval + .bvec con dcm2niix (C. Rorden,
  https://github.com/rordenlab/dcm2niix; paquete pip `dcm2niix`). Los bvec quedan en los ejes de la imagen (convención FSL).
- NIfTI (.nii / .nii.gz): DEBE venir con su .bval y su .bvec. El encabezado NIfTI no guarda los valores b ni las
  direcciones del gradiente. Por eso, cuando dcm2niix convierte un DICOM, los deja en esos dos archivos de texto aparte.
  En ds001378 (formato BIDS) vienen junto al NIfTI con el mismo nombre (sub-XX_ses-XX_dwi.bval / .bvec).
  Sin ellos no se puede calcular el tensor, así que se detiene con error. No basta con avisar: DSI Studio solo advierte
  y crea el .sz igual (verificado con la release 2026.7.25).

Después, `dsi_studio --action=src --source=<nifti> --bval=<bval> --bvec=<bvec>` crea el .sz
(https://dsi-studio.labsolver.org/doc/cli_t1.html). Es el mismo primer paso de Marín et al. 2025 y de la tesis (archivo SRC).
"""
import tempfile
import zipfile
from pathlib import Path

import nibabel as nib
import numpy as np

from . import dsi_studio


def _quitar_ext(ruta):
    nombre = ruta.name
    for ext in (".nii.gz", ".nii"):
        if nombre.endswith(ext):
            return ruta.with_name(nombre[: -len(ext)])
    return ruta.with_suffix("")


def dicom_a_nifti(carpeta_dicom, carpeta_salida):
    """Convierte una carpeta DICOM con dcm2niix y devuelve la ruta del NIfTI que tiene .bval/.bvec."""
    import dcm2niix  # paquete pip que trae el binario

    carpeta_salida = Path(carpeta_salida)
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    r = dcm2niix.main(["-z", "y", "-f", "dwi_%s", "-o", str(carpeta_salida), str(carpeta_dicom)],
                      capture_output=True, text=True)
    if r.returncode != 0:
        raise ValueError(f"dcm2niix falló (código {r.returncode}): {r.stdout[-500:]}")
    candidatos = [n for n in sorted(carpeta_salida.glob("*.nii.gz"))
                  if _quitar_ext(n).with_suffix(".bval").exists()]
    if len(candidatos) != 1:
        raise ValueError(f"dcm2niix generó {len(candidatos)} series con .bval; se espera exactamente 1 DWI.")
    return candidatos[0]


def resolver_entrada(entrada, carpeta_trabajo, bval=None, bvec=None):
    """Devuelve (nifti, bval, bvec) a partir de un NIfTI, una carpeta DICOM o un zip DICOM."""
    entrada = Path(entrada)
    carpeta_trabajo = Path(carpeta_trabajo)
    if entrada.suffix.lower() == ".zip":
        carpeta_dicom = Path(tempfile.mkdtemp(dir=carpeta_trabajo, prefix="dicom_"))
        with zipfile.ZipFile(entrada) as z:
            z.extractall(carpeta_dicom)
        entrada = carpeta_dicom
    if entrada.is_dir():
        entrada = dicom_a_nifti(entrada, carpeta_trabajo / "nifti")
    if not entrada.exists():
        raise FileNotFoundError(f"No se encontró {entrada}")
    base = _quitar_ext(entrada)
    bval = Path(bval) if bval else base.with_suffix(".bval")
    bvec = Path(bvec) if bvec else base.with_suffix(".bvec")
    faltan = [f.name for f in (bval, bvec) if not f.exists()]
    if faltan:
        raise FileNotFoundError(
            f"Falta {' y '.join(faltan)}. Un NIfTI no guarda los valores b ni las direcciones del gradiente: "
            "hay que entregar el .bval y el .bvec que generó la conversión desde DICOM, o entregar el DICOM.")
    validar(entrada, bval, bvec)
    return entrada, bval, bvec


def validar(nifti, bval, bvec):
    """Comprueba que haya un valor b y una dirección por volumen, y al menos un b0.

    Umbral b0 = 50 s/mm²: el default `b0_threshold` de `dipy.core.gradients.gradient_table`.
    """
    forma = nib.load(str(nifti)).shape
    n_vol = forma[3] if len(forma) == 4 else 1
    bvals = np.loadtxt(bval, ndmin=1)
    bvecs = np.loadtxt(bvec, ndmin=2)
    if bvecs.shape[0] != 3:
        bvecs = bvecs.T
    if not (len(bvals) == bvecs.shape[1] == n_vol):
        raise ValueError(f"El DWI tiene {n_vol} volúmenes, el .bval {len(bvals)} valores y el .bvec "
                         f"{bvecs.shape[1]} direcciones: deben coincidir.")
    if not np.any(bvals < 50):
        raise ValueError("No hay ningún volumen b0 (b < 50 s/mm²).")


def crear_src(nifti, bval, bvec, carpeta):
    """Crea <carpeta>/dwi.sz con DSI Studio y devuelve su ruta."""
    salida = Path(carpeta) / "dwi.sz"
    dsi_studio.correr("src", carpeta, source=Path(nifti).resolve(), bval=Path(bval).resolve(),
                      bvec=Path(bvec).resolve(), output=salida.name, overwrite=1)
    return salida
