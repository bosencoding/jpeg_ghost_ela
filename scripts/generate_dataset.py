"""Generator dataset uji forensik JPEG (Authentic & Tampered) dengan ground truth Q1->Q2."""

import io
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _make_textured_scene(width: int = 800, height: int = 600, seed: int = 42) -> Image.Image:
    """Membuat citra sintetis bertekstur kaya (gradien, noise halus, objek geometris)."""
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, width, dtype=np.float32)
    y = np.linspace(0, 1, height, dtype=np.float32)
    xv, yv = np.meshgrid(x, y)

    r = 60 + 140 * xv + 30 * np.sin(8 * yv)
    g = 80 + 110 * yv + 25 * np.cos(6 * xv)
    b = 130 + 80 * (1 - xv) + 20 * np.sin(5 * (xv + yv))
    noise = rng.normal(0, 6.0, (height, width, 3))

    arr = np.stack([r, g, b], axis=2) + noise
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB")

    draw = ImageDraw.Draw(img)
    draw.rectangle([70, 90, 250, 260], fill=(190, 95, 70), outline=(40, 30, 30), width=3)
    draw.ellipse([500, 320, 720, 520], fill=(70, 155, 110), outline=(25, 50, 35), width=3)
    draw.polygon([(380, 70), (470, 210), (290, 210)], fill=(215, 185, 75))
    return img


def _make_donor_object(size: tuple[int, int] = (224, 224), seed: int = 99) -> Image.Image:
    """Membuat citra donor bertekstur setara dengan latar untuk skenario splicing."""
    rng = np.random.default_rng(seed)
    w, h = size
    x = np.linspace(0, 1, w, dtype=np.float32)
    y = np.linspace(0, 1, h, dtype=np.float32)
    xv, yv = np.meshgrid(x, y)

    arr = np.stack([
        90 + 110 * xv + 20 * np.sin(6 * yv) + rng.normal(0, 6.0, (h, w)),
        100 + 90 * yv + 20 * np.cos(5 * xv) + rng.normal(0, 6.0, (h, w)),
        110 + 80 * (1 - xv) + rng.normal(0, 6.0, (h, w)),
    ], axis=2)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")


def generate_all(base_dir: Path) -> None:
    auth_dir = base_dir / "authentic"
    tamp_dir = base_dir / "tampered"
    auth_dir.mkdir(parents=True, exist_ok=True)
    tamp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Authentic: single compression Q=95
    scene1 = _make_textured_scene(800, 600, seed=11)
    scene1.save(auth_dir / "auth_01_kamera_asli.jpg", format="JPEG", quality=95)

    # 2. Authentic: single compression Q=90 dengan tekstur berbeda
    scene2 = _make_textured_scene(800, 600, seed=22)
    scene2.save(auth_dir / "auth_02_indoor_tekstur.jpg", format="JPEG", quality=90)

    # 3. Authentic: global recompression Q=85 (kontrol negatif double compression global)
    buf = io.BytesIO()
    scene1.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    Image.open(buf).save(auth_dir / "auth_03_kompresi_ulang_q85.jpg", format="JPEG", quality=85)

    # 4. Tampered: Splicing donor Q1=65 ke target Q2=95, final Q=95 (8x8 aligned)
    donor = _make_donor_object((224, 224), seed=99)
    donor_buf = io.BytesIO()
    donor.save(donor_buf, format="JPEG", quality=65)
    donor_buf.seek(0)
    donor_q65 = Image.open(donor_buf)

    bg_buf = io.BytesIO()
    scene1.save(bg_buf, format="JPEG", quality=95)
    bg_buf.seek(0)
    spliced_65 = Image.open(bg_buf).convert("RGB")
    spliced_65.paste(donor_q65, (288, 192))
    spliced_65.save(tamp_dir / "tamp_01_splice_q65_ke_q95.jpg", format="JPEG", quality=95)

    # 5. Tampered: Splicing donor Q1=75 ke target Q2=95, final Q=95
    donor2_buf = io.BytesIO()
    _make_donor_object((200, 200), seed=105).save(donor2_buf, format="JPEG", quality=75)
    donor2_buf.seek(0)
    spliced_75 = scene2.copy()
    spliced_75.paste(Image.open(donor2_buf), (300, 200))
    spliced_75.save(tamp_dir / "tamp_02_splice_q75_ke_q95.jpg", format="JPEG", quality=95)

    # 6. Tampered: Copy-move pada citra Q1=75 lalu disimpan ulang Q=90
    cm_buf = io.BytesIO()
    scene1.save(cm_buf, format="JPEG", quality=75)
    cm_buf.seek(0)
    cm_img = Image.open(cm_buf).convert("RGB")
    patch = cm_img.crop((70, 90, 250, 260))
    cm_img.paste(patch, (460, 80))
    cm_img.save(tamp_dir / "tamp_03_copymove_q75_ke_q90.jpg", format="JPEG", quality=90)

    # 7. Tampered: Text overlay tajam pada citra Q1=70 lalu disimpan Q=95
    txt_buf = io.BytesIO()
    scene2.save(txt_buf, format="JPEG", quality=70)
    txt_buf.seek(0)
    txt_img = Image.open(txt_buf).convert("RGB")
    draw = ImageDraw.Draw(txt_img)
    draw.rectangle([220, 460, 580, 540], fill=(20, 20, 20), outline=(255, 255, 255), width=3)
    draw.text((255, 490), "EDITED / FORGED STAMP", fill=(255, 230, 80), font=ImageFont.load_default())
    txt_img.save(tamp_dir / "tamp_04_text_overlay_q70_ke_q95.jpg", format="JPEG", quality=95)

    # --- Tambahan 10 Dataset Baru (4 Authentic + 6 Tampered) ---

    # 8. Authentic: single compression Q=92 (seed 33)
    scene3 = _make_textured_scene(800, 600, seed=33)
    scene3.save(auth_dir / "auth_04_outdoor_q92.jpg", format="JPEG", quality=92)

    # 9. Authentic: single compression Q=88 (seed 44)
    scene4 = _make_textured_scene(800, 600, seed=44)
    scene4.save(auth_dir / "auth_05_arsitektur_q88.jpg", format="JPEG", quality=88)

    # 10. Authentic: single compression Q=95 (seed 55)
    scene5 = _make_textured_scene(800, 600, seed=55)
    scene5.save(auth_dir / "auth_06_studio_q95.jpg", format="JPEG", quality=95)

    # 11. Authentic: global recompression Q=80 dari scene3
    buf_a7 = io.BytesIO()
    scene3.save(buf_a7, format="JPEG", quality=95)
    buf_a7.seek(0)
    Image.open(buf_a7).save(auth_dir / "auth_07_kompresi_ulang_q80.jpg", format="JPEG", quality=80)

    # 12. Tampered: Splicing donor Q1=55 ke target Q2=95 (8x8 aligned)
    d55_buf = io.BytesIO()
    _make_donor_object((208, 208), seed=111).save(d55_buf, format="JPEG", quality=55)
    d55_buf.seek(0)
    spliced_55 = scene3.copy()
    spliced_55.paste(Image.open(d55_buf), (128, 128))
    spliced_55.save(tamp_dir / "tamp_05_splice_q55_ke_q95.jpg", format="JPEG", quality=95)

    # 13. Tampered: Splicing donor Q1=60 ke target Q2=90 (8x8 aligned)
    d60_buf = io.BytesIO()
    _make_donor_object((192, 192), seed=122).save(d60_buf, format="JPEG", quality=60)
    d60_buf.seek(0)
    spliced_60 = scene4.copy()
    spliced_60.paste(Image.open(d60_buf), (448, 256))
    spliced_60.save(tamp_dir / "tamp_06_splice_q60_ke_q90.jpg", format="JPEG", quality=90)

    # 14. Tampered: Splicing donor Q1=70 ke target Q2=95 (8x8 aligned)
    d70_buf = io.BytesIO()
    _make_donor_object((240, 176), seed=133).save(d70_buf, format="JPEG", quality=70)
    d70_buf.seek(0)
    spliced_70 = scene5.copy()
    spliced_70.paste(Image.open(d70_buf), (256, 192))
    spliced_70.save(tamp_dir / "tamp_07_splice_q70_ke_q95.jpg", format="JPEG", quality=95)

    # 15. Tampered: Splicing donor Q1=80 ke target Q2=95 (8x8 aligned)
    d80_buf = io.BytesIO()
    _make_donor_object((208, 208), seed=144).save(d80_buf, format="JPEG", quality=80)
    d80_buf.seek(0)
    spliced_80 = scene3.copy()
    spliced_80.paste(Image.open(d80_buf), (320, 160))
    spliced_80.save(tamp_dir / "tamp_08_splice_q80_ke_q95.jpg", format="JPEG", quality=95)

    # 16. Tampered: Multi-splicing (dua objek berbeda Q1=60 dan Q1=75 pada latar Q2=95)
    d_m1 = io.BytesIO()
    _make_donor_object((160, 160), seed=155).save(d_m1, format="JPEG", quality=60)
    d_m1.seek(0)
    d_m2 = io.BytesIO()
    _make_donor_object((160, 160), seed=166).save(d_m2, format="JPEG", quality=75)
    d_m2.seek(0)
    multi_img = scene4.copy()
    multi_img.paste(Image.open(d_m1), (96, 192))
    multi_img.paste(Image.open(d_m2), (512, 192))
    multi_img.save(tamp_dir / "tamp_09_multisplice_q60_q75_ke_q95.jpg", format="JPEG", quality=95)

    # 17. Tampered: Copy-move pada citra Q1=65 lalu disimpan ulang Q=95
    cm2_buf = io.BytesIO()
    scene5.save(cm2_buf, format="JPEG", quality=65)
    cm2_buf.seek(0)
    cm2_img = Image.open(cm2_buf).convert("RGB")
    patch2 = cm2_img.crop((500, 320, 720, 520))
    cm2_img.paste(patch2, (80, 320))
    cm2_img.save(tamp_dir / "tamp_10_copymove_q65_ke_q95.jpg", format="JPEG", quality=95)

    print(f"Dataset uji berhasil dibuat di: {base_dir}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    generate_all(project_root / "dataset")
