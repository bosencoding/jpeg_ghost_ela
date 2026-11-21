# JPEG Link Signature — Analisis Forensik Citra (ELA & JPEG Ghost)

Aplikasi analisis forensik citra digital berbasis Python dan PyQt6 yang mengintegrasikan ekstraksi **JPEG Link Signature** dengan dua metode deteksi manipulasi citra (*image tampering/forgery*): **Error Level Analysis (ELA)** dan **JPEG Ghost**.

---

## 1. Fitur Utama

1. **JPEG Link Signature**
   Mengekstrak dan menganalisis struktur internal file JPEG secara biner: urutan *marker* (`SOI`, `APP0/APP1`, `DQT`, `SOF0/SOF2`, `DHT`, `SOS`), matriks *Quantization Tables* 8×8 (Luminance & Chrominance), estimasi kualitas JPEG, jumlah *Huffman Tables*, metadata EXIF, serta menghasilkan *Signature Hash* (SHA-256) untuk membandingkan kecocokan sumber/encoder antar dua file JPEG.
2. **Error Level Analysis (ELA)**
   Mendeteksi anomali tingkat kompresi dengan menyimpan ulang citra di memori (`io.BytesIO`) pada kualitas acuan ($Q$) dan menghitung selisih absolut piksel ($\|I_{\text{orig}} - I_{\text{resaved}}\|$) yang diamplifikasi dengan *scale factor* atau *auto-scale* untuk menyoroti area hasil *splicing* atau penyuntingan lokal.
3. **JPEG Ghost (Farid, 2009)**
   Mendeteksi jejak *double JPEG compression* dengan memindai kompresi ulang pada rentang kualitas tertentu ($Q = 50\dots95$), menghitung *Sum of Squared Differences* (SSD) rata-rata kanal RGB, melakukan *spatial averaging* per blok ($8\times8$, $16\times16$, atau $32\times32$) untuk meredam artefak kisi DCT, dan memvisualisasikannya dengan *slider* interaktif serta *grid thumbnail* (`COLORMAP_JET` atau *grayscale*).

---

## 2. Prasyarat & Instalasi

* Python **3.10** atau lebih baru
* `pip` (Python package manager)

### Langkah Instalasi

1. Masuk ke direktori proyek:
   ```bash
   cd tugaskul_ghost_jpeg
   ```
2. Buat dan aktifkan *virtual environment*:
   ```bash
   python3 -m venv .venv
   # Linux / macOS:
   source .venv/bin/activate
   # Windows:
   .venv\Scripts\activate
   ```
3. Instal seluruh pustaka yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```

---

## 3. Petunjuk Menjalankan Aplikasi

Jalankan perintah berikut dari direktori utama proyek:
```bash
python main.py
```

Jika ingin membuat ulang dataset uji sintetis:
```bash
python scripts/generate_dataset.py
```

---

## 4. Panduan Penggunaan (User Guide)

### Memuat Citra Uji
* Klik **Load Image...** untuk memilih file `.jpg`/`.jpeg` dari komputer Anda, **atau** pilih salah satu sampel dari dropdown **Sampel Dataset** lalu klik **Muat Sampel**.

### A. Tab 1: JPEG Link Signature
* Secara otomatis mengekstrak marker JPEG, matriks DQT 8×8, estimasi kualitas, EXIF, dan *Signature Hash*.
* Klik **Bandingkan dengan JPEG Lain...** untuk mengecek apakah dua file JPEG memiliki *Quantization Tables* dan urutan marker yang identik.

### B. Tab 2: Error Level Analysis (ELA)
1. Atur **JPEG Quality (Q)** (default `90`, rentang `50–100`).
2. Atur **Error Scale** (default `15`, rentang `1–50`) atau centang **Auto-Scale**.
3. Klik **Run ELA**.
4. Klik **Simpan Hasil ELA (.png)** untuk menyimpan visualisasi secara *lossless*.

**Cara Membaca Hasil ELA:**
* **Authentic:** Area dengan tekstur serupa memiliki tingkat kecerahan error yang seragam.
* **Tampered:** Objek tempelan atau teks editan memiliki kecerahan error yang jauh lebih terang atau lebih gelap dibanding sekitarnya.

### C. Tab 3: JPEG Ghost
1. Atur rentang **Q Min** (`50`), **Q Max** (`95`), **Step** (`5`), dan **Block Size** (`16`).
2. Centang **Colormap JET** (disarankan) dan klik **Generate Ghost Maps**.
3. Geser **Pilih Kualitas Q** atau klik tombol `Q = ...` pada grid thumbnail di bagian bawah.

**Cara Membaca Hasil JPEG Ghost:**
* Saat nilai $Q$ mendekati kualitas kompresi asli ($Q_1$) dari bagian yang ditempelkan, selisih kuadrat (SSD) di area tersebut mencapai titik minimum lokal.
* Pada **Colormap JET**, area manipulasi akan tampak berwarna **biru tua pekat** kontras terhadap latar belakang hijau/kuning/merah (misal pada `tamp_01_splice_q65_ke_q95.jpg` di sekitar `Q = 65`).

---

## 5. Struktur Direktori

```text
tugaskul_ghost_jpeg/
├── main.py                       # Entry point GUI PyQt6
├── requirements.txt              # Daftar pustaka Python
├── README.md                     # Dokumentasi & User Guide
├── src/
│   ├── __init__.py
│   ├── link_signature.py         # Ekstraksi & perbandingan JPEG Link Signature
│   ├── ela.py                    # Implementasi Error Level Analysis (ELA)
│   ├── jpeg_ghost.py             # Implementasi JPEG Ghost (Farid, 2009)
│   └── utils.py                  # Fungsi bantu I/O gambar & simpan PNG lossless
├── scripts/
│   └── generate_dataset.py       # Generator dataset uji Authentic & Tampered
├── dataset/
│   ├── README_DATASET.md         # Deskripsi skenario dataset uji
│   ├── authentic/                # Sampel citra asli
│   └── tampered/                 # Sampel citra manipulasi (splicing, copy-move, overlay)
└── tests/
    └── test_forensics.py         # Unit test modul forensik
```

---

## 6. Referensi

* Krawetz, N. (2007). *A Picture's Worth... Digital Image Analysis and Forensics*. Hacker Factor Solutions.
* Farid, H. (2009). *Exposing Digital Forgeries from JPEG Ghosts*. IEEE Transactions on Information Forensics and Security, 4(1), 154–160.
