import numpy as np
from dipy.denoise.localpca import mppca

from alps.preproceso import RADIO_PCA, mppca_paralelo


def test_mppca_paralelo_identico_al_serial():
    rng = np.random.default_rng(0)
    datos = (100 + 10 * rng.standard_normal((40, 12, 10, 8))).astype(np.float32)
    serial = mppca(datos, patch_radius=RADIO_PCA)
    paralelo = mppca_paralelo(datos, n_procesos=4)
    assert paralelo.dtype == serial.dtype
    assert np.array_equal(paralelo, serial)
