# Decisiones metodológicas

Cada fila: qué se decidió, de qué fuente sale y qué alternativa se descartó.
Lo que no tiene fuente directa se marca **SUPUESTO**.

Fuentes:
- **[Liu]** Liu X, Barisano G, et al. *Cross-Vendor Test-Retest Validation of DTI-ALPS for Evaluating
  Glymphatic System Function.* Aging Dis 2024;15(4):1885-98. DOI 10.14336/AD.2023.0321-2, PMC11272201.
  Pipeline FSL (sección "FSL pipeline" y Tabla 2).
- **[alps.sh]** Repositorio github.com/gbarisano/alps (MIT), script `alps.sh`, rama `main`
  (último commit revisado: 2025-09-12).
- **[Taoka]** Taoka T, et al. Jpn J Radiol 2017;35(4):172-8. Definición del índice ALPS.
- **[Marín]** Marín I, et al. Open Neuroimaging J 2025;18:e18744400389049 (`utilidad_directa/marin25.pdf`).
- **[DIPY]** Documentación y tutoriales de DIPY (versión indicada en `requirements.txt`).

## Pipeline

| Decisión | Fuente | Alternativa descartada |
|---|---|---|
| Template: `JHU-ICBM-FA-1mm.nii.gz` (FSL) | [Liu] Tabla 2; [alps.sh] `template=${FSLDIR}/data/atlases/JHU/JHU-ICBM-FA-1mm.nii.gz` | Plantilla QA de DSI Studio (usada por el intento anterior); MNI152 T1 (Liu la usa solo si hay imagen estructural) |
| Denoising MP-PCA antes del tensor (`dipy.denoise.localpca.mppca`, `patch_radius=2` = ventana 5×5×5) | [Liu] "MP-PCA denoising ... dwidenoise"; [alps.sh] `denoise=1`; ventana 5×5×5 = default de `dwidenoise` | Omitirlo (decidido con el autor el 2026-11-02: se incluye) |
| Corrección de Gibbs después del denoising (`dipy.denoise.gibbs.gibbs_removal`) | [Liu] "Gibbs-unringing ... mrdegibbs"; mismo orden que [alps.sh] | Omitirla |
| Máscara cerebral: `median_otsu` sobre los b0 | Indicación del autor | `bet` sobre b0 ([alps.sh]); no hay FSL en Windows |
| Ajuste del tensor por mínimos cuadrados lineales (`fit_method="OLS"`) | [alps.sh] `dtifit` sin `--wls` (= mínimos cuadrados lineales) | WLS (default de DIPY; decidido con el autor el 2026-11-02) |
| Dxx, Dyy, Dzz = elementos diagonales del tensor en los ejes de la imagen | [alps.sh] `fslroi dti_tensor 0/3/5` (tensor de dtifit en ejes de vóxel) | Reorientar el tensor (fuera de alcance) |
| Registro afín (12 gdl) del FA del sujeto al template | [alps.sh] `flirt -dof 12`; [Liu] "rigid and affine transformation" | Registro no lineal (`fnirt`, opcional en [alps.sh]; fuera de alcance) |
| Dxx/Dyy/Dzz al template con la matriz del FA, interpolación lineal, sin reorientar | [alps.sh] `flirt -applyxfm` sobre el tensor, sin `-interp` (default de FLIRT: trilineal) | `vecreg` (opción `-f 2` de [alps.sh]) |
| ROIs: esferas de radio 2.5 mm (5 mm de diámetro) en la grilla del template | [Liu] "spheres with 5mm diameter"; [alps.sh] `rois=2.5` | Radio 5 mm (default anterior de [alps.sh], corregido el 2025-05-28) |
| Centros de las ROIs (vóxel JHU): ver sección ROIs | [Liu], [alps.sh] | — |
| Media en cada ROI = promedio de todos sus vóxeles | [alps.sh] `fslstats -k roi -m` | Excluir vóxeles fuera de la máscara cerebral |
| ALPS_h = mean(Dxx_proy, Dxx_asoc) / mean(Dyy_proy, Dzz_asoc); ALPS = mean(ALPS_L, ALPS_R) | [Taoka]; [alps.sh] líneas `alps_L`, `alps_R`, `alps`; [Liu] "average of bilateral ALPS indexes" | Solo hemisferio izquierdo (algunos estudios previos) |

## ROIs

Vóxeles en la grilla JHU-ICBM-FA-1mm (182×218×182; x = 90 − i, y = −126 + j, z = −72 + k mm).

| ROI | Vóxel (i,j,k) | mm (x,y,z) | [Liu] | [alps.sh] y `ROIs_JHU_ALPS/` |
|---|---|---|---|---|
| L-SCR (proyección) | (116,110,99) | (−26,−16,+27) | 116 | 116 |
| R-SCR (proyección) | (64,110,99) | (+26,−16,+27) | 64 | 64 |
| L-SLF (asociación) | (128,110,99) | (−38,−16,+27) | 128 | 128 |
| R-SLF (asociación) | **(52,110,99)** | (+38,−16,+27) | **51** | **52** |

- **Conflicto R-SLF.** El paper dice 51; el generador de esferas de `alps.sh` y el archivo `R_SLF.nii.gz` del repo
  usan 52, que es simétrico con L-SLF respecto de i = 90. Decidido con el autor (2026-11-02): manda el archivo del
  repo, porque es lo que el software publicado usa por defecto. Alternativa descartada: 51 (paper).
- **Radio.** Se incluyen los vóxeles cuyo centro está a ≤ 2.5 mm del centro: 81 vóxeles por ROI, idéntico vóxel a vóxel
  a los 4 archivos de `ROIs_JHU_ALPS/` descargados el 2026-11-02 (`tests/test_rois.py`).
- **Origen de los archivos (no versionados, en `templates/`).** ROIs: `raw.githubusercontent.com/gbarisano/alps/main/ROIs_JHU_ALPS/`
  (MIT). Template: `data/atlases/JHU/JHU-ICBM-FA-1mm.nii.gz` del paquete oficial de FSL `fsl-data_atlases-2103.0`
  (canal conda `fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public`), sha256 `8edecc45…defe1882`. Tiene licencia FSL
  (uso académico no comercial), así que no se redistribuye.

## Supuestos

| Supuesto | Motivo | Alternativa |
|---|---|---|
| **SUPUESTO** Métrica de registro: información mutua (DIPY), inicialización por centro de masa → traslación → rígido → afín, parámetros del tutorial de DIPY | DIPY no implementa *correlation ratio* ni la búsqueda angular ±90° de FLIRT | `-cost corratio -searchr* -90 90` de [alps.sh] |
| **SUPUESTO** `median_otsu` con los defaults de DIPY (`median_radius=4`, `numpass=4`) | Sin fuente para estos valores; son los defaults | Ajustarlos por sujeto |
| **SUPUESTO** Gibbs con los defaults de DIPY (`slice_axis=2`, `n_points=3`) | Equivalen a los defaults de `mrdegibbs` | — |
| **SUPUESTO** La diferencia de convención de bvec entre FSL y DIPY no afecta | Dxx, Dyy y Dzz no cambian al invertir el signo de un eje | — |
| **SUPUESTO** El color-FA de la figura QC se lleva al template canal por canal, sin reorientar | Solo es para control visual; no entra en el índice | — |

## Limitaciones conocidas

- Sin corrección de movimiento ni de corrientes de Foucault (eddy), y sin TOPUP: [Liu] las hace; aquí quedan fuera de alcance.
- Sin registro no lineal y sin reorientación del tensor.
- La corrección de Gibbs supone adquisición sin Fourier parcial (advertencia de MRtrix3); no está verificado para ds001378.
