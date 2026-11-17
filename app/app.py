"""App Streamlit delgada: recibe el DWI, llama a alps.pipeline.ejecutar y muestra el resultado con el detalle de cada paso.

Uso: streamlit run app/app.py (Linux o macOS; en Windows, dentro de WSL)
"""
import re
import sys
import tempfile
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from alps import atlas, informe, tensor  # noqa: E402
from alps.pipeline import _id_desde_ruta, ejecutar  # noqa: E402

RESULTADOS = RAIZ / "resultados_app"
NOMBRES = {"fa": "FA", "md": "MD", "txx": "Dxx (txx)", "tyy": "Dyy (tyy)", "tzz": "Dzz (tzz)",
           "figura": "Figura QC", "figura_eddy": "Figura eddy", "informe": "Informe (.md)"}


def _ruta_local(texto):
    """Acepta rutas de Windows (C:\\...) cuando la app corre en WSL, donde ese disco está en /mnt/c."""
    texto = texto.strip().strip('"')
    windows = re.match(r"^([A-Za-z]):[\\/](.*)$", texto)
    if windows and sys.platform != "win32" and Path("/mnt").is_dir():
        return Path("/mnt", windows[1].lower(), *re.split(r"[\\/]+", windows[2]))
    return Path(texto)


def _archivos(carpeta):
    rutas = {m: carpeta / f"dti.fz.{m}.nii.gz" for m in tensor.METRICAS}
    rutas = {**rutas, "figura": carpeta / "qc_dti.png", "figura_eddy": carpeta / "qc_eddy.png",
             "informe": carpeta / "informe.md"}
    return {nombre: ruta for nombre, ruta in rutas.items() if ruta.exists()}


def _mostrar_paso(paso, carpeta):
    st.markdown(paso["que_hizo"])
    if paso.get("figura") and (carpeta / paso["figura"]).exists():
        st.image(str(carpeta / paso["figura"]))
    for i in range(0, len(paso["datos"]), 4):  # filas de hasta 4 métricas, para que no se corten
        for col, (etiqueta, valor) in zip(st.columns(4), paso["datos"][i:i + 4]):
            col.metric(etiqueta, valor)
    if paso["tabla"]:
        st.dataframe(paso["tabla"], hide_index=True, width="stretch")
    for nota in paso["notas"]:
        (st.warning if "SUPUESTO" in nota or "outlier" in nota else st.info)(nota)
    with st.expander("Comandos ejecutados (copiados del log)"):
        st.code("\n\n".join(paso["comandos"]), language="bash", wrap_lines=True)
    st.markdown("**Documentación en que se basa**")
    st.markdown("\n".join(f"- [{texto}]({url})" if url else f"- {texto}" for texto, url in paso["fuentes"]))


def _mostrar_resultado(carpeta, versiones, pasos):
    rutas = _archivos(carpeta)
    st.subheader(f"Resultado: {carpeta.name}")
    st.image(str(rutas["figura"]))
    st.subheader("Detalle del procesamiento")
    st.caption("Qué hizo cada paso, con qué parámetros y en qué documentación se basa. Versiones: "
               + " · ".join(f"{k} {v}" for k, v in versiones.items()))
    for pestaña, paso in zip(st.tabs([p["titulo"] for p in pasos]), pasos):
        with pestaña:
            _mostrar_paso(paso, carpeta)
    st.subheader("Descargas")
    st.caption(f"Carpeta: {carpeta}")
    for col, (nombre, ruta) in zip(st.columns(len(rutas)), rutas.items()):
        col.download_button(NOMBRES[nombre], ruta.read_bytes(), ruta.name, width="stretch")


st.set_page_config(page_title="DTI-ALPS con atlas", layout="wide")
st.title("DTI-ALPS con atlas estándar · pasos 1-3")
st.caption("Implementado: entrada, corrección de eddy y movimiento, y tensor DTI, con DSI Studio y FSL eddy "
           "(como Marín et al. 2025). Pendiente: el atlas con las ROIs, el registro y el índice ALPS.")

procesar, candidatos = st.tabs(["Procesar un sujeto (pasos 1-3)", "Atlas candidatos (paso 4, en discusión)"])

with procesar:
    modo = st.radio("Entrada", ["Subir archivos", "Ruta local", "Sujeto ya procesado"], horizontal=True)
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
    elif modo == "Ruta local":
        ruta = st.text_input("Ruta a un NIfTI DWI (con .bval/.bvec del mismo nombre), carpeta DICOM o .zip DICOM")
        if ruta:
            entrada = _ruta_local(ruta)
            if not entrada.exists():
                st.warning(f"No existe: {entrada}")
                entrada = None
    else:  # ver un sujeto procesado antes, sin volver a correr eddy (~45 min)
        hechos = sorted(p.parent.name for p in RESULTADOS.glob("*/informe.json"))
        elegido = st.selectbox("Sujeto", hechos, index=None, placeholder="Elige un sujeto procesado")
        if elegido:
            st.session_state["resultado"] = (RESULTADOS / elegido, *informe.leer(RESULTADOS / elegido))

    if entrada is not None:
        id_sujeto = st.text_input("Identificador", value=_id_desde_ruta(entrada))

    if modo != "Sujeto ya procesado" and st.button("Procesar", type="primary", disabled=entrada is None):
        with st.status("Procesando… (eddy tarda unos 45 min)", expanded=True) as estado:
            try:
                r = ejecutar(entrada, RESULTADOS / id_sujeto, bval, bvec, id_sujeto=id_sujeto, avisar=st.write)
                st.session_state["resultado"] = (r["archivos"]["figura"].parent, r["versiones"], r["pasos"])
                estado.update(label="Listo", state="complete", expanded=False)
            except Exception as e:  # se muestra el error al usuario en vez de cortar la app
                estado.update(label="Error", state="error")
                st.exception(e)

    if "resultado" in st.session_state:
        _mostrar_resultado(*st.session_state["resultado"])

with candidatos:
    st.markdown(
        "Se comparan dos candidatos en el corte de las ROIs de Liu et al. 2024. Ambos vienen con FSL y están en la "
        "misma grilla MNI de 1 mm.")
    c1, c2 = st.columns(2)
    c1.markdown("**JHU-ICBM-FA 1 mm**: el template de Liu et al. 2024. Solo FA, sin la dirección de las fibras.")
    c2.markdown("**FSL HCP1065 1 mm**: FA y dirección principal (V1) promedio de 1065 sujetos. En color-FA se ven el "
                "azul (proyección) y el verde (asociación) con que los neurorradiólogos ubicaron las ROIs en "
                "Marín et al. 2025.")
    figura = RESULTADOS / "atlas_candidatos.png"
    try:
        if not figura.exists():
            RESULTADOS.mkdir(exist_ok=True)
            atlas.figura_candidatos(figura)
        st.image(str(figura))
    except FileNotFoundError as e:
        st.info(str(e))
    st.caption("Fuentes: FSL 6.0.7.23 (`data/atlases/JHU`, `data/standard/FSL_HCP1065_*`); color-FA: Pajevic & "
               "Pierpaoli 1999, Magn Reson Med 42:526-40; ROIs: Liu et al. 2024 (alps/rois.py).")
