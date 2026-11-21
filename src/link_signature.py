"""Ekstraksi JPEG Link Signature (Quantization Tables, Huffman Tables, Marker, EXIF)."""

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct
from PIL import ExifTags, Image

# Zigzag order untuk mengonversi DQT 64-byte ke matriks 8x8
_ZIGZAG_ORDER = [
    0, 1, 5, 6, 14, 15, 27, 28,
    2, 4, 7, 13, 16, 26, 29, 42,
    3, 8, 12, 17, 25, 30, 41, 43,
    9, 11, 18, 24, 31, 40, 44, 53,
    10, 19, 23, 32, 39, 45, 52, 54,
    20, 22, 33, 38, 46, 51, 55, 60,
    21, 34, 37, 47, 50, 56, 59, 61,
    35, 36, 48, 49, 57, 58, 62, 63,
]

# Tabel kuantisasi luminansi standar IJG (Q=50) untuk estimasi kualitas JPEG
_STD_LUMA_Q50 = [
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
]

_MARKER_NAMES = {
    0xD8: "SOI (Start of Image)",
    0xD9: "EOI (End of Image)",
    0xE0: "APP0 (JFIF)",
    0xE1: "APP1 (EXIF/XMP)",
    0xE2: "APP2 (ICC Profile)",
    0xED: "APP13 (Photoshop/IPTC)",
    0xEE: "APP14 (Adobe)",
    0xDB: "DQT (Quantization Table)",
    0xC0: "SOF0 (Baseline DCT)",
    0xC2: "SOF2 (Progressive DCT)",
    0xC4: "DHT (Huffman Table)",
    0xDA: "SOS (Start of Scan)",
    0xDD: "DRI (Restart Interval)",
    0xFE: "COM (Comment)",
}


@dataclass
class JpegLinkSignature:
    """Representasi struktur internal dan tanda tangan (signature) file JPEG."""

    file_path: str
    file_size_bytes: int
    width: int
    height: int
    color_mode: str
    is_jpeg: bool
    markers: list[str] = field(default_factory=list)
    quantization_tables: dict[int, list[list[int]]] = field(default_factory=dict)
    huffman_tables_count: int = 0
    estimated_quality: int | None = None
    exif: dict[str, str] = field(default_factory=dict)
    signature_hash: str = ""
    sof_type: str = "Unknown"


def _unzigzag(flat64: list[int]) -> list[list[int]]:
    matrix = [[0] * 8 for _ in range(8)]
    for i, z_idx in enumerate(_ZIGZAG_ORDER):
        r, c = divmod(i, 8)
        matrix[r][c] = flat64[z_idx]
    return matrix


def _estimate_quality_from_luma(luma_8x8: list[list[int]]) -> int:
    flat = [val for row in luma_8x8 for val in row]
    if all(v == 1 for v in flat):
        return 100

    ratios = [
        (flat[i] * 100.0) / _STD_LUMA_Q50[i]
        for i in range(64)
        if _STD_LUMA_Q50[i] > 0
    ]
    avg_scale = sum(ratios) / len(ratios)
    if avg_scale <= 100.0:
        q = round((200.0 - avg_scale) / 2.0)
    else:
        q = round(5000.0 / avg_scale) if avg_scale > 0 else 1
    return max(1, min(100, int(q)))


def _parse_jpeg_markers(data: bytes) -> tuple[list[str], dict[int, list[list[int]]], int, str]:
    markers: list[str] = []
    dqts: dict[int, list[list[int]]] = {}
    dht_count = 0
    sof_type = "Unknown"

    if len(data) < 2 or data[0:2] != b"\xFF\xD8":
        return markers, dqts, dht_count, sof_type

    markers.append(_MARKER_NAMES[0xD8])
    pos = 2
    n = len(data)

    while pos < n - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue

        while pos < n and data[pos] == 0xFF:
            pos += 1
        if pos >= n:
            break

        marker = data[pos]
        pos += 1

        if marker == 0x00 or (0xD0 <= marker <= 0xD7):
            continue

        name = _MARKER_NAMES.get(marker, f"0xFF{marker:02X}")
        markers.append(name)

        if marker == 0xD9:  # EOI
            break
        if marker == 0xDA:  # SOS - compressed scan data follows
            break

        if pos + 2 > n:
            break
        seg_len = struct.unpack(">H", data[pos : pos + 2])[0]
        seg_data = data[pos + 2 : pos + seg_len]
        pos += seg_len

        if marker in (0xC0, 0xC2):
            sof_type = name

        elif marker == 0xDB:  # DQT
            idx = 0
            while idx < len(seg_data):
                pq_tq = seg_data[idx]
                precision = (pq_tq >> 4) & 0x0F
                table_id = pq_tq & 0x0F
                idx += 1
                step = 2 if precision == 1 else 1
                needed = 64 * step
                if idx + needed > len(seg_data):
                    break
                if precision == 0:
                    vals = list(seg_data[idx : idx + 64])
                else:
                    vals = list(struct.unpack(">64H", seg_data[idx : idx + 128]))
                dqts[table_id] = _unzigzag(vals)
                idx += needed

        elif marker == 0xC4:  # DHT
            idx = 0
            while idx < len(seg_data):
                if idx + 17 > len(seg_data):
                    break
                counts = seg_data[idx + 1 : idx + 17]
                dht_count += 1
                idx += 17 + sum(counts)

    return markers, dqts, dht_count, sof_type


def extract_link_signature(image_path: str) -> JpegLinkSignature:
    """Mengekstrak metadata struktur internal JPEG dan menghitung signature hash."""
    path = Path(image_path)
    raw_bytes = path.read_bytes()

    with Image.open(path) as img:
        width, height = img.size
        color_mode = img.mode
        fmt = (img.format or "").upper()
        exif_dict: dict[str, str] = {}
        raw_exif = img.getexif()
        if raw_exif:
            for tag_id, val in raw_exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, f"Tag_{tag_id}")
                exif_dict[str(tag_name)] = str(val)[:120]

    is_jpeg = raw_bytes.startswith(b"\xFF\xD8") or fmt == "JPEG"
    markers, dqts, dht_count, sof_type = _parse_jpeg_markers(raw_bytes)

    est_q = _estimate_quality_from_luma(dqts[0]) if 0 in dqts else None

    hasher = hashlib.sha256()
    hasher.update("|".join(markers).encode("utf-8"))
    for tid in sorted(dqts.keys()):
        hasher.update(f"DQT{tid}:{dqts[tid]}".encode("utf-8"))
    hasher.update(f"DHT:{dht_count}".encode("utf-8"))

    return JpegLinkSignature(
        file_path=str(path),
        file_size_bytes=len(raw_bytes),
        width=width,
        height=height,
        color_mode=color_mode,
        is_jpeg=is_jpeg,
        markers=markers,
        quantization_tables=dqts,
        huffman_tables_count=dht_count,
        estimated_quality=est_q,
        exif=exif_dict,
        signature_hash=hasher.hexdigest()[:24],
        sof_type=sof_type,
    )


def compare_signatures(sig_a: JpegLinkSignature, sig_b: JpegLinkSignature) -> dict[str, object]:
    """Membandingkan dua JPEG Link Signature untuk mengecek kecocokan sumber/encoder."""
    same_hash = sig_a.signature_hash == sig_b.signature_hash
    same_dqt = sig_a.quantization_tables == sig_b.quantization_tables
    same_markers = sig_a.markers == sig_b.markers
    return {
        "exact_signature_match": same_hash,
        "same_quantization_tables": same_dqt,
        "same_marker_sequence": same_markers,
        "quality_a": sig_a.estimated_quality,
        "quality_b": sig_b.estimated_quality,
    }
