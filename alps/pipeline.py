"""Pipeline completo (Liu, Barisano et al. 2024): DWI -> preproceso -> tensor -> registro afín -> ROIs -> ALPS.

Lo usan la CLI (`python -m alps`) y la app Streamlit. Cada etapa documenta su fuente en su módulo.
"""
import re
from pathlib import Path

from . import entrada, indice, preproceso, registro, rois, salida, tensor


def _id_desde_ruta(ruta):
    nombre = Path(ruta).name
    nombre = re.sub(r"(\.nii\.gz|\.nii|\.zip)$", "", nombre)
    return re.sub(r"_dwi$", "", nombre)


def ejecutar(ruta_entrada, carpeta_salida, bval=None, bvec=None, template=None, id_sujeto=None, avisar=print):
    """Calcula el ALPS y escribe las salidas en carpeta_salida. Devuelve {fila, archivos}."""
    carpeta_salida = Path(carpeta_salida)
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    id_sujeto = id_sujeto or _id_desde_ruta(ruta_entrada)

    avisar("1/5 Leyendo el DWI")
    nifti, f_bval, f_bvec = entrada.resolver_entrada(ruta_entrada, carpeta_salida, bval, bvec)
    datos, affine, gtab = entrada.cargar_dwi(nifti, f_bval, f_bvec)

    avisar("2/5 Denoising MP-PCA y corrección de Gibbs")
    datos = preproceso.preprocesar(datos)

    avisar("3/5 Ajustando el tensor")
    mapas = tensor.ajustar_tensor(datos, gtab)

    avisar("4/5 Registro afín del FA al template JHU-ICBM-FA-1mm (la etapa más lenta, ~5 min)")
    fa_template, affine_template = registro.cargar_template(template)
    mapa_afin = registro.registrar(mapas["FA"], affine, fa_template, affine_template)
    en_template = {k: registro.al_template(mapa_afin, mapas[k]) for k in ("Dxx", "Dyy", "Dzz", "FA", "color_FA")}

    avisar("5/5 Calculando el índice en las ROIs y escribiendo las salidas")
    mascaras = rois.esferas(fa_template.shape)
    medias = indice.medias_en_rois(en_template["Dxx"], en_template["Dyy"], en_template["Dzz"], mascaras)
    fila = {"id": id_sujeto, **medias, **indice.indice_alps(medias)}

    archivos = {
        "csv": carpeta_salida / "alps.csv",
        "rois": carpeta_salida / "rois_en_template.nii.gz",
        "fa": carpeta_salida / "FA_en_template.nii.gz",
        "figura": carpeta_salida / "qc_alps.png",
    }
    salida.guardar_csv(fila, archivos["csv"])
    salida.guardar_nifti(mascaras, en_template["FA"], affine_template, archivos["rois"], archivos["fa"])
    salida.figura_qc(en_template["color_FA"], mascaras, fila, archivos["figura"], titulo=id_sujeto)
    return {"fila": fila, "archivos": archivos}
