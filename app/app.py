"""App Streamlit delgada: recibe el DWI, llama a alps.pipeline.ejecutar y muestra el resultado.

Uso: streamlit run app/app.py
"""
import sys
import tempfile
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from alps.pipeline import _id_desde_ruta, ejecutar  # noqa: E402

st.set_page_config(page_title="DTI-ALPS con atlas", layout="wide")
st.title("Índice DTI-ALPS con atlas estándar")
st.caption("Pasos 1-3: entrada, corrección de eddy y movimiento, y tensor DTI, con DSI Studio y FSL eddy "
           "(como Marín et al. 2025). El atlas, las ROIs y el índice ALPS vienen después.")

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

if st.button("Procesar", type="primary", disabled=entrada is None):
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
    rutas = st.session_state["resultado"]
    st.image(str(rutas["figura"]))
    st.caption(f"Archivos en {rutas['figura'].parent}")
    for col, (nombre, ruta) in zip(st.columns(len(rutas)), rutas.items()):
        col.download_button(nombre.upper() if nombre != "figura" else "Figura QC", ruta.read_bytes(), ruta.name)
