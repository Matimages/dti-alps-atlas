import numpy as np

from alps.registro import AFFINE_MNI, bvecs_al_atlas

BVECS = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [0.6, 0.8, 0]]).T  # 3×N, convención FSL


def test_sin_registro_y_misma_grilla_no_cambia():
    assert np.allclose(bvecs_al_atlas(BVECS, AFFINE_MNI, np.eye(4), AFFINE_MNI), BVECS)


def test_misma_imagen_guardada_ras_o_las_tiene_los_mismos_bvecs_fsl():
    # En FSL los bvecs no cambian si la imagen se guarda con el eje x invertido (por eso se invierte x con det > 0).
    ras = np.diag([1.0, 1.0, 1.0, 1.0])
    assert np.allclose(bvecs_al_atlas(BVECS, ras, np.eye(4), AFFINE_MNI), BVECS)


def test_rotacion_de_la_cabeza_se_deshace():
    # El registro lleva puntos del atlas al sujeto girados 30° en z; una dirección del sujeto vuelve girada −30°.
    t = np.radians(30)
    rot = np.array([[np.cos(t), -np.sin(t), 0, 0], [np.sin(t), np.cos(t), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
    g_mundo = np.array([[np.cos(t)], [np.sin(t)], [0.0]])  # eje x del atlas, visto en el sujeto girado
    g_fsl_sujeto = np.diag([-1.0, 1.0, 1.0]) @ g_mundo  # sujeto en LAS (como AFFINE_MNI): vóxel i = −x
    salida = bvecs_al_atlas(g_fsl_sujeto, AFFINE_MNI, rot, AFFINE_MNI)
    assert np.allclose(salida[:, 0], [-1, 0, 0])  # x del mundo en la grilla LAS del atlas, sin inversión (det < 0)
