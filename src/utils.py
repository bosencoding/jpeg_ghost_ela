"""Fungsi bantu I/O gambar dan konversi untuk analisis forensik."""

from pathlib import Path
import numpy as np
from PIL import Image


def load_rgb_image(image_path: str) -> Image.Image:
    """Membuka citra dan mengonversinya ke mode RGB."""
    return Image.open(image_path).convert("RGB")


def save_lossless_png(image_array: np.ndarray, output_path: str) -> Path:
    """Menyimpan array RGB uint8 sebagai file PNG lossless."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image_array.astype(np.uint8)).save(out, format="PNG")
    return out
