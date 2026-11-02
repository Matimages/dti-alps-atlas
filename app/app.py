"""App Streamlit delgada: recibe el DWI, llama a alps.pipeline.ejecutar y muestra el resultado.

Uso: streamlit run app/app.py
"""
import sys
import tempfile
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
try:  # DIPY escribe mensajes Unicode; la consola de Windows (cp1252) no los puede mostrar
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from alps.pipeline import _id_desde_ruta, ejecutar  # noqa: E402

st.set_page_config(page_title="DTI-ALPS con atlas", layout="wide")
st.title("Índice DTI-ALPS con atlas estándar")
st.caption("Pipeline de Liu, Barisano et al. 2024 (Aging Dis), reimplementado con DIPY. "
           "Template JHU-ICBM-FA-1mm, registro afín y ROIs esféricas de 2.5 mm. Tarda unos 10 minutos.")

modo = st.radio("Entrada", ["Subir archivos", "Ruta local"], horizontal=True)
entrada = bval = bvec = id_sujeto = None
if modo == "Subir archivos":
    archivos = st.file_uploader("Un .zip con DICOM, o un NIfTI (.nii/.nii.gz) junto con su .bval y su .bvec",
                                accept_multiple_files=True)
    if archivos:
        tmp = Path(tempfile.mkdtemp(prefix="alps_"))
        for a in archivos:
            (tmp / a.name).write_bytes(a.getbuffer())
        nombres = [a.name for a in archivos]
        zips = [n for n in nombres if n.lower().endswith(".zip")]
        niftis = [n for n in nombres if n.lower().endswith((".nii", ".nii.gz"))]
        bvals = [n for n in nombres if n.lower().endswith(".bval")]
        bvecs = [n for n in nombres if n.lower().endswith(".bvec")]
        if len(zips) == 1:
            entrada = tmp / zips[0]
        elif len(niftis) == 1 and len(bvals) == 1 and len(bvecs) == 1:
            entrada, bval, bvec = tmp / niftis[0], tmp / bvals[0], tmp / bvecs[0]
        else:
            st.warning("Sube un .zip DICOM, o exactamente un NIfTI, un .bval y un .bvec.")
else:
    ruta = st.text_input("Ruta a un NIfTI DWI (con .bval/.bvec del mismo nombre), carpeta DICOM o .zip DICOM")
    if ruta:
        entrada = Path(ruta.strip().strip('"'))
        if not entrada.exists():
            st.warning(f"No existe: {entrada}")
            entrada = None

if entrada is not None:
    id_sujeto = st.text_input("Identificador", value=_id_desde_ruta(entrada))

if st.button("Calcular ALPS", type="primary", disabled=entrada is None):
    with st.status("Procesando…", expanded=True) as estado:
        try:
            r = ejecutar(entrada, RAIZ / "resultados_app" / id_sujeto, bval, bvec,
                         id_sujeto=id_sujeto, avisar=st.write)
            st.session_state["resultado"] = r
            estado.update(label="Listo", state="complete")
        except Exception as e:  # se muestra el error al usuario en vez de cortar la app
            estado.update(label="Error", state="error")
            st.exception(e)

if "resultado" in st.session_state:
    fila, rutas = st.session_state["resultado"]["fila"], st.session_state["resultado"]["archivos"]
    c1, c2, c3 = st.columns(3)
    c1.metric("ALPS izquierdo", f"{fila['alps_L']:.3f}")
    c2.metric("ALPS derecho", f"{fila['alps_R']:.3f}")
    c3.metric("ALPS (promedio)", f"{fila['alps']:.3f}")
    st.image(str(rutas["figura"]))
    st.dataframe([fila], hide_index=True)
    st.caption(f"Archivos en {rutas['csv'].parent}")
    d1, d2, d3, d4 = st.columns(4)
    d1.download_button("CSV", rutas["csv"].read_bytes(), rutas["csv"].name, "text/csv")
    d2.download_button("Figura QC", rutas["figura"].read_bytes(), rutas["figura"].name, "image/png")
    d3.download_button("ROIs (NIfTI)", rutas["rois"].read_bytes(), rutas["rois"].name)
    d4.download_button("FA en template (NIfTI)", rutas["fa"].read_bytes(), rutas["fa"].name)
