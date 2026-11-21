"""Aplikasi GUI PyQt6: JPEG Link Signature, Error Level Analysis (ELA), & JPEG Ghost."""

from pathlib import Path
import sys
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ela import compute_ela
from src.jpeg_ghost import compute_jpeg_ghost, compute_ks_statistic
from src.link_signature import compare_signatures, extract_link_signature
from src.utils import load_rgb_image, save_lossless_png


def numpy_to_qpixmap(arr: np.ndarray) -> QPixmap:
    """Mengonversi array RGB uint8 menjadi QPixmap."""
    h, w, ch = arr.shape
    bytes_per_line = ch * w
    q_img = QImage(arr.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(q_img)


class GhostWorker(QThread):
    """Worker thread untuk komputasi JPEG Ghost agar UI tetap responsif."""

    finished_maps = pyqtSignal(dict, dict)
    failed = pyqtSignal(str)

    def __init__(self, image_path: str, qualities: list[int], block_size: int, apply_colormap: bool):
        super().__init__()
        self.image_path = image_path
        self.qualities = qualities
        self.block_size = block_size
        self.apply_colormap = apply_colormap

    def run(self) -> None:
        try:
            maps, raw_maps = compute_jpeg_ghost(
                self.image_path,
                qualities=self.qualities,
                block_size=self.block_size,
                apply_colormap=self.apply_colormap,
                return_raw_maps=True,
            )
            self.finished_maps.emit(maps, raw_maps)
        except Exception as exc:
            self.failed.emit(str(exc))


class ImageLabel(QLabel):
    """QLabel dengan penskalaan proporsional otomatis untuk menampilkan gambar."""

    def __init__(self, placeholder: str = "Belum ada gambar"):
        super().__init__(placeholder)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setStyleSheet("border: 1px solid #444; background-color: #1e1e1e; color: #aaa;")
        self._pixmap: QPixmap | None = None

    def set_pixmap_image(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._update_scaled()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_scaled()

    def _update_scaled(self) -> None:
        if self._pixmap is not None and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            super().setPixmap(scaled)


class ForensicsMainWindow(QMainWindow):
    """Jendela utama aplikasi JPEG Link Signature — Forensik Citra Digital."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JPEG Link Signature — Forensik Citra (ELA & JPEG Ghost)")
        self.resize(1280, 820)

        self.current_image_path: str | None = None
        self.current_ela_array: np.ndarray | None = None
        self.current_ghost_maps: dict[int, np.ndarray] = {}
        self.current_ghost_raw: dict[int, np.ndarray] = {}
        self.current_signature = None
        self.ghost_worker: GhostWorker | None = None

        self._init_ui()
        self._populate_dataset_samples()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        # Toolbar atas: muat gambar & sampel dataset
        top_bar = QHBoxLayout()
        self.btn_open = QPushButton("Load Image...")
        self.btn_open.clicked.connect(self._open_image_dialog)
        top_bar.addWidget(self.btn_open)

        top_bar.addWidget(QLabel("Sampel Dataset:"))
        self.combo_dataset = QComboBox()
        self.combo_dataset.setMinimumWidth(280)
        top_bar.addWidget(self.combo_dataset)

        self.btn_load_sample = QPushButton("Muat Sampel")
        self.btn_load_sample.clicked.connect(self._load_selected_sample)
        top_bar.addWidget(self.btn_load_sample)

        self.lbl_path = QLabel("Belum ada file dipilih")
        self.lbl_path.setStyleSheet("color: #888;")
        top_bar.addWidget(self.lbl_path, stretch=1)
        root_layout.addLayout(top_bar)

        # Splitter utama: Kiri = Gambar Asli, Kanan = Tab Forensik
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, stretch=1)

        left_box = QGroupBox("Citra Uji (Original)")
        left_layout = QVBoxLayout(left_box)
        self.orig_preview = ImageLabel("Pilih gambar JPEG untuk memulai analisis")
        left_layout.addWidget(self.orig_preview)
        splitter.addWidget(left_box)

        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        splitter.setSizes([420, 840])

        self._build_link_signature_tab()
        self._build_ela_tab()
        self._build_ghost_tab()

    def _build_link_signature_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btn_row = QHBoxLayout()
        self.btn_extract_sig = QPushButton("Ekstrak JPEG Link Signature")
        self.btn_extract_sig.clicked.connect(self._run_link_signature)
        btn_row.addWidget(self.btn_extract_sig)

        self.btn_compare_sig = QPushButton("Bandingkan dengan JPEG Lain...")
        self.btn_compare_sig.clicked.connect(self._compare_with_other_jpeg)
        btn_row.addWidget(self.btn_compare_sig)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.sig_output = QTextEdit()
        self.sig_output.setReadOnly(True)
        self.sig_output.setStyleSheet("font-family: monospace; font-size: 12px;")
        layout.addWidget(self.sig_output)

        self.tabs.addTab(tab, "1. JPEG Link Signature")

    def _build_ela_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        ctrl_box = QGroupBox("Parameter Error Level Analysis (ELA)")
        ctrl_layout = QGridLayout(ctrl_box)

        ctrl_layout.addWidget(QLabel("JPEG Quality (Q):"), 0, 0)
        self.ela_q_slider = QSlider(Qt.Orientation.Horizontal)
        self.ela_q_slider.setRange(50, 100)
        self.ela_q_slider.setValue(75)
        self.ela_q_val = QLabel("75")
        self.ela_q_slider.valueChanged.connect(lambda v: self.ela_q_val.setText(str(v)))
        ctrl_layout.addWidget(self.ela_q_slider, 0, 1)
        ctrl_layout.addWidget(self.ela_q_val, 0, 2)

        ctrl_layout.addWidget(QLabel("Error Scale:"), 1, 0)
        self.ela_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.ela_scale_slider.setRange(1, 50)
        self.ela_scale_slider.setValue(15)
        self.ela_scale_val = QLabel("15")
        self.ela_scale_slider.valueChanged.connect(lambda v: self.ela_scale_val.setText(str(v)))
        ctrl_layout.addWidget(self.ela_scale_slider, 1, 1)
        ctrl_layout.addWidget(self.ela_scale_val, 1, 2)

        self.ela_autoscale = QCheckBox("Auto-Scale (255 / max_diff)")
        self.ela_autoscale.toggled.connect(lambda chk: self.ela_scale_slider.setEnabled(not chk))
        ctrl_layout.addWidget(self.ela_autoscale, 2, 0, 1, 2)

        btn_row = QHBoxLayout()
        self.btn_run_ela = QPushButton("Run ELA")
        self.btn_run_ela.clicked.connect(self._run_ela)
        btn_row.addWidget(self.btn_run_ela)

        self.btn_save_ela = QPushButton("Simpan Hasil ELA (.png)")
        self.btn_save_ela.clicked.connect(self._save_ela_png)
        btn_row.addWidget(self.btn_save_ela)
        ctrl_layout.addLayout(btn_row, 2, 2)

        layout.addWidget(ctrl_box)

        self.ela_preview = ImageLabel("Klik 'Run ELA' untuk melihat peta Error Level Analysis")
        layout.addWidget(self.ela_preview, stretch=1)

        hint = QLabel(
            "Interpretasi: Gambar asli memiliki tingkat error seragam sesuai tekstur. "
            "Area hasil splicing/editan memiliki kecerahan error yang kontras (lebih terang/gelap)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(hint)

        self.tabs.addTab(tab, "2. Error Level Analysis (ELA)")

    def _build_ghost_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        ctrl_box = QGroupBox("Parameter JPEG Ghost (Farid, 2009)")
        ctrl_layout = QHBoxLayout(ctrl_box)

        ctrl_layout.addWidget(QLabel("Q Min:"))
        self.ghost_qmin = QSpinBox()
        self.ghost_qmin.setRange(10, 90)
        self.ghost_qmin.setValue(15)
        ctrl_layout.addWidget(self.ghost_qmin)

        ctrl_layout.addWidget(QLabel("Q Max:"))
        self.ghost_qmax = QSpinBox()
        self.ghost_qmax.setRange(20, 100)
        self.ghost_qmax.setValue(95)
        ctrl_layout.addWidget(self.ghost_qmax)

        ctrl_layout.addWidget(QLabel("Step:"))
        self.ghost_step = QSpinBox()
        self.ghost_step.setRange(1, 20)
        self.ghost_step.setValue(5)
        ctrl_layout.addWidget(self.ghost_step)

        ctrl_layout.addWidget(QLabel("Block Size:"))
        self.ghost_block = QComboBox()
        self.ghost_block.addItems(["8", "16", "32"])
        self.ghost_block.setCurrentText("16")
        ctrl_layout.addWidget(self.ghost_block)

        self.ghost_colormap = QCheckBox("Colormap JET")
        self.ghost_colormap.setChecked(True)
        ctrl_layout.addWidget(self.ghost_colormap)

        self.btn_run_ghost = QPushButton("Generate Ghost Maps")
        self.btn_run_ghost.clicked.connect(self._run_ghost)
        ctrl_layout.addWidget(self.btn_run_ghost)

        self.btn_save_ghost = QPushButton("Simpan Peta (.png)")
        self.btn_save_ghost.clicked.connect(self._save_ghost_png)
        ctrl_layout.addWidget(self.btn_save_ghost)

        layout.addWidget(ctrl_box)

        # Slider interaktif untuk memilih Q
        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Pilih Kualitas Q:"))
        self.ghost_q_slider = QSlider(Qt.Orientation.Horizontal)
        self.ghost_q_slider.setEnabled(False)
        self.ghost_q_slider.valueChanged.connect(self._on_ghost_slider_changed)
        slider_row.addWidget(self.ghost_q_slider, stretch=1)
        self.lbl_ghost_q = QLabel("Q = -")
        self.lbl_ghost_q.setMinimumWidth(65)
        slider_row.addWidget(self.lbl_ghost_q)
        layout.addLayout(slider_row)

        # Area tampilan utama + grid thumbnail
        ghost_split = QSplitter(Qt.Orientation.Vertical)
        self.ghost_preview = ImageLabel("Klik 'Generate Ghost Maps' untuk memindai double compression")
        ghost_split.addWidget(self.ghost_preview)

        self.ghost_grid_scroll = QScrollArea()
        self.ghost_grid_scroll.setWidgetResizable(True)
        self.ghost_grid_container = QWidget()
        self.ghost_grid_layout = QGridLayout(self.ghost_grid_container)
        self.ghost_grid_scroll.setWidget(self.ghost_grid_container)
        self.ghost_grid_scroll.setMinimumHeight(180)
        ghost_split.addWidget(self.ghost_grid_scroll)
        ghost_split.setSizes([400, 220])

        layout.addWidget(ghost_split, stretch=1)

        # Panel Statistik K-S (Slide 18)
        ks_row = QHBoxLayout()
        ks_row.addWidget(QLabel("ROI K-S (x, y, w, h):"))
        self.ks_x = QSpinBox()
        self.ks_x.setRange(0, 10000)
        self.ks_x.setValue(288)
        self.ks_y = QSpinBox()
        self.ks_y.setRange(0, 10000)
        self.ks_y.setValue(192)
        self.ks_w = QSpinBox()
        self.ks_w.setRange(8, 10000)
        self.ks_w.setValue(224)
        self.ks_h = QSpinBox()
        self.ks_h.setRange(8, 10000)
        self.ks_h.setValue(224)
        for sb in (self.ks_x, self.ks_y, self.ks_w, self.ks_h):
            ks_row.addWidget(sb)
        self.btn_calc_ks = QPushButton("Hitung K-S Statistic")
        self.btn_calc_ks.clicked.connect(self._run_ks_statistic)
        ks_row.addWidget(self.btn_calc_ks)
        self.lbl_ks_result = QLabel("K(Q): -")
        self.lbl_ks_result.setStyleSheet("color: #8fd3f4; font-weight: bold;")
        ks_row.addWidget(self.lbl_ks_result, stretch=1)
        layout.addLayout(ks_row)

        hint = QLabel(
            "Interpretasi: Normalisasi dilakukan lintas kualitas (Slide 16). Saat Q mendekati kualitas kompresi "
            "asli objek tempelan (Q1), area manipulasi tampak biru tua pekat (minimum lokal) dan K-S Statistic meningkat."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(hint)

        self.tabs.addTab(tab, "3. JPEG Ghost")

    def _populate_dataset_samples(self) -> None:
        dataset_dir = Path(__file__).resolve().parent / "dataset"
        self.combo_dataset.clear()
        if not dataset_dir.exists():
            return
        for p in sorted(dataset_dir.rglob("*.jpg")) + sorted(dataset_dir.rglob("*.jpeg")):
            rel = p.relative_to(dataset_dir)
            self.combo_dataset.addItem(str(rel), str(p))

    def _load_selected_sample(self) -> None:
        path = self.combo_dataset.currentData()
        if path:
            self._load_image(path)

    def _open_image_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Citra Uji",
            str(Path(__file__).resolve().parent / "dataset"),
            "Image Files (*.jpg *.jpeg *.png *.bmp *.webp)",
        )
        if path:
            self._load_image(path)

    def _load_image(self, path: str) -> None:
        try:
            rgb = np.array(load_rgb_image(path), dtype=np.uint8)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Gagal membuka gambar:\n{exc}")
            return

        self.current_image_path = path
        self.lbl_path.setText(path)
        self.orig_preview.set_pixmap_image(numpy_to_qpixmap(rgb))
        self.current_ela_array = None
        self.current_ghost_maps = {}
        self._run_link_signature()

    def _run_link_signature(self) -> None:
        if not self.current_image_path:
            return
        try:
            sig = extract_link_signature(self.current_image_path)
            self.current_signature = sig
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Gagal mengekstrak Link Signature:\n{exc}")
            return

        lines = [
            f"File          : {sig.file_path}",
            f"Ukuran File   : {sig.file_size_bytes:,} bytes",
            f"Dimensi       : {sig.width} x {sig.height} px ({sig.color_mode})",
            f"Format JPEG   : {'Ya' if sig.is_jpeg else 'Bukan JPEG'} ({sig.sof_type})",
            f"Estimasi Q    : {sig.estimated_quality if sig.estimated_quality is not None else 'N/A'}",
            f"Jumlah DHT    : {sig.huffman_tables_count}",
            f"Signature Hash: {sig.signature_hash}",
            "",
            "--- Urutan Marker JPEG ---",
            " -> ".join(sig.markers) if sig.markers else "(Tidak ada marker JPEG)",
            "",
            "--- Quantization Tables (DQT 8x8) ---",
        ]
        for tid, mat in sorted(sig.quantization_tables.items()):
            label = "Luminance (Y)" if tid == 0 else f"Chrominance (ID={tid})"
            lines.append(f"[{label}]")
            for row in mat:
                lines.append("  " + " ".join(f"{v:3d}" for v in row))
        if sig.exif:
            lines.append("")
            lines.append("--- EXIF Metadata ---")
            for k, v in sig.exif.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append("")
            lines.append("--- EXIF Metadata ---")
            lines.append("  (Tidak ada metadata EXIF)")

        self.sig_output.setPlainText("\n".join(lines))

    def _compare_with_other_jpeg(self) -> None:
        if not self.current_signature:
            QMessageBox.information(self, "Info", "Muat gambar JPEG utama terlebih dahulu.")
            return
        other_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih JPEG Pembanding",
            str(Path(__file__).resolve().parent / "dataset"),
            "JPEG Files (*.jpg *.jpeg)",
        )
        if not other_path:
            return
        other_sig = extract_link_signature(other_path)
        res = compare_signatures(self.current_signature, other_sig)
        msg = (
            f"Pembanding: {Path(other_path).name}\n\n"
            f"Exact Signature Match    : {res['exact_signature_match']}\n"
            f"Same Quantization Tables : {res['same_quantization_tables']}\n"
            f"Same Marker Sequence     : {res['same_marker_sequence']}\n"
            f"Estimasi Q (Utama vs Pembanding): {res['quality_a']} vs {res['quality_b']}"
        )
        QMessageBox.information(self, "Hasil Perbandingan Link Signature", msg)

    def _run_ela(self) -> None:
        if not self.current_image_path:
            QMessageBox.information(self, "Info", "Muat gambar terlebih dahulu.")
            return
        q = self.ela_q_slider.value()
        scale = None if self.ela_autoscale.isChecked() else self.ela_scale_slider.value()
        ela_arr = compute_ela(self.current_image_path, quality=q, scale=scale)
        self.current_ela_array = ela_arr
        self.ela_preview.set_pixmap_image(numpy_to_qpixmap(ela_arr))

    def _save_ela_png(self) -> None:
        if self.current_ela_array is None:
            QMessageBox.information(self, "Info", "Jalankan ELA terlebih dahulu.")
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Simpan ELA (.png)", "output_ela.png", "PNG (*.png)")
        if out_path:
            save_lossless_png(self.current_ela_array, out_path)
            QMessageBox.information(self, "Tersimpan", f"Hasil ELA disimpan ke:\n{out_path}")

    def _run_ghost(self) -> None:
        if not self.current_image_path:
            QMessageBox.information(self, "Info", "Muat gambar terlebih dahulu.")
            return
        qmin = self.ghost_qmin.value()
        qmax = self.ghost_qmax.value()
        step = self.ghost_step.value()
        if qmin >= qmax:
            QMessageBox.warning(self, "Parameter Tidak Valid", "Q Min harus lebih kecil dari Q Max.")
            return

        qualities = list(range(qmin, qmax + 1, step))
        block_size = int(self.ghost_block.currentText())
        apply_cmap = self.ghost_colormap.isChecked()

        self.btn_run_ghost.setEnabled(False)
        self.btn_run_ghost.setText("Memproses...")

        self.ghost_worker = GhostWorker(self.current_image_path, qualities, block_size, apply_cmap)
        self.ghost_worker.finished_maps.connect(self._on_ghost_finished)
        self.ghost_worker.failed.connect(self._on_ghost_failed)
        self.ghost_worker.start()

    def _on_ghost_finished(self, maps: dict, raw_maps: dict) -> None:
        self.btn_run_ghost.setEnabled(True)
        self.btn_run_ghost.setText("Generate Ghost Maps")
        self.current_ghost_maps = maps
        self.current_ghost_raw = raw_maps

        qs = sorted(maps.keys())
        self.ghost_q_slider.setEnabled(True)
        self.ghost_q_slider.setRange(0, len(qs) - 1)
        self.ghost_q_slider.setValue(0)
        self._ghost_qualities_list = qs
        self._on_ghost_slider_changed(0)
        self._populate_ghost_grid(qs)
        self.lbl_ks_result.setText("K(Q): Klik 'Hitung K-S Statistic'")

    def _run_ks_statistic(self) -> None:
        if not self.current_ghost_raw:
            QMessageBox.information(self, "Info", "Generate Ghost Maps terlebih dahulu.")
            return
        roi = (self.ks_x.value(), self.ks_y.value(), self.ks_w.value(), self.ks_h.value())
        scores = compute_ks_statistic(self.current_ghost_raw, roi)
        best_q = max(scores, key=lambda q: scores[q])
        summary = ", ".join(f"Q{q}:{v:.2f}" for q, v in sorted(scores.items()))
        self.lbl_ks_result.setText(f"Maks K(Q={best_q}) = {scores[best_q]:.3f}")
        QMessageBox.information(
            self,
            "Hasil K-S Statistic",
            f"Statistik Kolmogorov-Smirnov K(Q) untuk ROI {roi}:\n\n{summary}\n\n"
            f"Perbedaan distribusi paling signifikan pada Q = {best_q} (K = {scores[best_q]:.4f}).",
        )

    def _on_ghost_failed(self, err: str) -> None:
        self.btn_run_ghost.setEnabled(True)
        self.btn_run_ghost.setText("Generate Ghost Maps")
        QMessageBox.critical(self, "Error JPEG Ghost", err)

    def _on_ghost_slider_changed(self, idx: int) -> None:
        if not self.current_ghost_maps or not hasattr(self, "_ghost_qualities_list"):
            return
        q = self._ghost_qualities_list[idx]
        self.lbl_ghost_q.setText(f"Q = {q}")
        self.ghost_preview.set_pixmap_image(numpy_to_qpixmap(self.current_ghost_maps[q]))

    def _populate_ghost_grid(self, qs: list[int]) -> None:
        while self.ghost_grid_layout.count():
            item = self.ghost_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 5
        for i, q in enumerate(qs):
            pix = numpy_to_qpixmap(self.current_ghost_maps[q]).scaled(
                150, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            btn = QPushButton()
            btn.setToolTip(f"Klik untuk melihat Q={q}")
            box = QVBoxLayout()
            lbl_img = QLabel()
            lbl_img.setPixmap(pix)
            lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_txt = QLabel(f"Q = {q}")
            lbl_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(4, 4, 4, 4)
            cell_layout.addWidget(lbl_img)
            btn_select = QPushButton(f"Q = {q}")
            btn_select.clicked.connect(lambda _checked=False, index=i: self.ghost_q_slider.setValue(index))
            cell_layout.addWidget(btn_select)

            self.ghost_grid_layout.addWidget(cell, i // cols, i % cols)

    def _save_ghost_png(self) -> None:
        if not self.current_ghost_maps or not hasattr(self, "_ghost_qualities_list"):
            QMessageBox.information(self, "Info", "Generate Ghost Maps terlebih dahulu.")
            return
        idx = self.ghost_q_slider.value()
        q = self._ghost_qualities_list[idx]
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan JPEG Ghost (.png)", f"output_ghost_q{q}.png", "PNG (*.png)"
        )
        if out_path:
            save_lossless_png(self.current_ghost_maps[q], out_path)
            QMessageBox.information(self, "Tersimpan", f"Peta JPEG Ghost Q={q} disimpan ke:\n{out_path}")


def main() -> None:
    app = QApplication(sys.argv)
    win = ForensicsMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
