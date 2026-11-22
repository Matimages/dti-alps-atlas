"""Paso 2: corrección de corrientes de Foucault (eddy) y de movimiento con FSL eddy, llamado directamente.

Reemplaza al denoising MP-PCA y a la corrección de Gibbs. Lo pidió la prof. Chabert en la reunión del 2026-11-03:
a 1.5T la relación señal-ruido es más baja que a 3T, donde se validó Liu et al. 2024, y el denoising podría eliminar
información. Marín et al. 2025 hicieron esta corrección con DSI Studio + EDDY.

Desde el 2026-11-22 eddy se llama directamente y no a través de DSI Studio. DSI Studio lo corría con un solo hilo
(~45 min por sujeto) y no permitía cambiar nada. Se usan los mismos parámetros que usaba DSI Studio (verificado en
`.eddy_values_of_all_input_parameters`) y solo se agrega `--nthr` con todos los núcleos: mismo algoritmo, más rápido.
- Máscara: `bet2 b0 b0_brain -m` sobre el primer b0, como gbarisano/alps (alps.sh) antes de eddy.
- `--acqp`: sin un JSON que diga la fase, alps.sh usa para Philips el eje de fase y un readout de 0.1 s.
  SUPUESTO: fase en el eje y (antero-posterior), "0 1 0 0.1". Sin TOPUP el valor del readout no cambia el resultado
  (FAQ de eddy). `--index`: un 1 por volumen.
- `eddy_cpu --data_is_shelled --nthr=<núcleos>`; el resto en los defaults de eddy (--repol=False, --slm=none,
  --mporder=0). Guía: https://fsl.fmrib.ox.ac.uk/fsl/docs/diffusion/eddy/users_guide/index.html.
  Andersson & Sotiropoulos 2016, NeuroImage 125:1063-78.
- Salidas: eddy.nii.gz (DWI corregido) y eddy.eddy_rotated_bvecs (bvecs rotados por el movimiento estimado; FAQ de eddy).
- Figura QC (qc_eddy.png): DWI original y corregido, y su diferencia, en el corte outlier más extremo del reporte de eddy
  (`.eddy_outlier_report`) o, si no hay outliers, en el volumen con más movimiento (`.eddy_movement_rms`).
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np

ACQP = "0 1 0 0.1"


def _fsl(programa):
    for candidato in (Path(os.environ.get("FSLDIR", "")) / "bin" / programa, shutil.which(programa)):
        if candidato and Path(candidato).exists():
            return str(candidato)
    raise FileNotFoundError(f"No se encontró {programa} de FSL: instálalo (ver README) y deja definida FSLDIR.")


def correr_fsl(comando, carpeta):
    """Corre un programa de FSL en `carpeta`, deja el comando y su salida en fsl.log y falla si termina con error."""
    entorno = {**os.environ, "FSLOUTPUTTYPE": "NIFTI_GZ"}
    r = subprocess.run(comando, cwd=carpeta, env=entorno, capture_output=True, text=True, errors="replace")
    with open(Path(carpeta) / "fsl.log", "a", encoding="utf-8") as f:
        f.write("$ " + " ".join(map(str, comando)) + "\n" + r.stdout + r.stderr + "\n")
    if r.returncode != 0:
        raise RuntimeError(f"{Path(comando[0]).name} falló (código {r.returncode}): {(r.stdout + r.stderr)[-500:]}")


def corregir(nifti, bval, bvec, carpeta):
    """Máscara con bet2 y eddy. Devuelve (DWI corregido, bvecs rotados, máscara)."""
    c = Path(carpeta)
    img = nib.load(str(nifti))
    b0 = int(np.argmin(np.loadtxt(bval, ndmin=1)))  # primer volumen con el b más bajo (el b0)
    nib.save(nib.Nifti1Image(np.asarray(img.dataobj[..., b0], dtype=np.float32), img.affine), str(c / "b0.nii.gz"))
    correr_fsl([_fsl("bet2"), "b0", "b0_brain", "-m"], c)
    (c / "acqparams.txt").write_text(ACQP + "\n")
    (c / "index.txt").write_text(" ".join(["1"] * img.shape[3]) + "\n")
    correr_fsl([_fsl("eddy_cpu"), f"--imain={Path(nifti).resolve()}", "--mask=b0_brain_mask", "--acqp=acqparams.txt",
                "--index=index.txt", f"--bvecs={Path(bvec).resolve()}", f"--bvals={Path(bval).resolve()}",
                "--out=eddy", "--data_is_shelled", f"--nthr={os.cpu_count() or 1}"], c)
    return c / "eddy.nii.gz", c / "eddy.eddy_rotated_bvecs", c / "b0_brain_mask.nii.gz"


def figura_eddy(carpeta, ruta, original):
    """DWI original y corregido por eddy, y su diferencia, en un mismo volumen y corte. Devuelve la ruta."""
    c = Path(carpeta)
    antes = nib.as_closest_canonical(nib.load(str(original)))  # RAS
    corregido = nib.load(str(c / "eddy.nii.gz"))
    despues = nib.as_closest_canonical(corregido)
    reporte = (c / "eddy.eddy_outlier_report").read_text()
    outliers = [(abs(float(m[3])), int(m[1]), int(m[2]), float(m[3]))
                for m in re.finditer(r"Slice (\d+) in scan (\d+) .*?mean (\S+) standard", reporte)]
    if outliers:
        _, k, v, de = max(outliers)
        motivo = f"Corte outlier más extremo según eddy ({de:.1f} DE; no se reemplaza)"
    else:
        v = int(np.loadtxt(c / "eddy.eddy_movement_rms")[:, 0].argmax())
        k = antes.shape[2] // 2
        motivo = "Volumen con más movimiento, corte central"
    k_ras = antes.shape[2] - 1 - k if nib.aff2axcodes(corregido.affine)[2] == "I" else k  # índice de eddy → RAS
    a = np.asarray(antes.dataobj[:, :, k_ras, v], dtype=float)
    d = np.asarray(despues.dataobj[:, :, k_ras, v], dtype=float)
    tope = np.percentile(a[a > 0], 99) if np.any(a > 0) else 1
    paneles = [("Original (antes de eddy)", a, tope), ("Corregido por eddy", d, tope),
               ("|Corregido − Original|", np.abs(d - a), tope / 2)]
    fig, ejes = plt.subplots(1, 3, figsize=(12, 4.6), facecolor="black")
    for ax, (rotulo, imagen, maximo) in zip(ejes, paneles):
        # RAS con i invertido: la derecha del paciente queda a la izquierda (radiológica); anterior arriba
        ax.imshow(imagen[::-1].T, origin="lower", cmap="gray", vmin=0, vmax=maximo)
        ax.set_title(rotulo, color="white", fontsize=11)
        ax.set_axis_off()
        ax.text(0.02, 0.5, "R", color="w", transform=ax.transAxes, va="center")
        ax.text(0.94, 0.5, "L", color="w", transform=ax.transAxes, va="center")
    fig.suptitle(f"Volumen {v}, corte {k} (numeración de eddy, desde 0). Convención radiológica.\n{motivo}",
                 color="white", fontsize=11)
    fig.tight_layout()
    fig.savefig(ruta, dpi=100, facecolor="black")
    plt.close(fig)
    return ruta
