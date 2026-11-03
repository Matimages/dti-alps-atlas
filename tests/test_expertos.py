import pytest

from alps.expertos import alps_expertos


def _tabla(ruta, columnas):
    """Escribe una tabla con el formato de DSI Studio: {nombre: (txx, tyy, tzz)}."""
    nombres = list(columnas)
    lineas = ["Name\t" + "\t".join(nombres) + "\t"]
    for i, fila in enumerate(("txx", "tyy", "tzz")):
        lineas.append(fila + "\t" + "\t".join(str(columnas[n][i]) for n in nombres) + "\t")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def test_lee_por_nombre_sin_importar_orden_ni_formato(tmp_path):
    _tabla(tmp_path / "BO" / "03.txt",
           {"A-D": (2, 9, 1), "p_i": (1, 1, 9), "P_D": (2, 1, 9), "A_I": (3, 9, 1)})
    r = alps_expertos("sub-control03_ses-01", tmp_path)["BO"]
    assert r["alps_L"] == pytest.approx(2.0)  # mean(1, 3) / mean(1, 1)
    assert r["alps_R"] == pytest.approx(2.0)  # mean(2, 2) / mean(1, 1)
    assert r["alps"] == pytest.approx(2.0)


def test_roi_sin_nombre_reconocible_deja_hemisferio_vacio(tmp_path):
    _tabla(tmp_path / "PC" / "01.txt",
           {"SC-I": (5, 5, 5), "P-I": (1, 1, 1), "A-I": (1, 1, 1), "P-D": (1, 1, 1), "New Region": (1, 1, 1)})
    r = alps_expertos("sub-control01_ses-01", tmp_path)["PC"]
    assert r["alps_L"] == pytest.approx(1.0)
    assert r["alps_R"] is None and r["alps"] is None


def test_otro_sujeto_o_sesion_no_muestra_nada(tmp_path):
    _tabla(tmp_path / "BO" / "01.txt", {"p_i": (1, 1, 1)})
    assert alps_expertos("sub-control01_ses-02", tmp_path) == {}
    assert alps_expertos("sub-SCA201_ses-01", tmp_path) == {}
