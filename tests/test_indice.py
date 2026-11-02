import numpy as np
import pytest

from alps.indice import indice_alps, medias_en_rois
from alps.rois import esferas


def test_formula_con_valores_conocidos():
    v = {"x_proj_L": 1.0, "x_assoc_L": 2.0, "y_proj_L": 0.5, "z_assoc_L": 1.0,
         "x_proj_R": 1.2, "x_assoc_R": 1.2, "y_proj_R": 1.0, "z_assoc_R": 1.0}
    r = indice_alps(v)
    assert r["alps_L"] == pytest.approx(1.5 / 0.75)
    assert r["alps_R"] == pytest.approx(1.2)
    assert r["alps"] == pytest.approx((2.0 + 1.2) / 2)


def test_difusion_isotropica_da_alps_1():
    forma = (182, 218, 182)
    d = np.full(forma, 0.8e-3, dtype=np.float32)
    r = indice_alps(medias_en_rois(d, d, d, esferas(forma)))
    assert r["alps_L"] == pytest.approx(1.0)
    assert r["alps_R"] == pytest.approx(1.0)


def test_media_usa_solo_la_roi_correspondiente():
    forma = (182, 218, 182)
    rois = esferas(forma)
    dxx = np.zeros(forma)
    dxx[rois["L_SCR"]] = 2.0
    dxx[rois["L_SLF"]] = 4.0
    uno = np.ones(forma)
    v = medias_en_rois(dxx, uno, uno, rois)
    assert v["x_proj_L"] == 2.0 and v["x_assoc_L"] == 4.0 and v["x_proj_R"] == 0.0
    assert indice_alps(v)["alps_L"] == pytest.approx(3.0)
