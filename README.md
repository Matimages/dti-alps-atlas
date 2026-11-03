# DTI-ALPS con atlas estándar

Calcula el índice DTI-ALPS a partir de un DWI usando el pipeline con atlas de
Liu, Barisano et al. 2024 (Aging Dis 15(4):1885-98, DOI 10.14336/AD.2023.0321-2; repositorio
[gbarisano/alps](https://github.com/gbarisano/alps)), reimplementado en Python con DIPY.

Proyecto de magíster BME423 (Universidad de Valparaíso). Las decisiones metodológicas y sus fuentes
están en [`docs/decisiones.md`](docs/decisiones.md).

## Qué hace

1. **Entrada**: NIfTI + `.bval` + `.bvec`, o una carpeta / `.zip` con DICOM (se convierte con dcm2niix).
2. **Preproceso**: denoising MP-PCA y corrección de Gibbs.
3. **Tensor**: máscara `median_otsu`; ajuste por mínimos cuadrados lineales; FA, Dxx, Dyy, Dzz en los ejes de la imagen.
4. **Registro**: afín (12 gdl) del FA al template JHU-ICBM-FA 1 mm. Dxx, Dyy y Dzz se llevan al template con la misma matriz.
5. **ROIs**: esferas de 2.5 mm de radio en L/R-SCR (proyección) y L/R-SLF (asociación), a la altura del cuerpo ventricular.
6. **Índice**: `ALPS = mean(Dxx_proy, Dxx_asoc) / mean(Dyy_proy, Dzz_asoc)` por hemisferio, y su promedio.

Salidas: `alps.csv`, `rois_en_template.nii.gz` (etiquetas 1-4: L-SCR, R-SCR, L-SLF, R-SLF),
`FA_en_template.nii.gz` y `qc_alps.png` (ROIs sobre el color-FA, convención radiológica).

## Instalación

Requiere Python 3.12.

```bash
python -m venv .venv
```
```bash
.venv/Scripts/python -m pip install -r requirements.txt
```
(En Linux/macOS: `.venv/bin/python`.)

### Template (no viene en el repositorio)

`JHU-ICBM-FA-1mm.nii.gz` es parte de FSL (licencia FSL: uso académico no comercial), así que no se redistribuye.
Hay que dejarlo en `templates/JHU-ICBM-FA-1mm.nii.gz`, o indicar su ruta con `--template` o con la variable
`DTI_ALPS_TEMPLATE`. Dónde conseguirlo:

- Con FSL instalado: `$FSLDIR/data/atlases/JHU/JHU-ICBM-FA-1mm.nii.gz`.
- Sin FSL: en el paquete `fsl-data_atlases` del canal conda oficial
  (`https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public/noarch/`), archivo `data/atlases/JHU/JHU-ICBM-FA-1mm.nii.gz`.

Opcional, para que `tests/test_rois.py` compare con las ROIs originales: descargar los 4 archivos de
`ROIs_JHU_ALPS/` de gbarisano/alps (MIT) a `templates/`.

## Uso

Línea de comandos:

```bash
.venv/Scripts/python -m alps ruta/sub-01_dwi.nii.gz -o salidas/sub-01
```

Si `.bval` y `.bvec` no tienen el mismo nombre que el NIfTI, se indican con `--bval` y `--bvec`. La entrada también
puede ser una carpeta DICOM o un `.zip` DICOM.

App:

```bash
.venv/Scripts/streamlit run app/app.py
```

En la app se suben los archivos (zip DICOM, o NIfTI + bval + bvec) o se escribe una ruta local. Los resultados quedan en
`resultados_app/<id>/` y se pueden descargar desde la misma página.

Un sujeto tarda unos 8 minutos en un PC de escritorio de 6 núcleos: MP-PCA ~1 min (en paralelo), Gibbs ~0.5 min,
registro ~5.5 min.

Pruebas:

```bash
.venv/Scripts/python -m pytest tests
```

## Limitaciones

- No corrige movimiento ni corrientes de Foucault (eddy), ni aplica TOPUP; Liu et al. sí lo hacen.
- Registro solo afín (sin no lineal) y sin reorientación del tensor (igual que el default de gbarisano/alps).
- El registro usa información mutua (DIPY), no la *correlation ratio* de FLIRT.
- El índice depende de que el registro sea bueno: revisar siempre `qc_alps.png`.

Detalle y fuentes de cada parámetro: [`docs/decisiones.md`](docs/decisiones.md).

## Cita

Si se usa, citar a Liu X, Barisano G, et al. (2024) y a Taoka T, et al. (2017, Jpn J Radiol 35:172-8).
