import nibabel as nib
import numpy as np
import pytest

from alps.entrada import resolver_entrada


def _dwi(carpeta, n_vol=3, bvals="0 1000 1000", bvecs=("0 1 0", "0 0 1", "0 0 0")):
    nifti = carpeta / "sub_dwi.nii.gz"
    nib.save(nib.Nifti1Image(np.zeros((4, 4, 4, n_vol), np.float32), np.eye(4)), str(nifti))
    if bvals is not None:
        (carpeta / "sub_dwi.bval").write_text(bvals)
    if bvecs is not None:
        (carpeta / "sub_dwi.bvec").write_text("\n".join(bvecs))
    return nifti


def test_nifti_con_bval_bvec_al_lado(tmp_path):
    nifti, bval, bvec = resolver_entrada(_dwi(tmp_path), tmp_path)
    assert bval.name == "sub_dwi.bval" and bvec.name == "sub_dwi.bvec"


def test_nifti_solo_se_detiene(tmp_path):
    with pytest.raises(FileNotFoundError, match="no guarda los valores b"):
        resolver_entrada(_dwi(tmp_path, bvals=None, bvecs=None), tmp_path)


def test_bval_que_no_coincide_con_los_volumenes(tmp_path):
    with pytest.raises(ValueError, match="deben coincidir"):
        resolver_entrada(_dwi(tmp_path, bvals="0 1000"), tmp_path)


def test_sin_b0(tmp_path):
    with pytest.raises(ValueError, match="b0"):
        resolver_entrada(_dwi(tmp_path, bvals="1000 1000 1000"), tmp_path)
