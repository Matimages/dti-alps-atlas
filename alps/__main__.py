"""CLI: python -m alps <entrada> [-o carpeta] [--bval f --bvec f]

<entrada> puede ser un NIfTI (con .bval/.bvec del mismo nombre), una carpeta DICOM o un .zip DICOM.
Por ahora corre los pasos 1-3 (entrada, eddy + movimiento, tensor DTI).
"""
import argparse

from .pipeline import _id_desde_ruta, ejecutar


def main():
    p = argparse.ArgumentParser(prog="python -m alps", description="Pasos 1-3 del pipeline DTI-ALPS con DSI Studio.")
    p.add_argument("entrada", help="NIfTI DWI, carpeta DICOM o .zip DICOM")
    p.add_argument("-o", "--salida", help="carpeta de salida (por defecto salidas/<id>)")
    p.add_argument("--bval", help=".bval (si no está junto al NIfTI con el mismo nombre)")
    p.add_argument("--bvec", help=".bvec (si no está junto al NIfTI con el mismo nombre)")
    a = p.parse_args()

    id_sujeto = _id_desde_ruta(a.entrada)
    r = ejecutar(a.entrada, a.salida or f"salidas/{id_sujeto}", a.bval, a.bvec, id_sujeto)
    for nombre, ruta in r["archivos"].items():
        print(f"  {nombre}: {ruta}")


if __name__ == "__main__":
    main()
