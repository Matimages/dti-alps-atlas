# DTI-ALPS con atlas estándar

Sistematiza el cálculo del índice DTI-ALPS en MRI clínica de 1.5T. Proyecto de magíster BME423 (Universidad de Valparaíso).

- Fases, herramientas y fuentes: [`docs/pipeline.md`](docs/pipeline.md).
- Cada decisión metodológica, con su fuente y la alternativa descartada: [`docs/decisiones.md`](docs/decisiones.md).

## Qué hace

1. **Entrada.** Carpeta o `.zip` con DICOM (se convierte con dcm2niix), o un NIfTI con su `.bval` y su `.bvec`. Un NIfTI
   sin `.bval`/`.bvec` se rechaza, porque el NIfTI no guarda los valores b ni las direcciones.
2. **Eddy + movimiento.** Máscara con FSL `bet2` y corrección con FSL `eddy_cpu` (todos los núcleos).
3. **FA del sujeto**, solo para guiar el registro.
4. **Registro afín** del FA al atlas FSL HCP1065 de 1 mm (espacio MNI).
5. **DWI al atlas.** Los 16 volúmenes pasan a la grilla del atlas y los bvecs se rotan igual.
6. **Tensor en el atlas** con DSI Studio: Dxx, Dyy y Dzz quedan en los ejes del atlas.
7. **Índice ALPS** en las 4 ROIs esféricas de Liu et al. 2024: `ALPS = mean(Dxx_proy, Dxx_asoc) / mean(Dyy_proy, Dzz_asoc)`
   por hemisferio, y su promedio.

Salidas por sujeto: `alps.csv`, `qc_alps.png` (ROIs sobre el color-FA del sujeto en el atlas), `qc_dti.png`, `qc_eddy.png`,
`dti.fz.{fa,md,txx,tyy,tzz}.nii.gz` y `rois_atlas.nii.gz` en el atlas, `informe.md` (qué hizo cada paso y en qué fuente se
basa), y `fsl.log` y `dsi_studio.log` con cada comando ejecutado.

## Instalación (macOS o Linux)

Una sola vez, desde la carpeta del repositorio. No usa `sudo` y deja todo dentro de `herramientas/`:

```bash
bash app/instalar.sh
```

Instala micromamba, un entorno con Python 3.12 y las librerías de `requirements.txt`, otro entorno aparte con **solo** los
paquetes de FSL que se usan (`fsl-eddy`, `fsl-bet2`, `fsl-data_standard`, `fsl-data_atlases`; licencia FSL, uso no comercial) y DSI Studio
2026.7.25 (licencia propia, uso académico). Descarga unos 700 MB. Al final verifica las herramientas y corre los tests.

En Windows: dentro de WSL2 (Ubuntu), porque FSL no tiene versión nativa para Windows.

## Uso

App: en macOS, doble clic en `app/abrir_app.command`, o desde la terminal:

```bash
bash app/abrir_app.command
```

Se abre en el navegador (http://localhost:8501). Se sube el DWI (zip DICOM, o NIfTI + bval + bvec) o se escribe su ruta.
Los resultados quedan en `resultados_app/<id>/` y se descargan desde la misma página. La opción "Sujeto ya procesado"
abre un resultado anterior sin volver a procesar.

Línea de comandos (después de `. herramientas/config.sh`):

```bash
herramientas/python/bin/python -m alps ruta/sub-01_dwi.nii.gz -o salidas/sub-01
```

Pruebas:

```bash
herramientas/python/bin/python -m pytest tests
```

## Limitaciones

- Sin TOPUP: ds001378 no tiene una adquisición con fase inversa. Fase y readout de eddy son un SUPUESTO (ver `docs/decisiones.md`).
- Eddy con sus valores por defecto: sin reemplazo de outliers y sin slice-to-volume.
- Registro solo afín. Las ROIs son las de referencia de Liu et al. 2024, no dibujadas por neurorradiólogos.

## Cita

Si se usa, citar DSI Studio (Yeh, doi:10.1038/s41592-025-02762-8), FSL eddy (Andersson & Sotiropoulos 2016,
NeuroImage 125:1063-78), Marín et al. 2025 (Open Neuroimaging J), Liu X, Barisano G, et al. (2024, Aging Dis) y
Taoka T, et al. (2017, Jpn J Radiol 35:172-8).
