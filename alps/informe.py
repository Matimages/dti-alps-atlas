"""Informe del procesamiento: qué hizo cada paso, con qué comando y parámetros, y en qué documentación se basa.

Pensado para que alguien que sabe del tema revise cada fase, en la app o en informe.md. No recalcula nada: lee lo que
dejaron las herramientas en la carpeta del sujeto. Eso incluye dsi_studio.log (cada comando de DSI Studio, escrito por
alps/dsi_studio.py), los archivos de FSL eddy (dwi.sz.corrected.eddy_*) y los NIfTI.

Cada paso es un dict: titulo, que_hizo, comandos, datos [(etiqueta, valor)], tabla [dict], notas y fuentes [(texto, url)].
"""
import json
import os
import re
from pathlib import Path

import nibabel as nib
import numpy as np

DSI_DOC = "https://dsi-studio.labsolver.org/doc"
DSI_CODIGO = "https://github.com/frankyeh/DSI-Studio/blob/master/libs/dsi/image_model.cpp"
EDDY_DOC = "https://fsl.fmrib.ox.ac.uk/fsl/docs/diffusion/eddy"

EDDY_PARAMETROS = {  # parámetro: qué es (guía de eddy)
    "slm": "Modelo de segundo nivel; la guía sugiere considerar 'linear' con pocas direcciones",
    "repol": "Reemplazo de cortes outlier",
    "ol_nstd": "Umbral (desviaciones estándar) para marcar un corte como outlier",
    "mporder": "Corrección slice-to-volume (0 = desactivada)",
    "niter": "Iteraciones",
    "fwhm": "Suavizado durante la estimación (mm)",
    "flm": "Modelo de los campos de eddy",
    "resamp": "Remuestreo final ('jac': única opción sin fase inversa)",
    "nthr": "Hilos de CPU",
}


def _bloques(log):
    """Separa dsi_studio.log en (comando, salida) por cada llamada."""
    partes = re.split(r"^\$ ", log, flags=re.M)[1:]
    return [tuple((p + "\n").split("\n", 1)) for p in partes]


def _valor(texto, clave):
    m = re.search(rf"{re.escape(clave)}=?\s*(\S+)", texto)
    return m[1] if m else "—"


def _voxeles(img):
    """[(Grilla, ...), (Vóxel, ...)] cortos, para que quepan en una métrica de la app."""
    return [("Grilla", "×".join(map(str, img.shape[:3]))),
            ("Vóxel (mm)", "×".join(f"{z:g}" for z in img.header.get_zooms()[:3]))]


def _paso1(carpeta, nifti, bval, bloques):
    img = nib.load(str(nifti))
    valores, cuentas = np.unique(np.round(np.loadtxt(bval, ndmin=1), -1), return_counts=True)
    convertido = (Path(carpeta) / "nifti").is_dir()
    return {
        "titulo": "1. Entrada",
        "que_hizo": ("Convirtió el DICOM a NIfTI + .bval + .bvec con dcm2niix. " if convertido else "")
        + "Verificó que hubiera un .bval y un .bvec (el NIfTI no guarda los valores b ni las direcciones), con un valor "
          "y una dirección por volumen y al menos un b0. Después creó el archivo fuente `dwi.sz` de DSI Studio.",
        "comandos": [c for c, _ in bloques if "--action=src" in c],
        "datos": [("Volúmenes", str(img.shape[3])), *_voxeles(img),
                  ("Valores b (s/mm²)", " · ".join(f"{v:g} ×{n}" for v, n in zip(valores, cuentas)))],
        "tabla": [],
        "notas": [f"Entrada: `{Path(nifti).name}` con `{Path(bval).name}` y su .bvec."],
        "fuentes": [("dcm2niix (DICOM → NIfTI + bval/bvec)", "https://github.com/rordenlab/dcm2niix"),
                    ("DSI Studio `--action=src`", f"{DSI_DOC}/cli_t1.html"),
                    ("Marín et al. 2025 y tesis previa: primer paso, archivo SRC de DSI Studio", None)],
    }


def _paso2(carpeta, bloques):
    c = Path(carpeta)
    acqp = (c / "dwi.sz.topup.acqparams.txt").read_text().split()
    valores = (c / "dwi.sz.corrected.eddy_values_of_all_input_parameters").read_text()
    rms = np.loadtxt(c / "dwi.sz.corrected.eddy_movement_rms")
    outliers = (c / "dwi.sz.corrected.eddy_outlier_report").read_text().strip().splitlines()
    notas = [f"`--acqp {' '.join(acqp)}`: fase en el eje y (antero-posterior) y readout de {acqp[3]} s. **SUPUESTO**: "
             "ds001378 no trae el JSON con la dirección de fase. El FAQ de eddy indica que 0.05 s sirve si el readout no "
             "se conoce.",
             "Sin TOPUP: no hay una adquisición con codificación de fase inversa."]
    if outliers:  # líneas de eddy: "Slice 7 in scan 3 is an outlier with mean -21.6 standard deviations off, ..."
        partes = [re.search(r"Slice (\d+) in scan (\d+) .*?mean (\S+) standard", o) for o in outliers]
        notas.append("Cortes outlier detectados, que no se reemplazan porque `--repol=False` (numeración de eddy, desde 0): "
                     + "; ".join(f"corte {p[1]} del volumen {p[2]} ({float(p[3]):.1f} DE)" for p in partes if p) + ".")
    return {
        "titulo": "2. Eddy y movimiento",
        "figura": "qc_eddy.png",
        "que_hizo": "DSI Studio escribió el DWI y los gradientes en el formato de FSL (invierte el eje y: DSI Studio usa "
                    "LPS y FSL LAS) y generó una máscara cerebral con su U-Net. FSL eddy estimó para cada volumen el "
                    "movimiento rígido y la distorsión por corrientes de Foucault, y remuestreó el DWI corregido. DSI "
                    "Studio lo recargó con los bvecs rotados por eddy y lo guardó como `dwi_eddy.sz`.",
        "comandos": [cmd for cmd, _ in bloques if "--cmd=eddy" in cmd]
        + [(c / "dwi.sz.corrected.eddy_command_txt").read_text().strip()],
        "datos": [("Mov. absoluto medio", f"{rms[1:, 0].mean():.2f} mm"), ("Mov. absoluto máx.", f"{rms[:, 0].max():.2f} mm"),
                  ("Mov. relativo medio", f"{rms[1:, 1].mean():.2f} mm"), ("Mov. relativo máx.", f"{rms[:, 1].max():.2f} mm"),
                  ("Cortes outlier", str(len(outliers))),
                  ("Bvecs rotados", "sí" if (c / "dwi.sz.corrected.eddy_rotated_bvecs").exists() else "no")],
        "tabla": [{"Parámetro": f"--{p}", "Valor": _valor(valores, "--" + p), "Qué es": d}
                  for p, d in EDDY_PARAMETROS.items()],
        "notas": notas,
        "fuentes": [("DSI Studio `--action=rec`, comandos `eddy` y `save_src`", f"{DSI_DOC}/cli_t2.html"),
                    ("Código de DSI Studio que arma y lee eddy (`run_eddy`, `load_topup_eddy_result`)", DSI_CODIGO),
                    ("FSL eddy: guía de uso", f"{EDDY_DOC}/users_guide/index.html"),
                    ("FSL eddy: FAQ (`--acqp`, readout, rotación de bvecs)", f"{EDDY_DOC}/FAQ/index.html"),
                    ("Andersson & Sotiropoulos 2016, NeuroImage 125:1063-78", "https://doi.org/10.1016/j.neuroimage.2015.10.019"),
                    ("Marín et al. 2025: eddy y movimiento con DSI Studio + EDDY", None)],
    }


def _paso3(carpeta, bloques):
    rec = [(cmd, out) for cmd, out in bloques if "--method=1" in cmd and "--cmd=eddy" not in cmd]
    salida = rec[-1][1] if rec else ""
    fa = nib.load(str(Path(carpeta) / "dti.fz.fa.nii.gz"))
    return {
        "titulo": "3. Tensor DTI",
        "que_hizo": "DSI Studio ajustó el tensor de difusión vóxel a vóxel sobre el DWI corregido (`dwi_eddy.sz`) y "
                    "exportó a NIfTI el FA, el MD y los elementos diagonales del tensor (txx, tyy, tzz = Dxx, Dyy, Dzz, "
                    "en los ejes de la imagen).",
        "comandos": [cmd for cmd, _ in rec] + [cmd for cmd, _ in bloques if "--action=exp" in cmd],
        "datos": [("Método", "DTI (method = 1)"), *_voxeles(fa),
                  ("Vóxeles en la máscara", _valor(salida, "mask voxels:"))],
        "tabla": [{"Parámetro": p, "Valor": _valor(salida, p), "Qué es": d} for p, d in (
            ("other_output", "Mapas adicionales pedidos ('tensor' = txx … tzz)"),
            ("make_isotropic", "Remuestreo a vóxel isotrópico (mm); default de DSI Studio"),
            ("dti_ignore_high_b", "Ignorar b altos en el DTI (aquí solo hay b = 1000)"),
            ("check_btable", "Revisión automática de la orientación de la b-table"),
            ("bias_field_correction", "Corrección de inhomogeneidad (0 en DTI)"))],
        "notas": ["Unidades: txx, tyy, tzz en mm²/s; MD en 10⁻³ mm²/s. DSI Studio exporta el FA cuantizado en pasos "
                  "de 1/255; txx, tyy y tzz no se cuantizan."],
        "fuentes": [("DSI Studio `--action=rec --method=1` y `--other_output`", f"{DSI_DOC}/cli_t2.html"),
                    ("DSI Studio `--action=exp`", f"{DSI_DOC}/cli_exp.html"),
                    ("Marín et al. 2025 y tesis previa: DTI pidiendo \"tensor\" (txx, tyy, tzz)", None),
                    ("Taoka et al. 2017: el índice ALPS usa Dxx, Dyy y Dzz", None)],
    }


def versiones(log):
    dsi = re.search(r"^DSI Studio \(.*?\),?\s*(.*)$", log, flags=re.M)  # "DSI Studio (doi:...), Sun ... Oct 30 2026"
    fsl = Path(os.environ.get("FSLDIR", "")) / "etc" / "fslversion"
    return {"DSI Studio": dsi[1].strip() if dsi else "?",
            "FSL": fsl.read_text().split(":")[0].strip() if fsl.exists() else "?"}


def pasos(carpeta, nifti, bval):
    log = (Path(carpeta) / "dsi_studio.log").read_text(encoding="utf-8")
    bloques = _bloques(log)
    return versiones(log), [_paso1(carpeta, nifti, bval, bloques), _paso2(carpeta, bloques), _paso3(carpeta, bloques)]


def a_markdown(nombre, version, lista):
    lineas = [f"# Informe del procesamiento: {nombre}", "",
              "Versiones: " + "; ".join(f"{k} {v}" for k, v in version.items()), ""]
    for p in lista:
        lineas += [f"## {p['titulo']}", "", p["que_hizo"], ""]
        lineas += [f"![{p['titulo']}]({p['figura']})", ""] if p.get("figura") else []
        lineas += ["```", *p["comandos"], "```", ""]
        lineas += [f"- **{k}:** {v}" for k, v in p["datos"]] + [""]
        if p["tabla"]:
            lineas += ["| Parámetro | Valor | Qué es |", "|---|---|---|"]
            lineas += [f"| `{f['Parámetro']}` | {f['Valor']} | {f['Qué es']} |" for f in p["tabla"]] + [""]
        lineas += [f"> {n}" for n in p["notas"]] + ["", "**Fuentes:**"]
        lineas += [f"- {t}" + (f": {u}" if u else "") for t, u in p["fuentes"]] + [""]
    return "\n".join(lineas)


def generar(carpeta, nifti, bval):
    """Escribe <carpeta>/informe.md (para leer) e informe.json (para la app) y devuelve (ruta .md, versiones, pasos)."""
    version, lista = pasos(carpeta, nifti, bval)
    ruta = Path(carpeta) / "informe.md"
    ruta.write_text(a_markdown(Path(carpeta).name, version, lista), encoding="utf-8")
    (Path(carpeta) / "informe.json").write_text(json.dumps({"versiones": version, "pasos": lista}, ensure_ascii=False,
                                                           indent=1), encoding="utf-8")
    return ruta, version, lista


def leer(carpeta):
    """Lee informe.json de un sujeto ya procesado: (versiones, pasos)."""
    d = json.loads((Path(carpeta) / "informe.json").read_text(encoding="utf-8"))
    return d["versiones"], d["pasos"]
