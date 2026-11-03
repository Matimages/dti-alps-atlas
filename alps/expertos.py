"""ALPS obtenido por cada neurorradiólogo con sus ROIs manuales (solo para comparar en modo experimental).

Fuente: Marín et al. 2025. Cuatro neurorradiólogos (BO, FT, PC, RR) dibujaron ROIs de 48 mm³ en DSI Studio
sobre los 16 controles de ds001378, sesión 1, y exportaron una tabla por sujeto (`<experto>/NN.txt`,
NN = número de sub-controlNN). El material no es público: ruta en DTI_ALPS_EXPERTOS o, por defecto,
`utilidad_directa/Archive 4/ROI_MD`.

- Índice: ALPS_h = mean(txx_proy, txx_asoc) / mean(tyy_proy, tzz_asoc), con las filas txx, tyy y tzz
  de la tabla. Es la misma fórmula y las mismas filas que `read_alps.m`.
- ROIs: p_i, a_i (izquierda) y p_d, a_d (derecha), identificadas por su NOMBRE, sin distinguir mayúsculas
  ni '-'/'_'. No se usa la posición: el orden de las columnas cambia entre archivos.
- Si un hemisferio no tiene sus dos ROIs con esos nombres, queda sin valor; no se adivina qué ROI es.
  Por ejemplo, en PC el A-D suele llamarse "New Region".
- Se ignoran las ROIs "SC": la profesora indicó que las dibujó ella y no son referencia (correo).
"""
import os
import re
from pathlib import Path

EXPERTOS = ("BO", "FT", "PC", "RR")
CARPETA_DEFECTO = Path(__file__).resolve().parents[1] / "utilidad_directa" / "Archive 4" / "ROI_MD"


def _leer_tabla(ruta):
    """Devuelve {roi_normalizada: {fila: valor}} (si un nombre se repite, la ROI se descarta)."""
    lineas = [ln.rstrip("\r\n").split("\t") for ln in open(ruta, encoding="utf-8", errors="replace")]
    nombres = [n.strip().lower().replace("-", "_") for n in lineas[0][1:] if n.strip()]
    repetidos = {n for n in nombres if nombres.count(n) > 1}
    filas = {ln[0].strip(): ln[1:] for ln in lineas[1:]}
    return {n: {f: float(filas[f][c]) for f in ("txx", "tyy", "tzz")}
            for c, n in enumerate(nombres) if n not in repetidos}


def alps_expertos(id_sujeto, carpeta=None):
    """{experto: {alps_L, alps_R, alps}} para sub-controlNN_ses-01 (None donde falta); {} si no aplica."""
    m = re.fullmatch(r"sub-control(\d+)_ses-01", id_sujeto)
    carpeta = Path(carpeta or os.environ.get("DTI_ALPS_EXPERTOS") or CARPETA_DEFECTO)
    if not m or not carpeta.is_dir():
        return {}
    resultado = {}
    for experto in EXPERTOS:
        ruta = carpeta / experto / f"{int(m.group(1)):02d}.txt"
        if not ruta.exists():
            continue
        rois = _leer_tabla(ruta)
        r = {}
        for h, lado in (("L", "i"), ("R", "d")):
            p, a = rois.get(f"p_{lado}"), rois.get(f"a_{lado}")
            r[f"alps_{h}"] = ((p["txx"] + a["txx"]) / 2) / ((p["tyy"] + a["tzz"]) / 2) if p and a else None
        ambos = r["alps_L"] is not None and r["alps_R"] is not None
        r["alps"] = (r["alps_L"] + r["alps_R"]) / 2 if ambos else None
        resultado[experto] = r
    return resultado
