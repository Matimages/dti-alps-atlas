"""Pipeline completo (estructura acordada con la prof. Chabert, reuniones del 2026-11-03 y 2026-11-17).

1 entrada → 2 eddy + movimiento → 3 FA del sujeto → 4 registro afín al atlas HCP1065 → 5 DWI al atlas con bvecs
rotados → 6 tensor DTI en el atlas → 7 índice ALPS con las ROIs esféricas de Liu et al. 2024.
El tensor se calcula después del registro (decisión de la prof. Chabert), para que Dxx, Dyy y Dzz queden en los ejes del
atlas. Las ROIs las iban a dibujar los neurorradiólogos; como probablemente no será posible, se usan las de Liu como
referencia. Lo usan la CLI (`python -m alps`) y la app Streamlit. Cada paso cita su fuente en su módulo.
"""
import re
import shutil
from pathlib import Path

import nibabel as nib
import numpy as np

from . import entrada, indice, informe, preproceso, registro, rois, salida, tensor

RESTOS = ("dwi*.sz", "dwi_atlas*", "dti.fz*", "eddy*", "b0*", "acqparams.txt", "index.txt", "fa_sujeto*",
          "registro_afin.txt", "rois_atlas.nii.gz", "alps.csv", "qc_*.png", "fsl.log", "dsi_studio.log", "informe.*",
          "nifti", "dicom_*")


def _id_desde_ruta(ruta):
    nombre = Path(ruta).name
    nombre = re.sub(r"(\.nii\.gz|\.nii|\.zip)$", "", nombre)
    return re.sub(r"_dwi$", "", nombre)


def _limpiar(carpeta):
    """Borra los archivos de una corrida anterior en la carpeta (también nifti/ y dicom_*/ de un DICOM anterior)."""
    for patron in RESTOS:
        for viejo in carpeta.glob(patron):
            if viejo.is_dir():
                shutil.rmtree(viejo)
            else:
                viejo.unlink()


def ejecutar(ruta_entrada, carpeta_salida, bval=None, bvec=None, id_sujeto=None, avisar=print):
    """Corre los 7 pasos y escribe todo en carpeta_salida.

    Devuelve {archivos: {nombre: ruta}, fila: {id, medias, alps_L, alps_R, alps}, versiones, pasos}
    (pasos: ver alps/informe.py).
    """
    c = Path(carpeta_salida).resolve()
    c.mkdir(parents=True, exist_ok=True)
    id_sujeto = id_sujeto or _id_desde_ruta(ruta_entrada)
    _limpiar(c)

    avisar("1/7 Leyendo el DWI y validando bval/bvec")
    nifti, f_bval, f_bvec = entrada.resolver_entrada(ruta_entrada, c, bval, bvec)

    avisar("2/7 Corrección de corrientes de Foucault y movimiento (FSL eddy)")
    dwi_eddy, bvec_eddy, mascara = preproceso.corregir(nifti, f_bval, f_bvec, c)

    avisar("3/7 FA del sujeto (para el registro)")
    fa, affine_fa = registro.fa_nativo(dwi_eddy, f_bval, bvec_eddy, mascara)
    nib.save(nib.Nifti1Image(fa.astype(np.float32), affine_fa), str(c / "fa_sujeto.nii.gz"))

    avisar("4/7 Registro afín del FA al atlas HCP1065")
    template, affine_t = registro.cargar_template()
    mapa = registro.registrar(fa, affine_fa, template, affine_t)
    np.savetxt(c / "registro_afin.txt", mapa.affine, fmt="%.6f")
    nib.save(nib.Nifti1Image(mapa.transform(fa).astype(np.float32), affine_t), str(c / "fa_sujeto_en_atlas.nii.gz"))

    avisar("5/7 DWI al atlas con los bvecs rotados")
    dwi_atlas, bvec_atlas = registro.dwi_al_atlas(dwi_eddy, bvec_eddy, mapa, c / "dwi_atlas.nii.gz",
                                                  c / "dwi_atlas.bvec")

    avisar("6/7 Tensor DTI en el atlas (DSI Studio)")
    mapas = tensor.reconstruir_dti(dwi_atlas, f_bval, bvec_atlas, c, affine_t, template.shape)

    avisar("7/7 Índice ALPS en las ROIs y salidas")
    esferas = rois.esferas(template.shape)
    t = {m: nib.load(str(r)).get_fdata(dtype="float32") for m, r in mapas.items()}
    medias = indice.medias_en_rois(t["txx"], t["tyy"], t["tzz"], esferas)
    fila = {"id": id_sujeto, **medias, **indice.indice_alps(medias)}

    archivos = {m: mapas[m] for m in tensor.METRICAS}
    archivos["csv"] = c / "alps.csv"
    archivos["rois"] = c / "rois_atlas.nii.gz"
    salida.guardar_csv(fila, archivos["csv"])
    salida.guardar_rois(esferas, affine_t, archivos["rois"])
    archivos["figura_alps"] = salida.figura_qc(tensor.color_fa(t), esferas, fila, c / "qc_alps.png", titulo=id_sujeto)
    archivos["figura"] = tensor.figura_qc(c, c / "qc_dti.png", titulo=id_sujeto)
    archivos["figura_eddy"] = preproceso.figura_eddy(c, c / "qc_eddy.png", nifti)
    archivos["informe"], versiones, pasos = informe.generar(c, nifti, f_bval, template, fila)
    return {"archivos": archivos, "fila": fila, "versiones": versiones, "pasos": pasos}
