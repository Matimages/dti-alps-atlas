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
- **[Reunión]** Reunión del autor con la prof. Stéren Chabert, 2026-11-03.
- **[DSI]** DSI Studio (F.-C. Yeh), release 2026.7.25 "Sun" (build 2026-10-30), documentación de línea de comandos
  (https://dsi-studio.labsolver.org/doc/cli_t1.html, cli_t2.html, cli_exp.html) y código fuente
  (github.com/frankyeh/DSI-Studio, `libs/dsi/image_model.cpp`).
- **[eddy]** FSL eddy (Andersson & Sotiropoulos, NeuroImage 2016), FSL 6.0.7.23. Guía de uso y FAQ en
  https://fsl.fmrib.ox.ac.uk/fsl/docs/diffusion/eddy/.
- **[Reunión 2]** Reunión del autor con la prof. Chabert, 2026-11-17.

## Pipeline completo (2026-11-22)

Reemplaza a las secciones siguientes donde se contradigan. Pasos: 1 entrada → 2 eddy → 3 FA del sujeto → 4 registro al
atlas → 5 DWI al atlas → 6 tensor en el atlas → 7 ALPS. Diagrama: [`pipeline.md`](pipeline.md).

| Decisión | Fuente | Alternativa descartada |
|---|---|---|
| Atlas: FSL HCP1065 1 mm (FA para registrar; misma grilla MNI que JHU) | [Reunión 2]: a la profesora le gustó la figura en color-FA con las ROIs de Liu | JHU-ICBM-FA (template de [Liu]; solo FA) |
| ROIs: las esferas de [Liu] (r = 2.5 mm, R-SLF en i = 52) como ROIs de referencia | [Reunión 2]: probablemente no habrá reunión con los neurorradiólogos | ROIs dibujadas por los neurorradiólogos sobre el atlas (pendiente si se logra) |
| Orden: registrar el DWI y después calcular el tensor (Dxx, Dyy, Dzz en los ejes del atlas) | [Reunión 2] (decisión de la profesora; el autor confirmó la interpretación el 2026-11-22) | Tensor en el sujeto y mapas llevados al template sin reorientar ([alps.sh]) |
| Eddy llamado directamente (`eddy_cpu`), con los mismos parámetros que usaba DSI Studio más `--nthr` = núcleos | [eddy] guía (`--nthr`); DSI Studio lo corría con 1 hilo (~45 min). La profesora reporta ~15 min en su equipo | Seguir vía DSI Studio (no permite cambiar parámetros) |
| Máscara para eddy: `bet2 b0 b0_brain -m` sobre el primer b0 | [alps.sh] | U-Net de DSI Studio |
| **SUPUESTO** `--acqp 0 1 0 0.1`: fase en y, readout 0.1 s | [alps.sh] para Philips usa el eje de fase y 0.1 s; ds001378 no trae JSON. Sin TOPUP, el readout no cambia el resultado ([eddy] FAQ) | `0 -1 0 0.05` (lo que fijaba DSI Studio) |
| FA del sujeto para el registro: DIPY `TensorModel` OLS dentro de la máscara de bet2 | [alps.sh] registra el FA de dtifit (OLS) | — |
| Registro afín 12 gdl con DIPY (información mutua) al FA del HCP1065 | [Liu]; [alps.sh] `flirt -dof 12`; **SUPUESTO**: parámetros del tutorial de [DIPY] | Registro no lineal |
| Bvecs rotados con la parte rotacional (descomposición polar) de la matriz afín | Leemans & Jones 2009 (Magn Reson Med 61:1336-49); Alexander et al. 2001 (IEEE TMI 20:1131-9); convención FSL según la documentación de MRtrix3. Verificado con `tests/test_registro.py` | No rotar los bvecs |
| Tensor en el atlas con DSI Studio, `--make_isotropic=0` (los mapas quedan en la grilla de 1 mm de las ROIs) | [DSI] cli_t2; [Marín] | DIPY |
| Instalación mínima: micromamba + paquetes `fsl-eddy`, `fsl-bet2`, `fsl-data_standard`, `fsl-data_atlases` del canal conda de FSL + DSI Studio (`app/instalar.sh`). Python y sus librerías van en un entorno aparte del de FSL: mezclados, en macOS se cargaban dos copias de OpenMP (`OMP: Error #15`, Mac Apple Silicon, 2026-11-22) | [Reunión 2]: que corra en el Mac de la profesora con la menor cantidad de módulos | FSL completo (varios GB) |

## Pasos 1-3 (reestructuración del 2026-11-03)

Pipeline acordado en [Reunión]: 1 entrada → 2 eddy + movimiento → 3 tensor → 4 atlas con ROIs dibujadas por los
neurorradiólogos → 5 registro por información mutua → 6 ALPS. Por ahora se implementan solo los pasos 1-3. El diagrama con
las herramientas y fuentes de cada paso está en [`pipeline.md`](pipeline.md).

| Decisión | Fuente | Alternativa descartada |
|---|---|---|
| Herramienta de los pasos 1-3: DSI Studio por línea de comandos, con FSL eddy | [Reunión] (no reinventar la rueda; usar DSI Studio); [Marín] hizo todo el procesamiento DTI con DSI Studio + EDDY. Decidido con el autor (2026-11-03) | Python + FSL eddy + DIPY (como [Liu]); solo DIPY (`motion_correction` no corrige eddy) |
| Desarrollo en WSL2 Ubuntu, pensando en macOS | FSL corre en Linux y macOS, y en Windows solo vía WSL (https://fsl.fmrib.ox.ac.uk/fsl/docs/install/windows.html); los neurorradiólogos usan macOS [Reunión] | VM de macOS (la licencia de software de macOS solo permite virtualizarlo en hardware Apple; falta citar el texto exacto, https://www.apple.com/legal/sla/); Windows nativo (sin eddy) |
| DICOM → NIfTI + .bval + .bvec con dcm2niix | Conversión estándar (https://github.com/rordenlab/dcm2niix); [Reunión]: "cuando entra DICOM se pasa a NIfTI" | `dsi_studio --action=src` directo desde DICOM (no hay DICOM de prueba para verificarlo) |
| Un NIfTI sin .bval/.bvec se rechaza con error | El encabezado NIfTI no guarda valores b ni direcciones; [Reunión] pidió atención a este caso. DSI Studio solo advierte y crea el .sz igual (verificado) | Seguir con advertencia |
| Validación: un valor b y una dirección por volumen, y al menos un b0 (b < 50 s/mm²) | Umbral = default `b0_threshold` de DIPY `gradient_table` | — |
| Archivo fuente `dwi.sz` con `dsi_studio --action=src --bval --bvec` | [DSI] cli_t1; [Marín] y tesis: primer paso, archivo SRC | — |
| **Sin** denoising MP-PCA ni corrección de Gibbs | [Reunión]: a 1.5T la SNR es más baja que a 3T (donde se validó [Liu]) y el denoising podría eliminar información. Gibbs: decidido con el autor (2026-11-03); [Marín] tampoco la usa | MP-PCA + Gibbs de [Liu] (implementado antes, eliminado) |
| Corrección de eddy y movimiento: `dsi_studio --action=rec --cmd=eddy+save_src=dwi_eddy.sz` → FSL `eddy_cpu` | [Reunión]; [Marín]; [DSI] cli_t2 y `run_eddy` | Llamar a eddy directamente desde Python |
| DSI Studio recarga el DWI corregido con los bvecs rotados por eddy (`.eddy_rotated_bvecs`) | [DSI] `load_topup_eddy_result`; [eddy] FAQ "Will eddy rotate my bvecs for me?" | — |
| **SUPUESTO** Fase de codificación AP y readout 0.05 s (`--acqp` = `0 -1 0 0.05`, lo fija DSI Studio cuando no hay TOPUP) | [DSI] `run_eddy`; [eddy] FAQ: con un readout desconocido, 0.05 s sirve. ds001378 no trae el JSON con `PhaseEncodingDirection` | LR (habría que confirmarlo con el protocolo Philips) |
| Sin TOPUP | ds001378 no tiene una adquisición con fase inversa | — |
| Máscara para eddy: U-Net de DSI Studio | [DSI] `run_eddy` (default) | `bet` |
| Reconstrucción DTI: `--method=1 --other_output=md,tensor`; el resto en los defaults de DSI Studio (máscara automática, remuestreo `make_isotropic=2`, `dti_ignore_high_b=1`) | [DSI] cli_t2; [Marín] y tesis: DTI pidiendo "tensor" | Tensor con DIPY (OLS), implementado antes |
| Figura QC con color-FA = \|V1\|·FA, calculado a partir del tensor completo exportado (también txy, txz, tyz); solo para mirar | Pajevic & Pierpaoli 1999 (Magn Reson Med 42:526-40); [Marín]: los neurorradiólogos ubican las fibras por color | FA en escala de grises (versión anterior) |
| Figura QC de eddy: DWI original y corregido, y su diferencia, en el corte outlier más extremo (o en el volumen con más movimiento) | [eddy] `.eddy_outlier_report` y `.eddy_movement_rms`. DSI Studio borra el NIfTI que le pasa a eddy, así que se compara con el original (mismos datos), ambos llevados a RAS | Solo métricas numéricas |
| Mapas exportados: fa, md, txx, tyy, tzz (`--action=exp`) | [DSI] cli_exp; txx/tyy/tzz son las filas que usan los neurorradiólogos (`Archive 4`) | — |

Observaciones para discutir con la profesora:
- DSI Studio le pasa a eddy solo `--data_is_shelled --verbose`, así que quedan los defaults de eddy: `--slm=none`,
  `--repol=False` (no reemplaza cortes outlier), sin slice-to-volume y `--nthr=1`. [Marín] dice que hubo
  "slice-to-volume registration and outlier replacement", pero la versión actual no los activa. En sub-control01, eddy
  marcó el corte 7 del volumen 3 como outlier (−21.6 DE) y no lo reemplazó. La guía de eddy recomienda considerar
  `--slm=linear` con pocas direcciones (aquí 15).
- Tiempo: ~45 min por sujeto, casi todo eddy con un solo hilo. La tesis reporta "más de una hora por imagen".
- DSI Studio remuestrea a 2 mm isotrópico por defecto y exporta el FA cuantizado en pasos de 1/255. txx, tyy y tzz se
  exportan en mm²/s, sin cuantizar.

## Pasos 4-6 (implementación anterior, en pausa hasta definir el atlas con los neurorradiólogos)

| Decisión | Fuente | Alternativa descartada |
|---|---|---|
| Template: `JHU-ICBM-FA-1mm.nii.gz` (FSL) | [Liu] Tabla 2; [alps.sh] `template=${FSLDIR}/data/atlases/JHU/JHU-ICBM-FA-1mm.nii.gz` | Plantilla QA de DSI Studio (usada por el intento anterior); MNI152 T1 (Liu la usa solo si hay imagen estructural) |
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

## Comparación con neurorradiólogos (solo en la app, modo experimental)

| Decisión | Fuente | Alternativa descartada |
|---|---|---|
| Mostrar el ALPS de cada neurorradiólogo (BO, FT, PC, RR) solo si el sujeto es sub-controlNN_ses-01 y existe su tabla | [Marín]: ROIs manuales sobre los 16 controles de ds001378, sesión 1 | — |
| ALPS del experto = mean(txx_proy, txx_asoc) / mean(tyy_proy, tzz_asoc), con las filas txx/tyy/tzz de su tabla de DSI Studio | `read_alps.m` (mismas filas y fórmula) | Recalcular con sus ROIs sobre nuestro tensor (es otra comparación, la de la etapa 2) |
| ROIs identificadas por nombre (p_i, a_i, p_d, a_d; sin distinguir mayúsculas ni '-'/'_') | El orden de las columnas cambia entre archivos | Usar la posición de la columna, como `read_alps.m` |
| Si falta el nombre de una ROI (p. ej. "New Region" en PC), ese hemisferio queda vacío | Trazabilidad: no se adivina qué ROI es. Decidido con el autor (2026-11-03) | Asignar "New Region"/"A.-" de PC como A-D |
| Se ignoran las ROIs "SC" | Correo de la profesora: las dibujó ella, "no son buenas referencias" | — |

## Supuestos

| Supuesto | Motivo | Alternativa |
|---|---|---|
| **SUPUESTO** Métrica de registro: información mutua (DIPY), inicialización por centro de masa → traslación → rígido → afín, parámetros del tutorial de DIPY | DIPY no implementa *correlation ratio* ni la búsqueda angular ±90° de FLIRT | `-cost corratio -searchr* -90 90` de [alps.sh] |
| **SUPUESTO** La diferencia de convención de bvec entre FSL y DIPY no afecta | Dxx, Dyy y Dzz no cambian al invertir el signo de un eje | — |
| **SUPUESTO** El color-FA de la figura QC se lleva al template canal por canal, sin reorientar | Solo es para control visual; no entra en el índice | — |

## Limitaciones conocidas

- Sin TOPUP (no hay adquisición con fase inversa en ds001378).
- Sin registro no lineal y sin reorientación del tensor (pasos 4-6, en pausa).
