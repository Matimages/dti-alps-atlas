# DTI-ALPS con atlas estándar

Sistematiza el cálculo del índice DTI-ALPS en MRI clínica de 1.5T. Proyecto de magíster BME423 (Universidad de Valparaíso).

Estado (2026-11-04): están implementados los pasos 1-3 del pipeline acordado con la prof. Stéren Chabert:
entrada → corrección de eddy y movimiento → tensor DTI. El atlas con ROIs dibujadas por los neurorradiólogos, el registro y
el índice ALPS (pasos 4-6) vienen después.

- Fases, herramientas y fuentes: [`docs/pipeline.md`](docs/pipeline.md).
- Cada decisión metodológica, con su fuente y la alternativa descartada: [`docs/decisiones.md`](docs/decisiones.md).

## Qué hace

1. **Entrada.** Recibe una carpeta o `.zip` con DICOM (se convierte con dcm2niix), o un NIfTI con su `.bval` y su `.bvec`.
   Un NIfTI sin `.bval`/`.bvec` se rechaza, porque el NIfTI no guarda los valores b ni las direcciones. Con eso crea el
   archivo fuente de DSI Studio (`dwi.sz`).
2. **Eddy + movimiento.** DSI Studio llama a FSL eddy y recarga el DWI corregido con los bvecs rotados (`dwi_eddy.sz`).
3. **Tensor DTI.** DSI Studio reconstruye el DTI y exporta FA, MD, Dxx, Dyy y Dzz a NIfTI.

Salidas por sujeto: `dti.fz.{fa,md,txx,tyy,tzz}.nii.gz`, `qc_dti.png` (cortes de FA y de Dxx/Dyy/Dzz en convención
radiológica), los `.sz` intermedios, los archivos de eddy (`dwi.sz.corrected.eddy_*`, entre ellos el reporte de outliers y el
movimiento) y `dsi_studio.log`, con cada comando ejecutado y su salida.

## Requisitos

Linux o macOS. En Windows funciona dentro de WSL2 (Ubuntu), porque FSL no tiene versión nativa para Windows.

1. **Python 3.12 o superior** y las dependencias:
   ```bash
   python3 -m venv ~/venvs/alps
   ```
   ```bash
   ~/venvs/alps/bin/pip install -r requirements.txt
   ```
2. **DSI Studio** (probado con la release 2026.7.25): https://dsi-studio.labsolver.org/download.html (licencia propia de
   DSI Studio, uso académico). Indica el ejecutable en la variable `DTI_ALPS_DSI_STUDIO`, o déjalo en el `PATH` como
   `dsi_studio`. En macOS también se busca en `/Applications/dsi_studio.app/Contents/MacOS/dsi_studio`.
3. **FSL** (probado con 6.0.7.23; trae `eddy`): https://fsl.fmrib.ox.ac.uk/fsl/docs/install/ (licencia FSL, uso
   no comercial). El instalador deja definida la variable `FSLDIR`.

## Uso

```bash
~/venvs/alps/bin/python -m alps ruta/sub-01_dwi.nii.gz -o salidas/sub-01
```

Si el `.bval` y el `.bvec` no tienen el mismo nombre que el NIfTI, se indican con `--bval` y `--bvec`. La entrada también
puede ser una carpeta DICOM o un `.zip` DICOM.

App:

```bash
~/venvs/alps/bin/streamlit run app/app.py
```

Un sujeto de ds001378 tarda unos 45 minutos, casi todo en eddy, que DSI Studio corre con un solo hilo.

Pruebas:

```bash
~/venvs/alps/bin/python -m pytest tests
```

## Limitaciones

- Sin TOPUP: ds001378 no tiene una adquisición con codificación de fase inversa. Se asume fase AP (ver `docs/decisiones.md`).
- DSI Studio llama a eddy con sus valores por defecto: sin reemplazo de outliers y sin slice-to-volume.

## Cita

Si se usa, citar DSI Studio (Yeh, doi:10.1038/s41592-025-02762-8), FSL eddy (Andersson & Sotiropoulos 2016,
NeuroImage 125:1063-78), Marín et al. 2025 (Open Neuroimaging J), Liu X, Barisano G, et al. (2024, Aging Dis) y
Taoka T, et al. (2017, Jpn J Radiol 35:172-8).
