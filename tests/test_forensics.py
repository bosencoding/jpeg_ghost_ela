"""Unit test untuk modul JPEG Link Signature, ELA, JPEG Ghost, dan dataset."""

from pathlib import Path
import numpy as np

from src.ela import compute_ela
from src.jpeg_ghost import compute_jpeg_ghost, compute_ks_statistic
from src.link_signature import compare_signatures, extract_link_signature

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTH_SAMPLE = PROJECT_ROOT / "dataset" / "authentic" / "auth_01_kamera_asli.jpg"
TAMP_SAMPLE = PROJECT_ROOT / "dataset" / "tampered" / "tamp_01_splice_q65_ke_q95.jpg"


def test_dataset_exists():
    assert AUTH_SAMPLE.exists(), "Dataset authentic belum dibuat"
    assert TAMP_SAMPLE.exists(), "Dataset tampered belum dibuat"
    auth_files = list((PROJECT_ROOT / "dataset" / "authentic").glob("*.jpg"))
    tamp_files = list((PROJECT_ROOT / "dataset" / "tampered").glob("*.jpg"))
    assert len(auth_files) == 16
    assert len(tamp_files) == 19


def test_link_signature_extraction():
    sig = extract_link_signature(str(AUTH_SAMPLE))
    assert sig.is_jpeg is True
    assert sig.width == 800 and sig.height == 600
    assert 0 in sig.quantization_tables
    assert len(sig.quantization_tables[0]) == 8
    assert sig.estimated_quality is not None
    assert 85 <= sig.estimated_quality <= 100
    assert len(sig.signature_hash) == 24

    cmp_self = compare_signatures(sig, sig)
    assert cmp_self["exact_signature_match"] is True
    assert cmp_self["same_quantization_tables"] is True


def test_ela_output_shape_and_dtype():
    ela_fixed = compute_ela(str(TAMP_SAMPLE), quality=90, scale=15)
    assert ela_fixed.shape == (600, 800, 3)
    assert ela_fixed.dtype == np.uint8

    ela_auto = compute_ela(str(TAMP_SAMPLE), quality=90, scale=None)
    assert ela_auto.shape == (600, 800, 3)
    assert ela_auto.dtype == np.uint8


def test_jpeg_ghost_detects_q65_minimum():
    maps, raw_maps = compute_jpeg_ghost(
        str(TAMP_SAMPLE),
        qualities=[15, 35, 55, 65, 85, 95],
        block_size=16,
        apply_colormap=False,
        return_raw_maps=True,
    )
    assert set(maps.keys()) == {15, 35, 55, 65, 85, 95}
    for q, arr in maps.items():
        assert arr.shape == (600, 800, 3)
        assert arr.dtype == np.uint8

    # Dengan normalisasi lintas kualitas (Slide 16), pada Q=65 area tempelan (288,192,224x224)
    # memiliki nilai d(x,y,65) lebih rendah daripada area latar belakang di Q=65.
    patch_mean_q65 = float(np.mean(raw_maps[65][210:390, 310:490]))
    bg_mean_q65 = float(np.mean(raw_maps[65][20:150, 20:200]))
    assert patch_mean_q65 < bg_mean_q65

    # Uji statistik K-S (Slide 18) pada ROI (288, 192, 224, 224)
    ks_scores = compute_ks_statistic(raw_maps, (288, 192, 224, 224))
    assert set(ks_scores.keys()) == {15, 35, 55, 65, 85, 95}
    assert ks_scores[65] > 0.3
