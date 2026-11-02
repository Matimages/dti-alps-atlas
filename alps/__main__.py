"""CLI: python -m alps <entrada> [-o carpeta] [--bval f --bvec f] [--template f]

<entrada> puede ser un NIfTI (con .bval/.bvec del mismo nombre), una carpeta DICOM o un .zip DICOM.
"""
import argparse
import sys

# DIPY escribe mensajes con caracteres Unicode; la consola de Windows (cp1252) no los puede mostrar.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from .pipeline import _id_desde_ruta, ejecutar  # noqa: E402


def main():
    p = argparse.ArgumentParser(prog="python -m alps", description="Índice DTI-ALPS con atlas (Liu et al. 2024).")
    p.add_argument("entrada", help="NIfTI DWI, carpeta DICOM o .zip DICOM")
    p.add_argument("-o", "--salida", help="carpeta de salida (por defecto salidas/<id>)")
    p.add_argument("--bval", help=".bval (si no está junto al NIfTI con el mismo nombre)")
    p.add_argument("--bvec", help=".bvec (si no está junto al NIfTI con el mismo nombre)")
    p.add_argument("--template", help="JHU-ICBM-FA-1mm.nii.gz (por defecto DTI_ALPS_TEMPLATE o templates/)")
    a = p.parse_args()

    id_sujeto = _id_desde_ruta(a.entrada)
    r = ejecutar(a.entrada, a.salida or f"salidas/{id_sujeto}", a.bval, a.bvec, a.template, id_sujeto)
    f = r["fila"]
    print(f"\n{f['id']}: ALPS L = {f['alps_L']:.3f}  R = {f['alps_R']:.3f}  media = {f['alps']:.3f}")
    for nombre, ruta in r["archivos"].items():
        print(f"  {nombre}: {ruta}")


if __name__ == "__main__":
    main()
