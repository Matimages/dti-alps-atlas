"""Informe del procesamiento: qué hizo cada paso, con qué comando y parámetros, y en qué documentación se basa.

Pensado para que alguien que sabe del tema revise cada fase, en la app o en informe.md. No recalcula nada: lee lo que
dejaron las herramientas en la carpeta del sujeto (fsl.log y dsi_studio.log con cada comando, los archivos de FSL eddy
eddy.eddy_*, la matriz del registro y los NIfTI).

Cada paso es un dict: titulo, que_hizo, comandos, datos [(etiqueta, valor)], tabla [dict], notas, fuentes [(texto, url)]
y, si tiene, figura (nombre del PNG en la carpeta).
"""
import json
import os
import re
from pathlib import Path

import nibabel as nib
import numpy as np

DSI_DOC = "https://dsi-studio.labsolver.org/doc"
EDDY_DOC = "https://fsl.fmrib.ox.ac.uk/fsl/docs/diffusion/eddy"
DIPY_REG = "https://docs.dipy.org/stable/examples_built/registration/affine_registration_3d.html"
ALPS_SH = "https://github.com/gbarisano/alps"

EDDY_PARAMETROS = {  # parámetro: qué es (guía de eddy)
    "nthr": "Hilos de CPU (agregado: DSI Studio usaba 1)",
    "slm": "Modelo de segundo nivel; la guía sugiere considerar 'linear' con pocas direcciones",
    "repol": "Reemplazo de cortes outlier",
    "ol_nstd": "Umbral (desviaciones estándar) para marcar un corte como outlier",
    "mporder": "Corrección slice-to-volume (0 = desactivada)",
    "niter": "Iteraciones",
    "flm": "Modelo de los campos de eddy",
    "resamp": "Remuestreo final ('jac': única opción sin fase inversa)",
}


def _comandos(log):
    """(comando, salida) de cada llamada registrada en un log con líneas '$ comando'."""
    partes = re.split(r"^\$ ", log, flags=re.M)[1:]
    return [tuple((p + "\n").split("\n", 1)) for p in partes]


def _valor(texto, clave):
    m = re.search(rf"{re.escape(clave)}=?\s*(\S+)", texto)
    return m[1] if m else "—"


def _voxeles(img):
    """[(Grilla, ...), (Vóxel, ...)] cortos, para que quepan en una métrica de la app."""
    return [("Grilla", "×".join(map(str, img.shape[:3]))),
            ("Vóxel (mm)", "×".join(f"{z:g}" for z in img.header.get_zooms()[:3]))]


def _paso1(c, nifti, bval):
    img = nib.load(str(nifti))
    valores, cuentas = np.unique(np.round(np.loadtxt(bval, ndmin=1), -1), return_counts=True)
    return {
        "titulo": "1. Entrada",
        "que_hizo": ("Convirtió el DICOM a NIfTI + .bval + .bvec con dcm2niix. " if (c / "nifti").is_dir() else "")
        + "Verificó que hubiera un .bval y un .bvec (el NIfTI no guarda los valores b ni las direcciones), con un valor "
          "y una dirección por volumen y al menos un b0.",
        "comandos": [], "tabla": [],
        "datos": [("Volúmenes", str(img.shape[3])), *_voxeles(img),
                  ("Valores b (s/mm²)", " · ".join(f"{v:g} ×{n}" for v, n in zip(valores, cuentas)))],
        "notas": [f"Entrada: `{Path(nifti).name}` con `{Path(bval).name}` y su .bvec."],
        "fuentes": [("dcm2niix (DICOM → NIfTI + bval/bvec)", "https://github.com/rordenlab/dcm2niix"),
                    ("Convención de bval/bvec de FSL", f"{EDDY_DOC}/users_guide/index.html")],
    }


def _paso2(c, fsl):
    valores = (c / "eddy.eddy_values_of_all_input_parameters").read_text()
    rms = np.loadtxt(c / "eddy.eddy_movement_rms")
    outliers = (c / "eddy.eddy_outlier_report").read_text().strip().splitlines()
    acqp = (c / "acqparams.txt").read_text().split()
    notas = [f"`--acqp {' '.join(acqp)}`: fase en el eje y (antero-posterior), readout de {acqp[3]} s, como alps.sh para "
             "Philips sin JSON. **SUPUESTO**: ds001378 no trae el JSON con la fase. Sin TOPUP, el readout no cambia el "
             "resultado (FAQ de eddy).",
             "Sin TOPUP: no hay una adquisición con codificación de fase inversa."]
    if outliers:  # "Slice 7 in scan 3 is an outlier with mean -21.6 standard deviations off, ..."
        partes = [re.search(r"Slice (\d+) in scan (\d+) .*?mean (\S+) standard", o) for o in outliers]
        notas.append("Cortes outlier detectados, que no se reemplazan porque `--repol=False` (numeración de eddy, desde 0): "
                     + "; ".join(f"corte {p[1]} del volumen {p[2]} ({float(p[3]):.1f} DE)" for p in partes if p) + ".")
    return {
        "titulo": "2. Eddy y movimiento",
        "figura": "qc_eddy.png",
        "que_hizo": "Hizo una máscara cerebral sobre el b0 con bet2. Luego FSL eddy estimó, para cada volumen, el movimiento "
                    "rígido de la cabeza y la distorsión por corrientes de Foucault, remuestreó el DWI corregido "
                    "(`eddy.nii.gz`) y rotó los bvecs según el movimiento (`eddy.eddy_rotated_bvecs`). Se usan los mismos "
                    "parámetros que usaba DSI Studio; solo se agregan hilos.",
        "comandos": [cmd for cmd, _ in fsl],
        "datos": [("Mov. absoluto medio", f"{rms[1:, 0].mean():.2f} mm"), ("Mov. absoluto máx.", f"{rms[:, 0].max():.2f} mm"),
                  ("Mov. relativo medio", f"{rms[1:, 1].mean():.2f} mm"), ("Mov. relativo máx.", f"{rms[:, 1].max():.2f} mm"),
                  ("Cortes outlier", str(len(outliers)))],
        "tabla": [{"Parámetro": f"--{p}", "Valor": _valor(valores, "--" + p), "Qué es": d}
                  for p, d in EDDY_PARAMETROS.items()],
        "notas": notas,
        "fuentes": [("FSL eddy: guía de uso", f"{EDDY_DOC}/users_guide/index.html"),
                    ("FSL eddy: FAQ (`--acqp`, readout, rotación de bvecs)", f"{EDDY_DOC}/FAQ/index.html"),
                    ("Andersson & Sotiropoulos 2016, NeuroImage 125:1063-78", "https://doi.org/10.1016/j.neuroimage.2015.10.019"),
                    ("gbarisano/alps (alps.sh): `bet2 -m` y `--acqp` para Philips", ALPS_SH),
                    ("Marín et al. 2025: corrección de eddy y movimiento antes del DTI", None)],
    }


def _paso3(c):
    return {
        "titulo": "3. FA del sujeto",
        "que_hizo": "Ajustó un tensor rápido en el espacio del sujeto (DIPY, mínimos cuadrados) dentro de la máscara de "
                    "bet2, solo para obtener el FA que guía el registro. Este tensor no se usa para el ALPS.",
        "comandos": [], "tabla": [], "notas": [],
        "datos": _voxeles(nib.load(str(c / "fa_sujeto.nii.gz"))),
        "fuentes": [("DIPY TensorModel", "https://docs.dipy.org/stable/examples_built/reconstruction/reconst_dti.html"),
                    ("alps.sh: el FA de dtifit (sin --wls) es la imagen que se registra", ALPS_SH)],
    }


def _paso4(c, template):
    matriz = np.loadtxt(c / "registro_afin.txt")
    fa_atlas = nib.load(str(c / "fa_sujeto_en_atlas.nii.gz")).get_fdata()
    dentro = template > 0.1
    r = np.corrcoef(fa_atlas[dentro], template[dentro])[0, 1]
    u, _, vt = np.linalg.svd(matriz[:3, :3])
    angulo = np.degrees(np.arccos(np.clip((np.trace(u @ vt) - 1) / 2, -1, 1)))
    return {
        "titulo": "4. Registro al atlas",
        "que_hizo": "Registró el FA del sujeto al FA del atlas FSL HCP1065 (1 mm, MNI) con una transformación afín de 12 "
                    "grados de libertad, maximizando la información mutua (centro de masa → traslación → rígido → afín).",
        "comandos": [],
        "datos": [("Correlación FA sujeto vs atlas", f"{r:.2f}"), ("Rotación de la cabeza", f"{angulo:.1f}°"),
                  ("Escalas (afín)", " · ".join(f"{s:.2f}" for s in np.linalg.svd(matriz[:3, :3])[1]))],
        "tabla": [{"Parámetro": p, "Valor": v, "Qué es": d} for p, v, d in (
            ("pipeline", "center_of_mass, translation, rigid, affine", "Etapas, de lo simple a lo completo"),
            ("métrica", "información mutua, 32 bins", "Qué se maximiza (DIPY no tiene correlation ratio)"),
            ("level_iters", "10000, 1000, 100", "Iteraciones por nivel de resolución"),
            ("sigmas / factors", "3, 1, 0 / 4, 2, 1", "Suavizado y submuestreo por nivel"))],
        "notas": ["**SUPUESTO**: parámetros del tutorial de DIPY. alps.sh usa `flirt -dof 12 -cost corratio`.",
                  "La matriz queda en `registro_afin.txt` y el FA del sujeto en el atlas en `fa_sujeto_en_atlas.nii.gz`."],
        "fuentes": [("DIPY: registro afín 3D", DIPY_REG), ("alps.sh: `flirt -dof 12` al template", ALPS_SH),
                    ("Liu et al. 2024: registro rígido y afín al template", None),
                    ("Atlas: FSL HCP1065 (FSL, data/standard)", "https://fsl.fmrib.ox.ac.uk/fsl/docs/")],
    }


def _paso5(c):
    return {
        "titulo": "5. DWI al atlas",
        "que_hizo": "Llevó cada uno de los volúmenes del DWI corregido a la grilla de 1 mm del atlas con la matriz del "
                    "registro (interpolación lineal). Rotó los bvecs con la parte rotacional de esa matriz, para que las "
                    "direcciones del gradiente sigan correspondiendo al cerebro ya registrado.",
        "comandos": [], "tabla": [],
        "datos": _voxeles(nib.load(str(c / "fa_sujeto_en_atlas.nii.gz"))),
        "notas": ["Por eso el tensor del paso 6 queda en los ejes del atlas: Dxx es izquierda-derecha del atlas, no de la "
                  "cabeza del sujeto."],
        "fuentes": [("Leemans & Jones 2009: la matriz b debe rotarse al rotar la imagen", "https://doi.org/10.1002/mrm.21890"),
                    ("Alexander et al. 2001: rotación por descomposición polar (finite strain)", "https://doi.org/10.1109/42.963816"),
                    ("Convención de bvecs de FSL (MRtrix3)", "https://mrtrix.readthedocs.io/en/latest/concepts/dw_scheme.html")],
    }


def _paso6(c, dsi):
    rec = [(cmd, out) for cmd, out in dsi if "--method=1" in cmd]
    salida = rec[-1][1] if rec else ""
    return {
        "titulo": "6. Tensor en el atlas",
        "figura": "qc_dti.png",
        "que_hizo": "DSI Studio ajustó el tensor de difusión vóxel a vóxel sobre el DWI ya llevado al atlas y exportó FA, MD "
                    "y los elementos diagonales del tensor (txx, tyy, tzz = Dxx, Dyy, Dzz) en los ejes del atlas.",
        "comandos": [cmd for cmd, _ in dsi],
        "datos": [("Método", "DTI (method = 1)"), *_voxeles(nib.load(str(c / "dti.fz.fa.nii.gz"))),
                  ("Vóxeles en la máscara", _valor(salida, "mask voxels:"))],
        "tabla": [{"Parámetro": p, "Valor": _valor(salida, p), "Qué es": d} for p, d in (
            ("other_output", "Mapas adicionales pedidos ('tensor' = txx … tzz)"),
            ("make_isotropic", "Remuestreo (0 = no; los mapas quedan en la grilla del atlas)"),
            ("check_btable", "Revisión automática de la orientación de la b-table"))],
        "notas": ["Unidades: txx, tyy, tzz en mm²/s; MD en 10⁻³ mm²/s. DSI Studio exporta el FA cuantizado en pasos de "
                  "1/255. El color-FA de la figura (|V1|·FA; Pajevic & Pierpaoli 1999) es solo para mirar."],
        "fuentes": [("DSI Studio `--action=rec --method=1` y `--other_output`", f"{DSI_DOC}/cli_t2.html"),
                    ("DSI Studio `--action=exp`", f"{DSI_DOC}/cli_exp.html"),
                    ("Marín et al. 2025 y tesis previa: DTI en DSI Studio pidiendo \"tensor\"", None)],
    }


def _paso7(fila):
    return {
        "titulo": "7. Índice ALPS",
        "figura": "qc_alps.png",
        "que_hizo": "Promedió Dxx, Dyy y Dzz en 4 esferas de 2.5 mm de radio (81 vóxeles cada una) en la corona radiada "
                    "(proyección, SCR) y el fascículo longitudinal superior (asociación, SLF) de cada hemisferio, y calculó "
                    "ALPS = mean(Dxx_proy, Dxx_asoc) / mean(Dyy_proy, Dzz_asoc) en cada lado y su promedio.",
        "comandos": [],
        "datos": [("ALPS izquierdo", f"{fila['alps_L']:.3f}"), ("ALPS derecho", f"{fila['alps_R']:.3f}"),
                  ("ALPS promedio", f"{fila['alps']:.3f}")],
        "tabla": [{"Parámetro": h, "Valor": " · ".join(f"{fila[k + h[-1]] * 1e3:.3f}" for k in
                   ("x_proj_", "x_assoc_", "y_proj_", "z_assoc_")),
                   "Qué es": "Dxx proy · Dxx asoc · Dyy proy · Dzz asoc (10⁻³ mm²/s)"}
                  for h in ("Hemisferio L", "Hemisferio R")],
        "notas": ["ROIs de referencia: las esferas de Liu et al. 2024, en la misma grilla MNI del atlas (R-SLF en i = 52, "
                  "como el archivo de gbarisano/alps). Se usan como referencia mientras no sea posible contar con ROIs "
                  "dibujadas por neurorradiólogos sobre el atlas."],
        "fuentes": [("Taoka et al. 2017: definición del índice ALPS", "https://doi.org/10.1007/s11604-017-0617-z"),
                    ("Liu et al. 2024: ROIs esféricas de 5 mm de diámetro y promedio de ambos lados",
                     "https://doi.org/10.14336/AD.2023.0321-2"),
                    ("gbarisano/alps: archivos de ROIs y fórmula", ALPS_SH)],
    }


def versiones(dsi_log):
    dsi = re.search(r"^DSI Studio \(.*?\),?\s*(.*)$", dsi_log, flags=re.M)  # "DSI Studio (doi:...), Sun ... Oct 30 2026"
    fsldir = Path(os.environ.get("FSLDIR", ""))
    if (fsldir / "etc" / "fslversion").exists():  # FSL completo
        fsl = (fsldir / "etc" / "fslversion").read_text().split(":")[0].strip()
    else:  # solo los paquetes de app/instalar.sh: se informa la versión del paquete de eddy
        meta = sorted((fsldir / "conda-meta").glob("fsl-eddy-[0-9]*.json"))
        fsl = "fsl-eddy " + json.loads(meta[-1].read_text())["version"] if meta else "?"
    return {"DSI Studio": dsi[1].strip() if dsi else "?", "FSL": fsl}


def a_markdown(nombre, version, lista):
    lineas = [f"# Informe del procesamiento: {nombre}", "",
              "Versiones: " + "; ".join(f"{k} {v}" for k, v in version.items()), ""]
    for p in lista:
        lineas += [f"## {p['titulo']}", "", p["que_hizo"], ""]
        lineas += [f"![{p['titulo']}]({p['figura']})", ""] if p.get("figura") else []
        lineas += ["```", *p["comandos"], "```", ""] if p["comandos"] else []
        lineas += [f"- **{k}:** {v}" for k, v in p["datos"]] + [""]
        if p["tabla"]:
            lineas += ["| Parámetro | Valor | Qué es |", "|---|---|---|"]
            lineas += [f"| `{f['Parámetro']}` | {f['Valor']} | {f['Qué es']} |" for f in p["tabla"]] + [""]
        lineas += [f"> {n}" for n in p["notas"]] + ["", "**Fuentes:**"]
        lineas += [f"- {t}" + (f": {u}" if u else "") for t, u in p["fuentes"]] + [""]
    return "\n".join(lineas)


def generar(carpeta, nifti, bval, template, fila):
    """Escribe <carpeta>/informe.md (para leer) e informe.json (para la app) y devuelve (ruta .md, versiones, pasos)."""
    c = Path(carpeta)
    dsi_log = (c / "dsi_studio.log").read_text(encoding="utf-8")
    fsl = _comandos((c / "fsl.log").read_text(encoding="utf-8"))
    version = versiones(dsi_log)
    lista = [_paso1(c, nifti, bval), _paso2(c, fsl), _paso3(c), _paso4(c, template), _paso5(c),
             _paso6(c, _comandos(dsi_log)), _paso7(fila)]
    ruta = c / "informe.md"
    ruta.write_text(a_markdown(c.name, version, lista), encoding="utf-8")
    (c / "informe.json").write_text(json.dumps({"versiones": version, "pasos": lista, "fila": fila},
                                               ensure_ascii=False, indent=1), encoding="utf-8")
    return ruta, version, lista


def leer(carpeta):
    """Lee informe.json de un sujeto ya procesado: (versiones, pasos, fila con el ALPS o None)."""
    d = json.loads((Path(carpeta) / "informe.json").read_text(encoding="utf-8"))
    return d["versiones"], d["pasos"], d.get("fila")
