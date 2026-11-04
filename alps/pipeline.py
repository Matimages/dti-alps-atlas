"""Pipeline, pasos 1-3 (reunión con la prof. Chabert, 2026-11-03): entrada -> eddy + movimiento -> tensor DTI.

Los pasos 4-6 (atlas con ROIs dibujadas por los neurorradiólogos, registro y ALPS) quedan fuera hasta que se
defina el atlas. El código anterior de esos pasos (registro.py, rois.py, indice.py, salida.py) se conserva, pero
no se ejecuta. Lo usan la CLI (`python -m alps`) y la app Streamlit. Cada paso cita su fuente en su módulo.
"""
import re
from pathlib import Path

from . import entrada, preproceso, tensor


def _id_desde_ruta(ruta):
    nombre = Path(ruta).name
    nombre = re.sub(r"(\.nii\.gz|\.nii|\.zip)$", "", nombre)
    return re.sub(r"_dwi$", "", nombre)


def ejecutar(ruta_entrada, carpeta_salida, bval=None, bvec=None, id_sujeto=None, avisar=print):
    """Corre los pasos 1-3 y escribe todo en carpeta_salida. Devuelve {métrica o 'figura': ruta}."""
    carpeta_salida = Path(carpeta_salida).resolve()
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    id_sujeto = id_sujeto or _id_desde_ruta(ruta_entrada)

    avisar("1/3 Leyendo el DWI y creando el archivo fuente de DSI Studio")
    nifti, f_bval, f_bvec = entrada.resolver_entrada(ruta_entrada, carpeta_salida, bval, bvec)
    src = entrada.crear_src(nifti, f_bval, f_bvec, carpeta_salida)

    avisar("2/3 Corrección de corrientes de Foucault (eddy) y movimiento")
    src = preproceso.corregir(src, carpeta_salida)

    avisar("3/3 Reconstrucción DTI y exportación de los mapas")
    archivos = tensor.reconstruir_dti(src, carpeta_salida)
    archivos["figura"] = carpeta_salida / "qc_dti.png"
    tensor.figura_qc({m: archivos[m] for m in tensor.METRICAS}, archivos["figura"], titulo=id_sujeto)
    return archivos
