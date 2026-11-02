from pathlib import Path

import numpy as np
import pytest

from alps.rois import CENTROS, esferas

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def test_81_voxeles_y_centro():
    for nombre, mascara in esferas().items():
        assert mascara.sum() == 81
        assert tuple(np.argwhere(mascara).mean(axis=0)) == CENTROS[nombre]


def test_simetria_izquierda_derecha():
    # Pares L/R simétricos respecto de i = 90 (x = 0 mm en JHU).
    assert CENTROS["L_SCR"][0] + CENTROS["R_SCR"][0] == 180
    assert CENTROS["L_SLF"][0] + CENTROS["R_SLF"][0] == 180


@pytest.mark.parametrize("nombre", list(CENTROS))
def test_igual_a_rois_de_gbarisano(nombre):
    """Compara con ROIs_JHU_ALPS/<nombre>.nii.gz de github.com/gbarisano/alps (si se descargó a templates/)."""
    archivo = TEMPLATES / f"{nombre}.nii.gz"
    if not archivo.exists():
        pytest.skip(f"falta {archivo}")
    import nibabel as nib

    repo = nib.load(str(archivo)).get_fdata() > 0
    assert np.array_equal(repo, esferas()[nombre])
