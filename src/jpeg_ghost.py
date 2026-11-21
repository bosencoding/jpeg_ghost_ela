"""Implementasi JPEG Ghost (Farid, 2009) dan Statistik Kolmogorov-Smirnov (K-S)."""

import io
import cv2
import numpy as np
from PIL import Image


def compute_jpeg_ghost(
    image_path: str,
    qualities: list[int] | None = None,
    block_size: int = 16,
    apply_colormap: bool = True,
    return_raw_maps: bool = False,
) -> dict[int, np.ndarray] | tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
    """Menghasilkan peta JPEG Ghost dengan normalisasi lintas kualitas (Slide 16).

    Langkah sesuai Farid (2009) & Slide 16:
    1. Hitung selisih kuadrat rata-rata 3 kanal RGB dan rata-rata spasial blok b x b:
       delta(x, y, q).
    2. Normalisasi per piksel (x, y) melintasi seluruh kualitas q yang diuji:
       d(x, y, q) = (delta(x, y, q) - min_q delta) / (max_q delta - min_q delta).

    Args:
        image_path: Path ke file gambar uji.
        qualities: Daftar nilai kualitas JPEG yang diuji. Default 50..95 step 5.
        block_size: Ukuran kernel spatial averaging (misal 8, 16, atau 32).
        apply_colormap: Jika True, terapkan COLORMAP_JET; jika False, grayscale RGB.
        return_raw_maps: Jika True, kembalikan juga dict peta float32 d(x, y, q) in [0, 1].

    Returns:
        dict[int, np.ndarray] atau tuple (ghost_maps_rgb, normalized_float_maps).
    """
    if qualities is None:
        qualities = list(range(50, 96, 5))

    orig_pil = Image.open(image_path).convert("RGB")
    orig_arr = np.asarray(orig_pil, dtype=np.float32)
    kernel = (int(block_size), int(block_size))

    deltas: list[np.ndarray] = []
    for q in qualities:
        buffer = io.BytesIO()
        orig_pil.save(buffer, format="JPEG", quality=int(q))
        buffer.seek(0)
        resaved_arr = np.asarray(Image.open(buffer), dtype=np.float32)

        sq_diff = np.mean((orig_arr - resaved_arr) ** 2, axis=2)
        smoothed_diff = cv2.blur(sq_diff, kernel)
        deltas.append(smoothed_diff)

    # Stack shape: (num_q, H, W) -> normalisasi melintasi sumbu kualitas (axis=0)
    delta_stack = np.stack(deltas, axis=0)
    min_q = np.min(delta_stack, axis=0)
    max_q = np.max(delta_stack, axis=0)
    denom = max_q - min_q

    ghost_maps: dict[int, np.ndarray] = {}
    raw_maps: dict[int, np.ndarray] = {}

    for idx, q in enumerate(qualities):
        d_map = np.zeros_like(delta_stack[idx], dtype=np.float32)
        valid = denom > 1e-12
        d_map[valid] = (delta_stack[idx][valid] - min_q[valid]) / denom[valid]
        raw_maps[int(q)] = d_map

        norm_uint8 = np.clip(d_map * 255.0, 0, 255).astype(np.uint8)
        if apply_colormap:
            colored = cv2.applyColorMap(norm_uint8, cv2.COLORMAP_JET)
            ghost_maps[int(q)] = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
        else:
            ghost_maps[int(q)] = cv2.cvtColor(norm_uint8, cv2.COLOR_GRAY2RGB)

    if return_raw_maps:
        return ghost_maps, raw_maps
    return ghost_maps


def _ks_2samp_stat(sample_a: np.ndarray, sample_b: np.ndarray) -> float:
    """Menghitung statistik Kolmogorov-Smirnov K = max_t |F_a(t) - F_b(t)|."""
    if sample_a.size == 0 or sample_b.size == 0:
        return 0.0
    a_sorted = np.sort(sample_a)
    b_sorted = np.sort(sample_b)
    all_vals = np.concatenate([a_sorted, b_sorted])
    cdf_a = np.searchsorted(a_sorted, all_vals, side="right") / float(a_sorted.size)
    cdf_b = np.searchsorted(b_sorted, all_vals, side="right") / float(b_sorted.size)
    return float(np.max(np.abs(cdf_a - cdf_b)))


def compute_ks_statistic(
    raw_maps: dict[int, np.ndarray],
    roi: tuple[int, int, int, int],
) -> dict[int, float]:
    """Menghitung statistik K-S antara wilayah ROI dan area lainnya untuk tiap Q.

    Sesuai Slide 18: K(Q) = max_t |F_objek(t; Q) - F_lainnya(t; Q)|.

    Args:
        raw_maps: Dict {Q: d_map_2d} dari compute_jpeg_ghost(..., return_raw_maps=True).
        roi: Tuple (x, y, width, height) wilayah yang dicurigai.

    Returns:
        dict[int, float]: Nilai K(Q) untuk setiap kualitas Q.
    """
    x, y, w, h = roi
    ks_scores: dict[int, float] = {}

    for q, d_map in sorted(raw_maps.items()):
        img_h, img_w = d_map.shape[:2]
        x1 = max(0, min(img_w - 1, int(x)))
        y1 = max(0, min(img_h - 1, int(y)))
        x2 = max(x1 + 1, min(img_w, int(x + w)))
        y2 = max(y1 + 1, min(img_h, int(y + h)))

        mask = np.zeros((img_h, img_w), dtype=bool)
        mask[y1:y2, x1:x2] = True

        obj_vals = d_map[mask]
        other_vals = d_map[~mask]
        ks_scores[int(q)] = _ks_2samp_stat(obj_vals, other_vals)

    return ks_scores
