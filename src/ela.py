"""Implementasi Error Level Analysis (ELA) untuk deteksi manipulasi citra JPEG."""

import io
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def compute_ela(
    image_path: str,
    quality: int = 90,
    scale: int | None = 15,
) -> np.ndarray:
    """Menghasilkan peta Error Level Analysis (ELA) dari gambar JPEG.

    Args:
        image_path: Path ke file gambar uji.
        quality: Level kualitas JPEG acuan saat menyimpan ulang (50-100).
        scale: Faktor pengali kecerahan (1-50). Jika None, gunakan auto-scaling
            berbasis nilai selisih maksimum (255.0 / max_diff).

    Returns:
        np.ndarray: Gambar hasil ELA dalam format RGB (uint8).
    """
    orig_img = Image.open(image_path).convert("RGB")

    buffer = io.BytesIO()
    orig_img.save(buffer, format="JPEG", quality=int(quality))
    buffer.seek(0)
    resaved_img = Image.open(buffer)

    ela_img = ImageChops.difference(orig_img, resaved_img)

    extrema = ela_img.getextrema()
    max_diff = max(ex[1] for ex in extrema)
    if max_diff == 0:
        max_diff = 1

    scale_factor = (255.0 / max_diff) if scale is None else float(scale)
    ela_img = ImageEnhance.Brightness(ela_img).enhance(scale_factor)

    return np.array(ela_img, dtype=np.uint8)
