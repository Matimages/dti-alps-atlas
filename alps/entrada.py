"""Etapa 1: lectura del DWI.

Acepta tres formas de entrada:
- NIfTI (.nii / .nii.gz) con .bval y .bvec al lado (mismo nombre) o indicados explícitamente;
- carpeta con DICOM;
- archivo .zip con DICOM.

Los DICOM se convierten con dcm2niix (Rorden; paquete pip `dcm2niix`), que genera NIfTI + .bval + .bvec
con los bvec en los ejes de la imagen (convención FSL), igual a lo que espera dtifit en [alps.sh].
"""
import tempfile
import zipfile
from pathlib import Path

import nibabel as nib
from dipy.core.gradients import gradient_table
from dipy.io.gradients import read_bvals_bvecs


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
    base = _quitar_ext(entrada)
    bval = Path(bval) if bval else base.with_suffix(".bval")
    bvec = Path(bvec) if bvec else base.with_suffix(".bvec")
    for f in (entrada, bval, bvec):
        if not f.exists():
            raise FileNotFoundError(f"No se encontró {f}")
    return entrada, bval, bvec


def cargar_dwi(nifti, bval, bvec):
    """Carga el DWI: devuelve (datos 4D float32, affine, gtab de DIPY)."""
    img = nib.load(str(nifti))
    datos = img.get_fdata(dtype="float32")
    bvals, bvecs = read_bvals_bvecs(str(bval), str(bvec))
    if datos.ndim != 4 or datos.shape[3] != len(bvals):
        raise ValueError(f"El DWI tiene forma {datos.shape} pero hay {len(bvals)} valores b.")
    return datos, img.affine, gradient_table(bvals, bvecs=bvecs)
