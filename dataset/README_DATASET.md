# Keterangan Dataset Uji

Semua gambar beresolusi 800x600 piksel agar proses pemindaian blok DCT pada JPEG Ghost berjalan cepat dan responsif saat didemokan.

## Authentic (Kontrol Negatif - 16 File)
1. `authentic/auth_01_kamera_asli.jpg` - Citra sintetis tanpa penyuntingan (single JPEG compression, Q=95).
2. `authentic/auth_02_indoor_tekstur.jpg` - Citra sintetis dengan variasi tekstur dan warna (single JPEG compression, Q=90).
3. `authentic/auth_03_kompresi_ulang_q85.jpg` - Citra utuh yang dikompresi ulang secara global di Q=85 (untuk menguji bahwa kompresi global tidak memunculkan anomali lokal palsu).
4. `authentic/auth_04_outdoor_q92.jpg` - Citra sintetis (single JPEG compression, Q=92).
5. `authentic/auth_05_arsitektur_q88.jpg` - Citra sintetis (single JPEG compression, Q=88).
6. `authentic/auth_06_studio_q95.jpg` - Citra sintetis (single JPEG compression, Q=95).
7. `authentic/auth_07_kompresi_ulang_q80.jpg` - Citra utuh yang dikompresi ulang secara global di Q=80.
8. `authentic/real_reconyx_hc500.jpg` - Foto kamera asli **Reconyx HC500 Hyperfire** (2048×1536, EXIF & DQT kamera utuh) dari `ianare/exif-samples`.
9. `authentic/real_pixel_sample_01.jpg` - Foto kamera asli **Google Pixel** (`Ultra_HDR_Samples_Originals_01.jpg`, EXIF & DQT utuh).
10. `authentic/real_pixel_sample_02.jpg` - Foto kamera asli **Google Pixel** (`Ultra_HDR_Samples_Originals_02.jpg`, EXIF & DQT utuh).
11. `authentic/real_pixel_sample_03.jpg` - Foto kamera asli **Google Pixel** (`Ultra_HDR_Samples_Originals_03.jpg`, EXIF & DQT utuh).
12. `authentic/real_pixel_sample_04.jpg` - Foto kamera asli **Google Pixel** (`Ultra_HDR_Samples_Originals_04.jpg`, EXIF & DQT utuh).
13. `authentic/real_pixel_sample_05.jpg` - Foto kamera asli **Google Pixel** (`Ultra_HDR_Samples_Originals_05.jpg`, EXIF & DQT utuh).
14. `authentic/real_pixel_sample_06.jpg` - Foto kamera asli **Google Pixel** (`Ultra_HDR_Samples_Originals_06.jpg`, EXIF & DQT utuh).
15. `authentic/real_pixel_sample_07.jpg` - Foto kamera asli **Google Pixel** (`Ultra_HDR_Samples_Originals_07.jpg`, EXIF & DQT utuh).
16. `authentic/real_pixel_sample_08.jpg` - Foto kamera asli **Google Pixel** (`Ultra_HDR_Samples_Originals_08.jpg`, EXIF & DQT utuh).

## Tampered (Kontrol Positif Manipulasi - 19 File)
1. `tampered/tamp_01_splice_q65_ke_q95.jpg` - Objek tempelan di koordinat `(288, 192)` berukuran `224x224` berasal dari JPEG `Q1=65` yang ditempelkan ke latar `Q2=95`. Target deteksi JPEG Ghost muncul jelas di `Q=65`.
2. `tampered/tamp_02_splice_q75_ke_q95.jpg` - Objek tempelan di koordinat `(300, 200)` berukuran `200x200` berasal dari JPEG `Q1=75` yang ditempelkan ke latar `Q2=95`. Target deteksi JPEG Ghost muncul di `Q=75`.
3. `tampered/tamp_03_copymove_q75_ke_q90.jpg` - Duplikasi objek (copy-move) dari `(70, 90)-(250, 260)` ke `(460, 80)` pada citra awal `Q=75` yang disimpan ulang di `Q=90`.
4. `tampered/tamp_04_text_overlay_q70_ke_q95.jpg` - Penambahan teks/kotak tajam baru di koordinat `(220, 460)-(580, 540)` pada citra `Q=70` yang disimpan ulang di `Q=95`.
5. `tampered/tamp_05_splice_q55_ke_q95.jpg` - Splicing objek `208x208` di `(128, 128)` dari `Q1=55` ke latar `Q2=95`. Target JPEG Ghost di `Q=55`.
6. `tampered/tamp_06_splice_q60_ke_q90.jpg` - Splicing objek `192x192` di `(448, 256)` dari `Q1=60` ke latar `Q2=90`. Target JPEG Ghost di `Q=60`.
7. `tampered/tamp_07_splice_q70_ke_q95.jpg` - Splicing objek `240x176` di `(256, 192)` dari `Q1=70` ke latar `Q2=95`. Target JPEG Ghost di `Q=70`.
8. `tampered/tamp_08_splice_q80_ke_q95.jpg` - Splicing objek `208x208` di `(320, 160)` dari `Q1=80` ke latar `Q2=95`. Target JPEG Ghost di `Q=80`.
9. `tampered/tamp_09_multisplice_q60_q75_ke_q95.jpg` - Multi-splicing dua objek `160x160`: kiri di `(96, 192)` dengan `Q1=60` dan kanan di `(512, 192)` dengan `Q1=75` pada latar `Q2=95`.
10. `tampered/tamp_10_copymove_q65_ke_q95.jpg` - Duplikasi objek (copy-move) elips dari `(500, 320)-(720, 520)` ke `(80, 320)` pada citra `Q=65` yang disimpan ulang di `Q=95`.
11. `tampered/tamp_real_splice_q65_ke_q95.jpg` - Splicing foto kamera asli (`real_pixel_sample_05` pada `Q1=65`) ke latar foto kamera asli (`real_pixel_sample_01` pada `Q2=95`).
12. `tampered/tamp_real_splice_q75_ke_q95.jpg` - Splicing foto kamera asli (`real_pixel_sample_05` pada `Q1=75`) ke latar foto kamera asli (`real_pixel_sample_02` pada `Q2=95`).
13. `tampered/tamp_real_copymove_q70_ke_q95.jpg` - Copy-move pada foto kamera asli `Q1=70` yang disimpan ulang pada `Q2=95`.
14. `tampered/tamp_real_overlay_q70_ke_q95.jpg` - Penambahan kotak/teks tajam pada foto kamera asli `Q1=70` yang disimpan ulang pada `Q2=95`.
15. `tampered/tamp_real_splice_q55_ke_q95.jpg` - Splicing foto kamera asli (`real_pixel_sample_07` pada `Q1=55`) ke latar foto kamera asli (`real_pixel_sample_03` pada `Q2=95`).
16. `tampered/tamp_real_splice_q60_ke_q90.jpg` - Splicing foto kamera asli (`real_pixel_sample_08` pada `Q1=60`) ke latar foto kamera asli (`real_pixel_sample_04` pada `Q2=90`).
17. `tampered/tamp_real_splice_q80_ke_q95.jpg` - Splicing foto kamera asli (`real_pixel_sample_07` pada `Q1=80`) ke latar foto kamera asli (`real_pixel_sample_06` pada `Q2=95`).
18. `tampered/tamp_real_multisplice_q60_q75_ke_q95.jpg` — Multi-splicing dua foto asli (`Q1=60` di kiri dan `Q1=75` di kanan) pada latar `real_pixel_sample_03` (`Q2=95`).
19. `tampered/tamp_real_copymove_q65_ke_q95.jpg` — Copy-move pada foto kamera asli `real_pixel_sample_04` (`Q1=65`) yang disimpan ulang pada `Q2=95`.
