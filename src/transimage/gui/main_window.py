"""
TransImage GUI - A Qt for Python application for image conversion and GIF creation.
"""

import sys
import os
from typing import Optional, List

from PySide6.QtCore import (
    Qt, QThread, Signal, Slot, QSize, QSettings, QUrl, QTimer,
    QRect, QRectF, QPointF
)
from PySide6.QtGui import (
    QAction, QIcon, QKeySequence, QPixmap, QDesktopServices, QImage,
    QPainter, QColor, QPen, QBrush
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QProgressBar, QStatusBar,
    QListWidget, QSplitter, QFrame, QScrollArea, QSlider,
    QDialog, QDialogButtonBox, QTextEdit, QRadioButton, QButtonGroup
)

from transimage.image_collector import collect_images
from transimage.image_converter import convert_image
from transimage.gif_creator import create_gif


# Styling for the primary action button (Convert Images / Create GIF).
PRIMARY_ACTION_STYLE = """
    QPushButton {
        background-color: #5BCEFA;
        color: #1e1e1e;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #7DD8FA;
    }
    QPushButton:pressed {
        background-color: #3BBEE8;
    }
    QPushButton:disabled {
        background-color: #444;
        color: #888;
    }
"""

# Styling for the cancel button (kept red to signal a destructive action).
CANCEL_ACTION_STYLE = """
    QPushButton {
        background-color: #8a2d2d;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #9a3d3d;
    }
    QPushButton:disabled {
        background-color: #444;
        color: #888;
    }
"""


class ImageConversionWorker(QThread):
    """Background worker that converts a single image or a folder of images."""

    progress = Signal(int, int, str)   # (current, total, filename)
    finished = Signal(list, list)      # (converted_files, errors)
    error = Signal(str)

    def __init__(self, input_path: str, output_path: str, output_format: str):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.output_format = output_format
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        converted_files = []
        errors = []

        try:
            if os.path.isfile(self.input_path):
                # Single-file conversion.
                output_filename = (
                    f"{os.path.splitext(os.path.basename(self.input_path))[0]}"
                    f".{self.output_format}"
                )
                output_file_path = os.path.join(self.output_path, output_filename)
                try:
                    convert_image(self.input_path, output_file_path, self.output_format)
                    if os.path.exists(output_file_path):
                        converted_files.append(output_file_path)
                    self.progress.emit(1, 1, os.path.basename(self.input_path))
                except ValueError as e:
                    errors.append(f"{self.input_path}: {str(e)}")

            elif os.path.isdir(self.input_path):
                # Batch conversion over every supported image in the folder.
                os.makedirs(self.output_path, exist_ok=True)
                image_files = collect_images(self.input_path)
                total = len(image_files)

                for i, file_path in enumerate(image_files):
                    if self._is_cancelled:
                        break

                    output_filename = (
                        f"{os.path.splitext(os.path.basename(file_path))[0]}"
                        f".{self.output_format}"
                    )
                    output_file_path = os.path.join(self.output_path, output_filename)

                    try:
                        convert_image(file_path, output_file_path, self.output_format)
                        if os.path.exists(output_file_path):
                            converted_files.append(output_file_path)
                    except ValueError as e:
                        errors.append(f"{file_path}: {str(e)}")

                    self.progress.emit(i + 1, total, os.path.basename(file_path))
            else:
                self.error.emit(f"Input path does not exist: {self.input_path}")
                return

        except Exception as e:
            self.error.emit(str(e))
            return

        self.finished.emit(converted_files, errors)


class GIFCreationWorker(QThread):
    """Background worker that builds a GIF from images or from a video file."""

    progress = Signal(str)             # status message
    finished = Signal(str)             # output GIF path
    error = Signal(str)

    def __init__(
        self,
        input_source,
        output: str,
        fps: float = 10,
        size: Optional[tuple] = None,
        crop: Optional[tuple] = None,
        loop: int = 0,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        skip_frames: int = 1,
        colors: int = 256,
        dither: bool = True,
    ):
        super().__init__()
        self.input_source = input_source
        self.output = output
        self.fps = fps
        self.size = size
        self.crop = crop
        self.loop = loop
        self.start_time = start_time
        self.end_time = end_time
        self.skip_frames = skip_frames
        self.colors = colors
        self.dither = dither
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.progress.emit("Collecting frames...")

            if self._is_cancelled:
                return

            self.progress.emit("Creating GIF...")

            # Delegate to the transimage package.
            create_gif(
                input=self.input_source,
                output=self.output,
                fps=self.fps,
                size=self.size,
                crop=self.crop,
                loop=self.loop,
                start_time=self.start_time,
                end_time=self.end_time,
                skip_frames=self.skip_frames,
                colors=self.colors,
                dither=self.dither,
            )

            if not self._is_cancelled:
                self.finished.emit(self.output)

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class DropLineEdit(QLineEdit):
    """QLineEdit that accepts files or folders dropped onto it."""

    def __init__(self, parent=None, accept_dirs=True, accept_files=True):
        super().__init__(parent)
        self.accept_dirs = accept_dirs
        self.accept_files = accept_files
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path) and self.accept_dirs:
                self.setText(path)
            elif os.path.isfile(path) and self.accept_files:
                self.setText(path)
            event.acceptProposedAction()


class ImagePreviewWidget(QWidget):
    """Displays a scaled preview of an image or video frame.

    Optionally renders an interactive crop overlay whose left / top / right /
    bottom edges can be dragged independently. Crop values are always stored
    in source-image pixel coordinates so that they survive scrubbing (every
    video frame has the same source dimensions).
    """

    # (left, top, right, bottom) in source pixels
    crop_changed = Signal(int, int, int, int)

    _NONE = 0
    _LEFT = 1
    _RIGHT = 2
    _TOP = 4
    _BOTTOM = 8

    _HIT_TOLERANCE = 8
    _MIN_CROP_SIZE = 4
    _HANDLE_SIZE = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self._message = "No preview available"
        self._display_rect = QRect()

        # Crop state (source pixel coordinates)
        self._crop_enabled = False
        self._crop_ltrb = (0, 0, 0, 0)

        # Drag state
        self._drag_flags = self._NONE
        self._drag_start_pos: Optional[QPointF] = None
        self._drag_start_ltrb = None

        self.setMinimumSize(200, 150)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # --- Public API -

    def set_image(self, path: str):
        if not path or not os.path.isfile(path):
            self.clear()
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.set_message("Cannot load image")
            return
        self.set_pixmap(pixmap)

    def set_pixmap(self, pixmap: QPixmap):
        """Display a QPixmap directly (used for video scrub frames).

        Crucially this does NOT reset the crop rectangle, so scrubbing never
        interferes with the user's crop selection.
        """
        if pixmap is None or pixmap.isNull():
            self.clear()
            return
        self._pixmap = pixmap
        self._message = ""

        # Clamp existing crop values to the new pixmap size (matters only if
        # the user loads a differently-sized video while crop is enabled).
        if self._crop_enabled:
            old = self._crop_ltrb
            self._crop_ltrb = self._clamp_ltrb(
                self._crop_ltrb, pixmap.width(), pixmap.height()
            )
            if old != self._crop_ltrb:
                self.crop_changed.emit(*self._crop_ltrb)

        self._update_display_rect()
        self.update()

    def clear(self):
        self._pixmap = None
        self._message = "No preview available"
        self.update()

    def set_message(self, text: str):
        """Show a text message instead of a pixmap (e.g. missing OpenCV)."""
        self._pixmap = None
        self._message = text
        self.update()

    def set_crop_enabled(self, enabled: bool):
        if self._crop_enabled == enabled:
            return
        self._crop_enabled = enabled
        self.update()

    def is_crop_enabled(self) -> bool:
        return self._crop_enabled

    def set_crop_ltrb(self, l: int, t: int, r: int, b: int):
        """Set crop from edge offsets. Values are clamped to the pixmap."""
        original = (int(l), int(t), int(r), int(b))
        if self._pixmap is not None:
            self._crop_ltrb = self._clamp_ltrb(
                original, self._pixmap.width(), self._pixmap.height()
            )
        else:
            self._crop_ltrb = tuple(max(0, v) for v in original)

        # If clamping changed the values, tell listeners so the spin boxes
        # can be brought back in sync.
        if self._crop_ltrb != original:
            self.crop_changed.emit(*self._crop_ltrb)
        self.update()

    def get_crop_ltrb(self):
        return self._crop_ltrb

    # --- Helpers --

    @staticmethod
    def _clamp_ltrb(ltrb, w: int, h: int):
        l, t, r, b = (int(v) for v in ltrb)
        l = max(0, min(l, w - 1))
        t = max(0, min(t, h - 1))
        r = max(0, min(r, w - 1))
        b = max(0, min(b, h - 1))
        if w - l - r < 1:
            r = max(0, w - l - 1)
            if w - l - r < 1:
                l = max(0, w - r - 1)
        if h - t - b < 1:
            b = max(0, h - t - 1)
            if h - t - b < 1:
                t = max(0, h - b - 1)
        return (l, t, r, b)

    def _update_display_rect(self):
        """Where the scaled pixmap is drawn, in widget coordinates."""
        if self._pixmap is None:
            self._display_rect = QRect()
            return
        avail = self.rect().adjusted(1, 1, -1, -1)   # 1 px inner border
        pw, ph = self._pixmap.width(), self._pixmap.height()
        if pw <= 0 or ph <= 0 or avail.width() <= 0 or avail.height() <= 0:
            self._display_rect = QRect()
            return
        scale = min(avail.width() / pw, avail.height() / ph)
        dw = max(1, int(pw * scale))
        dh = max(1, int(ph * scale))
        dx = avail.x() + (avail.width() - dw) // 2
        dy = avail.y() + (avail.height() - dh) // 2
        self._display_rect = QRect(dx, dy, dw, dh)

    def _crop_rect_in_display(self) -> QRectF:
        if self._pixmap is None or self._display_rect.isEmpty():
            return QRectF()
        l, t, r, b = self._crop_ltrb
        pw, ph = self._pixmap.width(), self._pixmap.height()
        sx = self._display_rect.width() / pw
        sy = self._display_rect.height() / ph
        return QRectF(
            self._display_rect.x() + l * sx,
            self._display_rect.y() + t * sy,
            (pw - l - r) * sx,
            (ph - t - b) * sy,
        )

    def _display_to_source(self, x: float, y: float):
        if self._display_rect.isEmpty() or self._pixmap is None:
            return (0.0, 0.0)
        sx = self._pixmap.width() / self._display_rect.width()
        sy = self._pixmap.height() / self._display_rect.height()
        return ((x - self._display_rect.x()) * sx,
                (y - self._display_rect.y()) * sy)

    # --- Painting -

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        if self._pixmap is None:
            painter.setPen(QColor("#888"))
            painter.drawText(self.rect(),
                             Qt.AlignmentFlag.AlignCenter, self._message)
        else:
            self._update_display_rect()
            if not self._display_rect.isEmpty():
                scaled = self._pixmap.scaled(
                    self._display_rect.size(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(self._display_rect.topLeft(), scaled)
                if self._crop_enabled:
                    self._paint_crop_overlay(painter)

        # Border
        painter.setPen(QColor("#444"))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def _paint_crop_overlay(self, painter: QPainter):
        crop_disp = self._crop_rect_in_display()
        if crop_disp.isEmpty():
            return
        disp = QRectF(self._display_rect)

        # Dim everything outside the crop region.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 140))
        painter.drawRect(QRectF(disp.x(), disp.y(),
                                disp.width(), crop_disp.y() - disp.y()))
        painter.drawRect(QRectF(disp.x(), crop_disp.bottom(),
                                disp.width(), disp.bottom() - crop_disp.bottom()))
        painter.drawRect(QRectF(disp.x(), crop_disp.y(),
                                crop_disp.x() - disp.x(), crop_disp.height()))
        painter.drawRect(QRectF(crop_disp.right(), crop_disp.y(),
                                disp.right() - crop_disp.right(),
                                crop_disp.height()))

        # Crop border
        pen = QPen(QColor("#5BCEFA"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(crop_disp)

        # Handles (corners + edge midpoints)
        hs = self._HANDLE_SIZE
        painter.setPen(QPen(QColor("#1e1e1e"), 1))
        painter.setBrush(QBrush(QColor("#5BCEFA")))
        cx = crop_disp.center().x()
        cy = crop_disp.center().y()
        for hx, hy in (
            (crop_disp.left(), crop_disp.top()),
            (cx, crop_disp.top()),
            (crop_disp.right(), crop_disp.top()),
            (crop_disp.left(), cy),
            (crop_disp.right(), cy),
            (crop_disp.left(), crop_disp.bottom()),
            (cx, crop_disp.bottom()),
            (crop_disp.right(), crop_disp.bottom()),
        ):
            painter.drawRect(QRectF(hx - hs / 2, hy - hs / 2, hs, hs))

    # --- Events ---

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display_rect()
        self.update()

    def _hit_test(self, pos) -> int:
        if not self._crop_enabled or self._pixmap is None:
            return self._NONE
        crop_disp = self._crop_rect_in_display()
        if crop_disp.isEmpty():
            return self._NONE
        tol = self._HIT_TOLERANCE
        x, y = pos.x(), pos.y()
        flags = self._NONE
        if (abs(x - crop_disp.left()) <= tol
                and crop_disp.top() - tol <= y <= crop_disp.bottom() + tol):
            flags |= self._LEFT
        if (abs(x - crop_disp.right()) <= tol
                and crop_disp.top() - tol <= y <= crop_disp.bottom() + tol):
            flags |= self._RIGHT
        if (abs(y - crop_disp.top()) <= tol
                and crop_disp.left() - tol <= x <= crop_disp.right() + tol):
            flags |= self._TOP
        if (abs(y - crop_disp.bottom()) <= tol
                and crop_disp.left() - tol <= x <= crop_disp.right() + tol):
            flags |= self._BOTTOM
        return flags

    def _update_cursor_for_flags(self, flags: int):
        if flags == self._NONE:
            self.unsetCursor()
        elif flags in (self._LEFT | self._TOP, self._RIGHT | self._BOTTOM):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif flags in (self._RIGHT | self._TOP, self._LEFT | self._BOTTOM):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif flags in (self._LEFT, self._RIGHT):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif flags in (self._TOP, self._BOTTOM):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        if not self._crop_enabled or self._pixmap is None:
            return
        flags = self._hit_test(event.position())
        if flags != self._NONE:
            self._drag_flags = flags
            self._drag_start_pos = event.position()
            self._drag_start_ltrb = self._crop_ltrb
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_flags != self._NONE and self._drag_start_pos is not None:
            self._apply_drag(event.position())
            event.accept()
            return
        if self._crop_enabled:
            self._update_cursor_for_flags(self._hit_test(event.position()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        if self._drag_flags != self._NONE:
            self._drag_flags = self._NONE
            self._drag_start_pos = None
            self._drag_start_ltrb = None
            event.accept()

    def _apply_drag(self, pos):
        if (self._pixmap is None or self._drag_start_pos is None
                or self._drag_start_ltrb is None):
            return

        x0, y0 = self._display_to_source(self._drag_start_pos.x(),
                                         self._drag_start_pos.y())
        x1, y1 = self._display_to_source(pos.x(), pos.y())
        dx = int(round(x1 - x0))
        dy = int(round(y1 - y0))

        l, t, r, b = self._drag_start_ltrb
        pw, ph = self._pixmap.width(), self._pixmap.height()
        min_size = self._MIN_CROP_SIZE

        if self._drag_flags & self._LEFT:
            max_l = pw - r - min_size
            l = max(0, min(l + dx, max_l))
        if self._drag_flags & self._RIGHT:
            max_r = pw - l - min_size
            r = max(0, min(r - dx, max_r))
        if self._drag_flags & self._TOP:
            max_t = ph - b - min_size
            t = max(0, min(t + dy, max_t))
        if self._drag_flags & self._BOTTOM:
            max_b = ph - t - min_size
            b = max(0, min(b - dy, max_b))

        new_ltrb = (l, t, r, b)
        if new_ltrb != self._crop_ltrb:
            self._crop_ltrb = new_ltrb
            self.update()
            self.crop_changed.emit(*new_ltrb)


class ImageConversionTab(QWidget):
    """Tab for image format conversion (single file or batch)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        # Wrap everything in a scroll area so the layout can't be squeezed.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- Input group ---
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout(input_group)

        input_path_layout = QHBoxLayout()
        input_path_layout.addWidget(QLabel("Source:"))
        self._input_path_edit = DropLineEdit()
        self._input_path_edit.setPlaceholderText(
            "Select an image file or folder containing images..."
        )
        input_path_layout.addWidget(self._input_path_edit, 1)

        self._browse_input_btn = QPushButton("Browse...")
        input_path_layout.addWidget(self._browse_input_btn)

        self._browse_folder_btn = QPushButton("Folder...")
        input_path_layout.addWidget(self._browse_folder_btn)

        input_layout.addLayout(input_path_layout)

        # Preview + file list side by side, user can drag the divider.
        preview_splitter = QSplitter(Qt.Orientation.Horizontal)

        self._preview = ImagePreviewWidget()
        self._preview.setMinimumWidth(250)
        preview_splitter.addWidget(self._preview)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        preview_splitter.addWidget(self._file_list)

        preview_splitter.setSizes([250, 400])
        input_layout.addWidget(preview_splitter)

        main_layout.addWidget(input_group)

        # --- Output group ---
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)

        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("Destination:"))
        self._output_path_edit = DropLineEdit(accept_files=False)
        self._output_path_edit.setPlaceholderText(
            "Select output folder for converted images..."
        )
        output_path_layout.addWidget(self._output_path_edit, 1)

        self._browse_output_btn = QPushButton("Browse...")
        output_path_layout.addWidget(self._browse_output_btn)

        output_layout.addLayout(output_path_layout)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Format:"))

        self._format_combo = QComboBox()
        self._format_combo.addItems(["png", "jpg", "bmp", "webp"])
        format_layout.addWidget(self._format_combo)

        format_layout.addSpacing(20)

        format_layout.addWidget(QLabel("JPG Quality:"))
        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(1, 100)
        self._quality_spin.setValue(95)
        format_layout.addWidget(self._quality_spin)

        format_layout.addStretch()
        output_layout.addLayout(format_layout)

        self._keep_original_check = QCheckBox("Keep original files when format matches")
        self._keep_original_check.setChecked(True)
        output_layout.addWidget(self._keep_original_check)

        main_layout.addWidget(output_group)

        # --- Progress group ---
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("Ready")
        progress_layout.addWidget(self._progress_label)

        main_layout.addWidget(progress_group)

        # --- Action buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._convert_btn = QPushButton("Convert Images")
        self._convert_btn.setMinimumWidth(150)
        self._convert_btn.setStyleSheet(PRIMARY_ACTION_STYLE)
        button_layout.addWidget(self._convert_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setStyleSheet(CANCEL_ACTION_STYLE)
        button_layout.addWidget(self._cancel_btn)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

        scroll.setWidget(content_widget)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _connect_signals(self):
        self._browse_input_btn.clicked.connect(self._browse_input_file)
        self._browse_folder_btn.clicked.connect(self._browse_input_folder)
        self._browse_output_btn.clicked.connect(self._browse_output_folder)
        self._input_path_edit.textChanged.connect(self._on_input_changed)
        self._file_list.itemSelectionChanged.connect(self._on_file_selected)
        self._convert_btn.clicked.connect(self._start_conversion)
        self._cancel_btn.clicked.connect(self._cancel_conversion)
        self._format_combo.currentTextChanged.connect(self._on_format_changed)

    def _browse_input_file(self):
        file_filter = (
            "Images (*.jpg *.jpeg *.png *.bmp *.webp);;"
            "All Files (*.*)"
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image File", "", file_filter
        )
        if path:
            self._input_path_edit.setText(path)

    def _browse_input_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if path:
            self._input_path_edit.setText(path)

    def _browse_output_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self._output_path_edit.setText(path)

    def _on_input_changed(self, text: str):
        # Refresh the file list and preview when the source path changes.
        self._file_list.clear()
        self._preview.clear()

        if not text or not os.path.exists(text):
            return

        if os.path.isfile(text):
            self._file_list.addItem(os.path.basename(text))
            self._preview.set_image(text)
        elif os.path.isdir(text):
            try:
                images = collect_images(text)
                for img in images:
                    self._file_list.addItem(os.path.basename(img))
                if images:
                    self._preview.set_image(images[0])
            except ValueError:
                pass

    def _on_file_selected(self):
        items = self._file_list.selectedItems()
        if not items:
            return

        input_path = self._input_path_edit.text()
        if os.path.isdir(input_path):
            file_path = os.path.join(input_path, items[0].text())
            self._preview.set_image(file_path)

    def _on_format_changed(self, fmt: str):
        # JPG quality only makes sense when the target is JPG.
        self._quality_spin.setEnabled(fmt.lower() == "jpg")

    def _validate_inputs(self) -> bool:
        input_path = self._input_path_edit.text().strip()
        output_path = self._output_path_edit.text().strip()

        if not input_path:
            QMessageBox.warning(self, "Validation Error",
                                "Please select an input file or folder.")
            return False

        if not os.path.exists(input_path):
            QMessageBox.warning(self, "Validation Error",
                                f"Input path does not exist:\n{input_path}")
            return False

        if not output_path:
            QMessageBox.warning(self, "Validation Error",
                                "Please select an output folder.")
            return False

        return True

    def _start_conversion(self):
        if not self._validate_inputs():
            return

        input_path = self._input_path_edit.text().strip()
        output_path = self._output_path_edit.text().strip()
        output_format = self._format_combo.currentText()

        os.makedirs(output_path, exist_ok=True)

        self._set_controls_enabled(False)
        self._progress_bar.setValue(0)
        self._progress_label.setText("Starting conversion...")

        self._worker = ImageConversionWorker(input_path, output_path, output_format)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_conversion(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._progress_label.setText("Cancelling...")

    def _set_controls_enabled(self, enabled: bool):
        self._convert_btn.setEnabled(enabled)
        self._cancel_btn.setEnabled(not enabled)
        self._input_path_edit.setEnabled(enabled)
        self._output_path_edit.setEnabled(enabled)
        self._format_combo.setEnabled(enabled)
        self._browse_input_btn.setEnabled(enabled)
        self._browse_folder_btn.setEnabled(enabled)
        self._browse_output_btn.setEnabled(enabled)

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, filename: str):
        if total > 0:
            progress = int((current / total) * 100)
            self._progress_bar.setValue(progress)
        self._progress_label.setText(f"Converting: {filename} ({current}/{total})")

    @Slot(list, list)
    def _on_finished(self, converted: List[str], errors: List[str]):
        self._set_controls_enabled(True)
        self._progress_bar.setValue(100)

        if errors:
            error_msg = "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n... and {len(errors) - 10} more errors"

            QMessageBox.warning(
                self, "Conversion Completed with Errors",
                f"Successfully converted {len(converted)} image(s).\n\n"
                f"Errors ({len(errors)}):\n{error_msg}"
            )
            self._progress_label.setText(
                f"Completed: {len(converted)} converted, {len(errors)} errors"
            )
        else:
            QMessageBox.information(
                self, "Conversion Complete",
                f"Successfully converted {len(converted)} image(s)."
            )
            self._progress_label.setText(f"Completed: {len(converted)} images converted")

    @Slot(str)
    def _on_error(self, message: str):
        self._set_controls_enabled(True)
        self._progress_bar.setValue(0)
        self._progress_label.setText("Error occurred")
        QMessageBox.critical(self, "Conversion Error", message)

    # -- Persistence --

    def save_settings(self, settings: QSettings):
        settings.setValue("conv_format", self._format_combo.currentText())
        settings.setValue("conv_quality", self._quality_spin.value())
        settings.setValue("conv_keep_original", self._keep_original_check.isChecked())
        settings.setValue("conv_output_path", self._output_path_edit.text())

    def load_settings(self, settings: QSettings):
        fmt = settings.value("conv_format", "png", type=str)
        idx = self._format_combo.findText(fmt)
        if idx >= 0:
            self._format_combo.setCurrentIndex(idx)

        self._quality_spin.setValue(settings.value("conv_quality", 95, type=int))
        self._keep_original_check.setChecked(
            settings.value("conv_keep_original", True, type=bool)
        )

        out = settings.value("conv_output_path", "", type=str)
        if out and os.path.isdir(out):
            self._output_path_edit.setText(out)


class GIFCreationTab(QWidget):
    """Tab for GIF creation from image files or from a video."""

    # Comparison tolerance for "is the FPS the same as the detected value".
    _FPS_MATCH_EPSILON = 0.01

    # Divisors used to build the size preset list from a source resolution.
    _SIZE_PRESET_DIVISORS = (2, 3, 4, 5, 6, 8, 10)
    # Don't offer presets smaller than this many pixels on either axis.
    _SIZE_PRESET_MIN_PIXELS = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._input_files: List[str] = []

        # Guards the spin-box <-> preview crop sync loop.
        self._updating_crop = False

        # Video scrubber state
        self._video_capture = None
        self._video_fps = 0.0
        self._video_total_frames = 0
        self._video_duration_ms = 0
        self._pending_scrub_ms = 0

        # Native FPS of the currently loaded video (0 if none / not video mode).
        self._detected_video_fps = 0.0

        # Source resolution detected from video or first image (0 = unknown).
        self._source_width = 0
        self._source_height = 0

        # Debounce: avoid decoding a frame on every single slider tick
        # while the user is dragging.
        self._scrub_timer = QTimer(self)
        self._scrub_timer.setSingleShot(True)
        self._scrub_timer.setInterval(200)
        self._scrub_timer.timeout.connect(self._apply_scrub_seek)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- Input group ---
        input_group = QGroupBox("Input Source")
        input_layout = QVBoxLayout(input_group)

        # Two mutually exclusive modes: video (default) or files.
        type_layout = QHBoxLayout()
        self._input_type_group = QButtonGroup(self)

        self._from_video_radio = QRadioButton("From Video")
        self._from_video_radio.setChecked(True)
        self._input_type_group.addButton(self._from_video_radio, 0)
        type_layout.addWidget(self._from_video_radio)

        self._from_files_radio = QRadioButton("From Files")
        self._input_type_group.addButton(self._from_files_radio, 1)
        type_layout.addWidget(self._from_files_radio)

        type_layout.addStretch()
        input_layout.addLayout(type_layout)

        input_path_layout = QHBoxLayout()
        input_path_layout.addWidget(QLabel("Source:"))
        self._input_path_edit = DropLineEdit()
        self._input_path_edit.setPlaceholderText("Select video file...")
        input_path_layout.addWidget(self._input_path_edit, 1)

        self._browse_input_btn = QPushButton("Browse...")
        input_path_layout.addWidget(self._browse_input_btn)

        self._add_files_btn = QPushButton("Add Files...")
        self._add_files_btn.setVisible(False)
        input_path_layout.addWidget(self._add_files_btn)

        input_layout.addLayout(input_path_layout)

        # File list + file-related buttons are only visible in "From Files" mode.
        self._files_list = QListWidget()
        self._files_list.setVisible(False)
        self._files_list.setMaximumHeight(120)
        input_layout.addWidget(self._files_list)

        self._file_buttons_layout = QHBoxLayout()
        self._clear_files_btn = QPushButton("Clear All")
        self._clear_files_btn.setVisible(False)
        self._file_buttons_layout.addWidget(self._clear_files_btn)
        self._remove_file_btn = QPushButton("Remove Selected")
        self._remove_file_btn.setVisible(False)
        self._file_buttons_layout.addWidget(self._remove_file_btn)
        self._file_buttons_layout.addStretch()
        input_layout.addLayout(self._file_buttons_layout)

        self._preview = ImagePreviewWidget()
        self._preview.setMinimumHeight(220)
        self._preview.setMaximumHeight(320)
        input_layout.addWidget(self._preview)

        main_layout.addWidget(input_group)

        # --- Video-only settings group ---
        # Placed above GIF Settings so that, in video mode, the
        # video-specific controls appear first.
        self._video_settings_group = QGroupBox("Video Settings")
        video_layout = QVBoxLayout(self._video_settings_group)

        video_row = QHBoxLayout()

        start_time_form = QFormLayout()
        start_time_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        self._start_time_spin = QDoubleSpinBox()
        self._start_time_spin.setRange(0, 99999)
        self._start_time_spin.setValue(0)
        self._start_time_spin.setSuffix(" s")
        start_time_form.addRow("Start Time:", self._start_time_spin)
        video_row.addLayout(start_time_form)

        end_time_form = QFormLayout()
        end_time_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        self._end_time_spin = QDoubleSpinBox()
        self._end_time_spin.setRange(0, 99999)
        self._end_time_spin.setValue(0)
        self._end_time_spin.setSpecialValueText("End")
        self._end_time_spin.setSuffix(" s")
        end_time_form.addRow("End Time:", self._end_time_spin)
        video_row.addLayout(end_time_form)

        # Skip Frames with a small "(default 1)" hint next to the spin box.
        skip_frames_form = QFormLayout()
        skip_frames_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        skip_frames_row = QHBoxLayout()
        self._skip_frames_spin = QSpinBox()
        self._skip_frames_spin.setRange(1, 100)
        self._skip_frames_spin.setValue(1)
        skip_frames_row.addWidget(self._skip_frames_spin)
        skip_frames_default = QLabel("(default 1)")
        skip_frames_default.setStyleSheet("color: #888; font-size: 11px;")
        skip_frames_row.addWidget(skip_frames_default)
        skip_frames_row.addStretch()
        skip_frames_form.addRow("Skip Frames:", skip_frames_row)
        video_row.addLayout(skip_frames_form)

        video_row.addStretch()
        video_layout.addLayout(video_row)

        # Quick reminder about how Skip Frames interacts with Frame Rate.
        # Detailed documentation lives in Help -> TransImage Help (F1).
        self._skip_frames_info = QLabel(
            "Skip Frames drops source frames to shrink the GIF. To keep the "
            "playback speed close to the original, set the output Frame Rate "
            "using the ratio of the video's FPS to Skip Frames:\n"
            "    output fps  =  video fps  /  skip frames\n"
            "For example, a 30 fps video with Skip Frames = 2 means you need to set "
            "Frame Rate to 15 fps. See Help (F1) for more detail."
        )
        self._skip_frames_info.setWordWrap(True)
        self._skip_frames_info.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border-left: 3px solid #5BCEFA;
                padding: 8px 12px;
                color: #aaa;
                font-size: 11px;
            }
        """)
        video_layout.addWidget(self._skip_frames_info)

        # --- Video scrubber ---
        # Lets the user seek through the video and preview any frame.
        scrubber_header = QLabel("Scrubber")
        scrubber_header.setStyleSheet("color: #F5A9B8; font-weight: bold;")
        video_layout.addWidget(scrubber_header)

        self._scrubber = QSlider(Qt.Orientation.Horizontal)
        self._scrubber.setRange(0, 0)
        self._scrubber.setEnabled(False)
        self._scrubber.setTracking(True)
        video_layout.addWidget(self._scrubber)

        scrubber_row = QHBoxLayout()

        self._set_start_btn = QPushButton("Set Start")
        self._set_start_btn.setEnabled(False)
        scrubber_row.addWidget(self._set_start_btn)

        self._set_end_btn = QPushButton("Set End")
        self._set_end_btn.setEnabled(False)
        scrubber_row.addWidget(self._set_end_btn)

        scrubber_row.addStretch()

        self._scrubber_time_label = QLabel("--:-- / --:--")
        self._scrubber_time_label.setStyleSheet("color: #aaa; font-size: 11px;")
        scrubber_row.addWidget(self._scrubber_time_label)

        video_layout.addLayout(scrubber_row)

        self._video_settings_group.setVisible(True)
        main_layout.addWidget(self._video_settings_group)

        # --- GIF settings group ---
        settings_group = QGroupBox("GIF Settings")
        settings_layout = QHBoxLayout(settings_group)

        left_form = QFormLayout()
        left_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._fps_spin = QDoubleSpinBox()
        self._fps_spin.setRange(0.1, 60.0)
        self._fps_spin.setValue(10.0)
        self._fps_spin.setSingleStep(0.5)
        self._fps_spin.setDecimals(3)
        self._fps_spin.setSuffix(" fps")
        left_form.addRow("Frame Rate:", self._fps_spin)

        # Hint shown under the Frame Rate field when the user has changed the
        # value away from the video's native frame rate. Hidden otherwise.
        self._detected_fps_hint = QLabel("")
        self._detected_fps_hint.setStyleSheet(
            "color: #888; font-size: 11px; padding-left: 4px;"
        )
        self._detected_fps_hint.setVisible(False)
        left_form.addRow("", self._detected_fps_hint)

        self._loop_spin = QSpinBox()
        self._loop_spin.setRange(0, 1000)
        self._loop_spin.setValue(0)
        self._loop_spin.setSpecialValueText("Infinite")
        left_form.addRow("Loop Count:", self._loop_spin)

        self._colors_spin = QSpinBox()
        self._colors_spin.setRange(2, 256)
        self._colors_spin.setValue(256)
        left_form.addRow("Colors:", self._colors_spin)

        self._dither_check = QCheckBox("Enable Dithering")
        self._dither_check.setChecked(True)
        left_form.addRow("", self._dither_check)

        settings_layout.addLayout(left_form)

        right_form = QFormLayout()
        right_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # --- Size: preset list (default) OR custom typed values ---
        self._size_mode_group = QButtonGroup(self)
        self._size_preset_radio = QRadioButton("Preset")
        self._size_preset_radio.setChecked(True)
        self._size_preset_radio.setToolTip(
            "Pick a scaled-down multiple of the source resolution."
        )
        self._size_custom_radio = QRadioButton("Custom")
        self._size_custom_radio.setToolTip(
            "Type an exact Width x Height. Set both to Auto to keep the "
            "original size."
        )
        self._size_mode_group.addButton(self._size_preset_radio, 0)
        self._size_mode_group.addButton(self._size_custom_radio, 1)

        size_mode_layout = QHBoxLayout()
        size_mode_layout.addWidget(self._size_preset_radio)
        size_mode_layout.addWidget(self._size_custom_radio)
        size_mode_layout.addStretch()
        right_form.addRow("Size Mode:", size_mode_layout)

        # Preset combo (default when a source resolution is known).
        self._size_preset_combo = QComboBox()
        self._size_preset_combo.addItem("Original", None)

        # Custom W x H row (hidden until the Custom radio is chosen).
        self._custom_size_widget = QWidget()
        custom_size_layout = QHBoxLayout(self._custom_size_widget)
        custom_size_layout.setContentsMargins(0, 0, 0, 0)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(0, 4096)
        self._width_spin.setValue(0)
        self._width_spin.setSpecialValueText("Auto")
        custom_size_layout.addWidget(self._width_spin)
        custom_size_layout.addWidget(QLabel("x"))
        self._height_spin = QSpinBox()
        self._height_spin.setRange(0, 4096)
        self._height_spin.setValue(0)
        self._height_spin.setSpecialValueText("Auto")
        custom_size_layout.addWidget(self._height_spin)
        self._custom_size_widget.setVisible(False)

        # Container holding both the combo and the custom row; only one is
        # ever visible at a time.
        size_stack = QWidget()
        size_stack_layout = QHBoxLayout(size_stack)
        size_stack_layout.setContentsMargins(0, 0, 0, 0)
        size_stack_layout.addWidget(self._size_preset_combo, 1)
        size_stack_layout.addWidget(self._custom_size_widget)
        right_form.addRow("Size:", size_stack)

        # Crop: L / T / R / B pixel counts, all 0 = no crop.
        crop_layout = QHBoxLayout()
        self._crop_left = QSpinBox()
        self._crop_left.setRange(0, 1000)
        self._crop_left.setPrefix("L:")
        crop_layout.addWidget(self._crop_left)
        self._crop_top = QSpinBox()
        self._crop_top.setRange(0, 1000)
        self._crop_top.setPrefix("T:")
        crop_layout.addWidget(self._crop_top)
        self._crop_right = QSpinBox()
        self._crop_right.setRange(0, 1000)
        self._crop_right.setPrefix("R:")
        crop_layout.addWidget(self._crop_right)
        self._crop_bottom = QSpinBox()
        self._crop_bottom.setRange(0, 1000)
        self._crop_bottom.setPrefix("B:")
        crop_layout.addWidget(self._crop_bottom)
        right_form.addRow("Crop (LTRB):", crop_layout)

        self._crop_overlay_check = QCheckBox("Enable interactive crop overlay on preview")
        self._crop_overlay_check.setToolTip(
            "Drag the edges of the highlighted rectangle on the preview to set the "
            "crop. The LTRB values above stay in sync automatically."
        )
        right_form.addRow("", self._crop_overlay_check)

        settings_layout.addLayout(right_form)

        main_layout.addWidget(settings_group)

        # --- Output group ---
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)

        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("Output GIF:"))
        self._output_path_edit = QLineEdit()
        self._output_path_edit.setPlaceholderText("Select output GIF file path...")
        output_path_layout.addWidget(self._output_path_edit, 1)

        self._browse_output_btn = QPushButton("Browse...")
        output_path_layout.addWidget(self._browse_output_btn)

        output_layout.addLayout(output_path_layout)

        main_layout.addWidget(output_group)

        # --- Progress group ---
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)   # busy/indeterminate
        self._progress_bar.setVisible(False)
        progress_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("Ready")
        progress_layout.addWidget(self._progress_label)

        main_layout.addWidget(progress_group)

        # --- Action buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._create_btn = QPushButton("Create GIF")
        self._create_btn.setMinimumWidth(150)
        self._create_btn.setStyleSheet(PRIMARY_ACTION_STYLE)
        button_layout.addWidget(self._create_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setStyleSheet(CANCEL_ACTION_STYLE)
        button_layout.addWidget(self._cancel_btn)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

        scroll.setWidget(content_widget)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _connect_signals(self):
        self._input_type_group.buttonClicked.connect(self._on_input_type_changed)
        self._browse_input_btn.clicked.connect(self._browse_input)
        self._add_files_btn.clicked.connect(self._add_files)
        self._clear_files_btn.clicked.connect(self._clear_files)
        self._remove_file_btn.clicked.connect(self._remove_selected_files)
        self._browse_output_btn.clicked.connect(self._browse_output)
        self._create_btn.clicked.connect(self._start_creation)
        self._cancel_btn.clicked.connect(self._cancel_creation)
        self._input_path_edit.textChanged.connect(self._on_input_path_changed)
        self._files_list.itemSelectionChanged.connect(self._on_file_selected)

        # Video scrubber signals.
        self._scrubber.valueChanged.connect(self._on_scrubber_moved)
        self._scrubber.sliderReleased.connect(self._apply_scrub_seek)
        self._set_start_btn.clicked.connect(self._set_start_from_scrubber)
        self._set_end_btn.clicked.connect(self._set_end_from_scrubber)

        # Crop overlay <-> spin box sync.
        self._preview.crop_changed.connect(self._on_preview_crop_changed)
        self._crop_left.valueChanged.connect(self._on_crop_spin_changed)
        self._crop_top.valueChanged.connect(self._on_crop_spin_changed)
        self._crop_right.valueChanged.connect(self._on_crop_spin_changed)
        self._crop_bottom.valueChanged.connect(self._on_crop_spin_changed)
        self._crop_overlay_check.toggled.connect(self._on_crop_overlay_toggled)

        # Frame-rate hint under the Frame Rate spin box.
        self._fps_spin.valueChanged.connect(self._update_fps_hint)

        # Size mode radio toggles which size widget is visible.
        self._size_mode_group.buttonClicked.connect(self._on_size_mode_changed)

    def _on_input_type_changed(self, button):
        # input_type == 0 -> video mode, == 1 -> files mode.
        input_type = self._input_type_group.id(button)
        is_video_mode = (input_type == 0)

        self._files_list.setVisible(not is_video_mode)
        self._add_files_btn.setVisible(not is_video_mode)
        self._clear_files_btn.setVisible(not is_video_mode)
        self._remove_file_btn.setVisible(not is_video_mode)
        self._browse_input_btn.setVisible(is_video_mode)
        self._video_settings_group.setVisible(is_video_mode)

        if is_video_mode:
            self._input_path_edit.setPlaceholderText("Select video file...")
        else:
            self._input_path_edit.setPlaceholderText(
                "Optional base path - use 'Add Files' button to add images..."
            )

        # Clear any state left over from the other mode.
        self._input_path_edit.clear()
        self._files_list.clear()
        self._input_files.clear()
        self._preview.clear()

        # Release any previously opened video and reset the scrubber.
        self._release_video_capture()
        self._scrubber.setRange(0, 0)
        self._scrubber.setEnabled(False)
        self._scrubber_time_label.setText("--:-- / --:--")
        self._set_start_btn.setEnabled(False)
        self._set_end_btn.setEnabled(False)

        # Drop any detected FPS / source resolution and hide the hint.
        self._detected_video_fps = 0.0
        self._source_width = 0
        self._source_height = 0
        self._reset_size_presets()
        self._update_fps_hint()

    def _browse_input(self):
        # Only reachable in video mode.
        file_filter = (
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm *.flv);;"
            "All Files (*.*)"
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", file_filter
        )
        if path:
            self._input_path_edit.setText(path)

    def _add_files(self):
        file_filter = (
            "Images (*.jpg *.jpeg *.png *.bmp *.webp);;"
            "All Files (*.*)"
        )
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Image Files", "", file_filter
        )

        for path in paths:
            if path not in self._input_files:
                self._input_files.append(path)
                self._files_list.addItem(os.path.basename(path))

        if self._input_files:
            first = self._input_files[0]
            self._preview.set_image(first)
            # Populate size presets from the first image's dimensions.
            pm = QPixmap(first)
            if not pm.isNull():
                self._set_source_resolution(pm.width(), pm.height())

    def _clear_files(self):
        self._input_files.clear()
        self._files_list.clear()
        self._preview.clear()
        self._set_source_resolution(0, 0)

    def _remove_selected_files(self):
        for item in self._files_list.selectedItems():
            row = self._files_list.row(item)
            self._files_list.takeItem(row)
            if row < len(self._input_files):
                del self._input_files[row]

        if self._input_files:
            first = self._input_files[0]
            self._preview.set_image(first)
            pm = QPixmap(first)
            if not pm.isNull():
                self._set_source_resolution(pm.width(), pm.height())
        else:
            self._preview.clear()
            self._set_source_resolution(0, 0)

    def _on_file_selected(self):
        items = self._files_list.selectedItems()
        if items:
            row = self._files_list.row(items[0])
            if row < len(self._input_files):
                self._preview.set_image(self._input_files[row])

    def _on_input_path_changed(self, text: str):
        # Load video metadata and enable the scrubber when a video is
        # selected. Fall back to image preview for non-video files.
        if not text or not os.path.isfile(text):
            return

        ext = os.path.splitext(text)[1].lower()
        if ext in ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'):
            self._load_video_info(text)

            # Default the output path to the same directory as the video,
            # using the video's base name and a .gif extension - but only
            # if the user hasn't already typed an output path.
            if not self._output_path_edit.text().strip():
                base, _ = os.path.splitext(text)
                self._output_path_edit.setText(base + ".gif")
        else:
            self._release_video_capture()
            self._detected_video_fps = 0.0
            self._set_source_resolution(0, 0)
            self._update_fps_hint()
            self._preview.set_image(text)

    # -- Video scrubber 

    def _load_video_info(self, path: str):
        """Open the video and set up the scrubber range."""
        self._release_video_capture()

        try:
            import cv2
        except ImportError:
            self._scrubber.setEnabled(False)
            self._set_start_btn.setEnabled(False)
            self._set_end_btn.setEnabled(False)
            self._scrubber_time_label.setText("OpenCV not installed")
            self._preview.set_message("Install opencv-python-headless to scrub")
            return

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            self._scrubber.setEnabled(False)
            self._scrubber_time_label.setText("Cannot open video")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        if fps <= 0 or total_frames <= 0:
            cap.release()
            self._scrubber.setEnabled(False)
            self._scrubber_time_label.setText("Unknown duration")
            return

        self._video_capture = cap
        self._video_fps = fps
        self._video_total_frames = total_frames
        self._video_duration_ms = int((total_frames / fps) * 1000)

        # Auto-apply the detected FPS to the GIF Frame Rate, making it the
        # default for this video. The hint label stays hidden while the spin
        # value matches the detected value.
        self._detected_video_fps = fps
        self._fps_spin.setValue(fps)
        self._update_fps_hint()

        # Populate the size preset list from the video's native resolution.
        if src_w > 0 and src_h > 0:
            self._set_source_resolution(src_w, src_h)

        self._scrubber.setRange(0, self._video_duration_ms)
        self._scrubber.setPageStep(max(1, self._video_duration_ms // 20))
        self._scrubber.setSingleStep(100)
        self._scrubber.setValue(0)
        self._scrubber.setEnabled(True)
        self._set_start_btn.setEnabled(True)
        self._set_end_btn.setEnabled(True)

        self._scrubber_time_label.setText(
            f"{self._format_duration(0)} / "
            f"{self._format_duration(self._video_duration_ms)}"
        )

        # Show the first frame immediately.
        self._pending_scrub_ms = 0
        self._apply_scrub_seek()

    def _release_video_capture(self):
        """Release the OpenCV capture if one is open."""
        if self._video_capture is not None:
            try:
                self._video_capture.release()
            except Exception:
                pass
            self._video_capture = None
        self._video_fps = 0.0
        self._video_total_frames = 0
        self._video_duration_ms = 0

    def _on_scrubber_moved(self, value: int):
        """Update the time label immediately; debounce the actual seek."""
        self._pending_scrub_ms = value
        self._scrubber_time_label.setText(
            f"{self._format_duration(value)} / "
            f"{self._format_duration(self._video_duration_ms)}"
        )
        self._scrub_timer.start()

    def _apply_scrub_seek(self):
        """Extract and display the frame at the pending scrub position."""
        self._scrub_timer.stop()

        if self._video_capture is None or self._video_fps <= 0:
            return

        try:
            import cv2
        except ImportError:
            return

        frame_num = int((self._pending_scrub_ms / 1000.0) * self._video_fps)
        frame_num = max(0, min(frame_num, self._video_total_frames - 1))

        try:
            self._video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ok, frame = self._video_capture.read()
        except Exception:
            return

        if not ok or frame is None:
            return

        # OpenCV returns BGR; QImage wants RGB.
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        # .copy() is important: QImage doesn't own the numpy buffer,
        # so without it we'd get garbage once `frame_rgb` is freed.
        qimg = QImage(
            frame_rgb.tobytes(), w, h, bytes_per_line,
            QImage.Format.Format_RGB888
        ).copy()

        self._preview.set_pixmap(QPixmap.fromImage(qimg))

    @staticmethod
    def _format_duration(ms: int) -> str:
        """Format milliseconds as 'M:SS'."""
        total_seconds = max(0, ms // 1000)
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def _set_start_from_scrubber(self):
        seconds = self._scrubber.value() / 1000.0
        self._start_time_spin.setValue(seconds)

    def _set_end_from_scrubber(self):
        seconds = self._scrubber.value() / 1000.0
        self._end_time_spin.setValue(seconds)

    def release_resources(self):
        """Called when the window closes so the codec handle is freed."""
        self._scrub_timer.stop()
        self._release_video_capture()

    # -- Size presets 

    def _set_source_resolution(self, width: int, height: int):
        """Record the source resolution and rebuild the size preset list."""
        self._source_width = max(0, int(width))
        self._source_height = max(0, int(height))
        self._populate_size_presets()

    def _reset_size_presets(self):
        self._source_width = 0
        self._source_height = 0
        self._populate_size_presets()

    def _populate_size_presets(self):
        """Fill the size preset combo from the recorded source resolution.

        For a 1920x1080 source this produces entries like:
            Original (1920x1080)
            960x540 (1/2)
            640x360 (1/3)
            480x270 (1/4)
            ...
        """
        self._size_preset_combo.blockSignals(True)
        previous_data = self._size_preset_combo.currentData()
        self._size_preset_combo.clear()

        w = self._source_width
        h = self._source_height

        if w <= 0 or h <= 0:
            self._size_preset_combo.addItem("Original", None)
        else:
            self._size_preset_combo.addItem(f"Original ({w}x{h})", None)
            for div in self._SIZE_PRESET_DIVISORS:
                pw = w // div
                ph = h // div
                if pw < self._SIZE_PRESET_MIN_PIXELS or ph < self._SIZE_PRESET_MIN_PIXELS:
                    continue
                self._size_preset_combo.addItem(
                    f"{pw}x{ph} (1/{div})", (pw, ph)
                )

        # Try to restore the previously selected preset if it's still present.
        if previous_data is not None:
            for i in range(self._size_preset_combo.count()):
                if self._size_preset_combo.itemData(i) == previous_data:
                    self._size_preset_combo.setCurrentIndex(i)
                    break

        self._size_preset_combo.blockSignals(False)

    def _on_size_mode_changed(self, button):
        is_custom = (self._size_mode_group.id(button) == 1)
        self._size_preset_combo.setVisible(not is_custom)
        self._custom_size_widget.setVisible(is_custom)

    # -- Crop overlay 

    def _on_crop_overlay_toggled(self, checked: bool):
        if checked:
            # Seed the widget from whatever is currently in the spin boxes.
            self._preview.set_crop_ltrb(
                self._crop_left.value(),
                self._crop_top.value(),
                self._crop_right.value(),
                self._crop_bottom.value(),
            )
            self._preview.set_crop_enabled(True)
        else:
            self._preview.set_crop_enabled(False)

    def _on_preview_crop_changed(self, l: int, t: int, r: int, b: int):
        """User dragged an edge on the preview -> update the spin boxes."""
        self._updating_crop = True
        try:
            self._crop_left.setValue(l)
            self._crop_top.setValue(t)
            self._crop_right.setValue(r)
            self._crop_bottom.setValue(b)
        finally:
            self._updating_crop = False

    def _on_crop_spin_changed(self, _value=None):
        """User edited a spin box -> update the crop rectangle."""
        if self._updating_crop:
            return
        self._preview.set_crop_ltrb(
            self._crop_left.value(),
            self._crop_top.value(),
            self._crop_right.value(),
            self._crop_bottom.value(),
        )

    # -- Frame rate hint 

    def _update_fps_hint(self, _value=None):
        """Show the video's native FPS under Frame Rate when the user has
        changed the output FPS away from the detected value."""
        if self._detected_video_fps <= 0:
            self._detected_fps_hint.setVisible(False)
            return

        current = self._fps_spin.value()
        if abs(current - self._detected_video_fps) < self._FPS_MATCH_EPSILON:
            # User is on the detected frame rate: nothing to point out.
            self._detected_fps_hint.setVisible(False)
        else:
            self._detected_fps_hint.setText(
                f"Video native: {self._detected_video_fps:g} fps"
            )
            self._detected_fps_hint.setVisible(True)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save GIF As", "",
            "GIF Files (*.gif);;All Files (*.*)"
        )
        if path:
            # Ensure the file has a .gif extension.
            if not path.lower().endswith('.gif'):
                path += '.gif'
            self._output_path_edit.setText(path)

    def _validate_inputs(self) -> bool:
        input_type = self._input_type_group.checkedId()
        output_path = self._output_path_edit.text().strip()

        if input_type == 0:  # From Video
            input_path = self._input_path_edit.text().strip()
            if not input_path:
                QMessageBox.warning(self, "Validation Error",
                                    "Please select a video file.")
                return False
            if not os.path.isfile(input_path):
                QMessageBox.warning(self, "Validation Error",
                                    f"Video file does not exist:\n{input_path}")
                return False

        else:  # From Files
            if not self._input_files:
                QMessageBox.warning(self, "Validation Error",
                                    "Please add at least one image file.")
                return False

        if not output_path:
            QMessageBox.warning(self, "Validation Error",
                                "Please specify an output GIF file path.")
            return False

        return True

    def _get_input_source(self):
        input_type = self._input_type_group.checkedId()

        if input_type == 0:
            return self._input_path_edit.text().strip()
        else:
            return self._input_files

    def _get_size(self):
        """Resolve the size tuple from the currently selected size mode."""
        if self._size_custom_radio.isChecked():
            width = self._width_spin.value()
            height = self._height_spin.value()
            return (width, height) if width > 0 and height > 0 else None
        # Preset mode.
        return self._size_preset_combo.currentData()

    def _start_creation(self):
        if not self._validate_inputs():
            return

        input_source = self._get_input_source()
        output_path = self._output_path_edit.text().strip()

        fps = self._fps_spin.value()
        loop = self._loop_spin.value()
        colors = self._colors_spin.value()
        dither = self._dither_check.isChecked()

        # Size comes from either the preset combo (default) or the custom
        # width/height spin boxes, depending on the selected size mode.
        size = self._get_size()

        # Crop: only pass a tuple if any side has a non-zero value.
        crop_l = self._crop_left.value()
        crop_t = self._crop_top.value()
        crop_r = self._crop_right.value()
        crop_b = self._crop_bottom.value()
        crop = (crop_l, crop_t, crop_r, crop_b) if any([crop_l, crop_t, crop_r, crop_b]) else None

        # Video-only parameters.
        start_time = None
        end_time = None
        skip_frames = 1

        if self._input_type_group.checkedId() == 0:  # Video
            if self._start_time_spin.value() > 0:
                start_time = self._start_time_spin.value()
            if self._end_time_spin.value() > 0:
                end_time = self._end_time_spin.value()
            skip_frames = self._skip_frames_spin.value()

        self._set_controls_enabled(False)
        self._progress_bar.setVisible(True)
        self._progress_label.setText("Creating GIF...")

        self._worker = GIFCreationWorker(
            input_source=input_source,
            output=output_path,
            fps=fps,
            size=size,
            crop=crop,
            loop=loop,
            start_time=start_time,
            end_time=end_time,
            skip_frames=skip_frames,
            colors=colors,
            dither=dither,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_creation(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._progress_label.setText("Cancelling...")

    def _set_controls_enabled(self, enabled: bool):
        self._create_btn.setEnabled(enabled)
        self._cancel_btn.setEnabled(not enabled)
        self._input_path_edit.setEnabled(enabled)
        self._output_path_edit.setEnabled(enabled)
        self._browse_input_btn.setEnabled(enabled)
        self._browse_output_btn.setEnabled(enabled)
        self._add_files_btn.setEnabled(enabled)
        self._clear_files_btn.setEnabled(enabled)
        self._remove_file_btn.setEnabled(enabled)
        self._fps_spin.setEnabled(enabled)
        self._loop_spin.setEnabled(enabled)
        self._colors_spin.setEnabled(enabled)
        self._dither_check.setEnabled(enabled)
        self._size_preset_radio.setEnabled(enabled)
        self._size_custom_radio.setEnabled(enabled)
        self._size_preset_combo.setEnabled(enabled)
        self._width_spin.setEnabled(enabled)
        self._height_spin.setEnabled(enabled)
        self._crop_left.setEnabled(enabled)
        self._crop_top.setEnabled(enabled)
        self._crop_right.setEnabled(enabled)
        self._crop_bottom.setEnabled(enabled)
        self._start_time_spin.setEnabled(enabled)
        self._end_time_spin.setEnabled(enabled)
        self._skip_frames_spin.setEnabled(enabled)
        self._crop_overlay_check.setEnabled(enabled)

        has_video = self._video_capture is not None
        self._scrubber.setEnabled(enabled and has_video)
        self._set_start_btn.setEnabled(enabled and has_video)
        self._set_end_btn.setEnabled(enabled and has_video)

    @Slot(str)
    def _on_progress(self, message: str):
        self._progress_label.setText(message)

    @Slot(str)
    def _on_finished(self, output_path: str):
        self._set_controls_enabled(True)
        self._progress_bar.setVisible(False)
        self._progress_label.setText(f"GIF created: {os.path.basename(output_path)}")

        reply = QMessageBox.question(
            self, "GIF Created",
            f"Successfully created GIF:\n{output_path}\n\nOpen the file location?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            folder = os.path.dirname(output_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    @Slot(str)
    def _on_error(self, message: str):
        self._set_controls_enabled(True)
        self._progress_bar.setVisible(False)
        self._progress_label.setText("Error occurred")
        QMessageBox.critical(self, "GIF Creation Error", message)

    def save_settings(self, settings: QSettings):
        settings.setValue("gif_input_type", self._input_type_group.checkedId())
        settings.setValue("gif_fps", self._fps_spin.value())
        settings.setValue("gif_loop", self._loop_spin.value())
        settings.setValue("gif_colors", self._colors_spin.value())
        settings.setValue("gif_dither", self._dither_check.isChecked())
        settings.setValue("gif_size_mode", self._size_mode_group.checkedId())
        settings.setValue("gif_width", self._width_spin.value())
        settings.setValue("gif_height", self._height_spin.value())
        settings.setValue("gif_crop_l", self._crop_left.value())
        settings.setValue("gif_crop_t", self._crop_top.value())
        settings.setValue("gif_crop_r", self._crop_right.value())
        settings.setValue("gif_crop_b", self._crop_bottom.value())
        settings.setValue("gif_crop_overlay", self._crop_overlay_check.isChecked())
        settings.setValue("gif_start_time", self._start_time_spin.value())
        settings.setValue("gif_end_time", self._end_time_spin.value())
        settings.setValue("gif_skip_frames", self._skip_frames_spin.value())
        settings.setValue("gif_output_path", self._output_path_edit.text())

    def load_settings(self, settings: QSettings):
        input_type = settings.value("gif_input_type", 0, type=int)
        if input_type == 0:
            self._from_video_radio.setChecked(True)
        else:
            self._from_files_radio.setChecked(True)

        # Re-run the visibility logic so the correct widgets show up.
        self._on_input_type_changed(
            self._from_video_radio if input_type == 0 else self._from_files_radio
        )

        self._fps_spin.setValue(settings.value("gif_fps", 10.0, type=float))
        self._loop_spin.setValue(settings.value("gif_loop", 0, type=int))
        self._colors_spin.setValue(settings.value("gif_colors", 256, type=int))
        self._dither_check.setChecked(settings.value("gif_dither", True, type=bool))

        size_mode = settings.value("gif_size_mode", 0, type=int)
        if size_mode == 1:
            self._size_custom_radio.setChecked(True)
        else:
            self._size_preset_radio.setChecked(True)
        # Apply the visibility that matches the restored radio state.
        self._on_size_mode_changed(
            self._size_custom_radio if size_mode == 1 else self._size_preset_radio
        )

        self._width_spin.setValue(settings.value("gif_width", 0, type=int))
        self._height_spin.setValue(settings.value("gif_height", 0, type=int))
        self._crop_left.setValue(settings.value("gif_crop_l", 0, type=int))
        self._crop_top.setValue(settings.value("gif_crop_t", 0, type=int))
        self._crop_right.setValue(settings.value("gif_crop_r", 0, type=int))
        self._crop_bottom.setValue(settings.value("gif_crop_b", 0, type=int))
        self._start_time_spin.setValue(settings.value("gif_start_time", 0.0, type=float))
        self._end_time_spin.setValue(settings.value("gif_end_time", 0.0, type=float))
        self._skip_frames_spin.setValue(settings.value("gif_skip_frames", 1, type=int))

        out = settings.value("gif_output_path", "", type=str)
        if out:
            self._output_path_edit.setText(out)

        # Must be last: seeding the crop from the spin-box values depends on
        # the other crop settings having been restored first.
        self._crop_overlay_check.setChecked(
            settings.value("gif_crop_overlay", False, type=bool)
        )


class HelpDialog(QDialog):
    """Dialog containing usage documentation for every TransImage option."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TransImage Help")
        self.resize(640, 560)

        layout = QVBoxLayout(self)

        browser = QTextEdit()
        browser.setReadOnly(True)
        browser.setHtml("""
            <style>
                h2 { color: #F5A9B8; margin-top: 18px; margin-bottom: 6px; }
                h3 { color: #5BCEFA; margin-top: 14px; margin-bottom: 4px; }
                p, li { color: #ddd; font-size: 12px; }
                code { background-color: #333; padding: 1px 4px; border-radius: 3px; }
                .note { color: #aaa; font-size: 11px; font-style: italic; }
            </style>

            <h2>Image Conversion</h2>

            <h3>Output Format</h3>
            <p>Target format for converted images. Available:
            <code>png</code>, <code>jpg</code>, <code>bmp</code>,
            <code>webp</code>. If the source already matches the target,
            the file is moved rather than re-encoded.</p>

            <h3>JPG Quality</h3>
            <p>Only applies when the target format is <code>jpg</code>.
            Ranges from 1 (smallest file, most artifacts) to 100
            (largest file, best fidelity). 95 is a good default.</p>

            <h3>Keep original files when format matches</h3>
            <p>When enabled, source files already in the target format
            are left in place rather than being overwritten or moved.</p>

            <h2>GIF Settings</h2>

            <h3>Frame Rate</h3>
            <p>Output frames per second. Higher values give smoother
            motion but larger files. For real-time playback of a video,
            see the Skip Frames section below.</p>

            <p>When a video is loaded in <b>From Video</b> mode, its
            native frame rate is detected automatically and used as the
            default Frame Rate. If you change the Frame Rate away from
            that value, a small hint appears under the field showing the
            video's native fps so you can always find your way back.</p>

            <h3>Loop Count</h3>
            <p>How many times the GIF repeats. <code>0</code> = infinite
            (recommended for most GIFs).</p>

            <h3>Colors</h3>
            <p>Maximum palette size (2 to 256). Lower values shrink the
            file but lose color detail. 256 = full 8-bit palette.</p>

            <h3>Enable Dithering</h3>
            <p>Adds a dithering pattern to smooth gradients. Improves
            perceived quality but can increase file size. Disable for
            flat colors or a retro/pixel-art look.</p>

            <h3>Size</h3>
            <p>The output size is chosen in one of two modes:</p>
            <ul>
                <li><b>Preset</b> (default): a dropdown listing scaled
                multiples of the source resolution. For a 1920x1080
                video this offers 1920x1080 (original), 960x540 (1/2),
                640x360 (1/3), 480x270 (1/4), and so on. Presets are
                populated automatically when a video is loaded or the
                first image is added.</li>
                <li><b>Custom</b>: type any Width x Height directly.
                Set both to <em>Auto</em> to keep the original size.</li>
            </ul>
            <p>In both modes the aspect ratio is preserved, so the
            frame fits inside the chosen box.</p>

            <h3>Crop (LTRB)</h3>
            <p>Trim N pixels off each edge of every frame before
            encoding. L = Left, T = Top, R = Right, B = Bottom. All 0
            means no crop.</p>

            <p>Enable <b>Interactive crop overlay on preview</b> to see
            the crop rectangle drawn on top of the video preview. Each
            of the four edges can be dragged independently; the LTRB
            spin boxes update automatically, and editing the spin boxes
            moves the rectangle in return. Scrubbing the timeline does
            not reset your crop selection.</p>

            <h2>Video Settings</h2>

            <h3>Start Time</h3>
            <p>Skip the first N seconds of the video. 0 = start at the
            very beginning.</p>

            <h3>End Time</h3>
            <p>Stop capturing at N seconds. Leave as <em>End</em> to
            capture to the last frame.</p>

            <h3>Skip Frames</h3>
            <p>Capture one frame out of every N source frames.
            <strong>Default: 1</strong> (capture every frame).</p>

            <p>Skip Frames drops source frames to shrink the GIF. To
            keep the playback speed close to the original, set the
            output Frame Rate using the ratio of the video's FPS to
            Skip Frames:</p>

            <p style="margin-left: 24px;">
                <code>output fps = video fps / skip frames</code>
            </p>

            <p>For example, a 30&nbsp;fps video with Skip Frames = 2:
            set Frame Rate to 15&nbsp;fps. With Skip Frames = 1, every
            source frame is captured, so set Frame Rate to the video's
            native FPS for real-time playback.</p>

            <p class="note">Tip: screen recordings often contain long
            runs of identical frames. Raising Skip Frames to 2 or 3
            removes those duplicates and can make the GIF feel more
            responsive while shrinking the file.</p>

            <h3>Scrubber</h3>
            <p>The slider under the video settings lets you jump to any
            point in the video and preview the frame that will be captured.
            Drag the handle to seek; the preview updates shortly after you
            stop dragging.</p>

            <p>Use <b>Set Start</b> and <b>Set End</b> to lock the current
            scrubber position into the Start Time and End Time fields. This
            is the fastest way to trim a clip: scrub to where you want to
            begin, click <b>Set Start</b>, scrub to where you want to end,
            click <b>Set End</b>.</p>

            <p class="note">Scrubbing requires OpenCV
            (<code>opencv-python-headless</code>). If it isn't installed,
            the scrubber is disabled and a hint is shown in the preview.</p>

            <h3>Output GIF path</h3>
            <p>When you pick a video in <b>From Video</b> mode and the
            Output GIF field is empty, TransImage automatically fills in
            a path in the same folder as the video, using the video's
            file name with a <code>.gif</code> extension. You can always
            overwrite this by typing your own path or clicking
            <b>Browse...</b>.</p>

            <h2>Tips &amp; Shortcuts</h2>
            <ul>
                <li><b>Drag and drop</b> a file or folder onto the
                Source field to set it instantly.</li>
                <li><b>Ctrl+N</b> starts a new session.</li>
                <li><b>Ctrl+,</b> opens the Settings dialog.</li>
                <li><b>F1</b> opens this Help dialog.</li>
                <li>Every action has a <b>Cancel</b> button; conversion
                and GIF creation both run on background threads and can
                be stopped mid-run.</li>
            </ul>
        """)
        layout.addWidget(browser)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class AboutDialog(QDialog):
    """About dialog for TransImage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About TransImage")
        self.setFixedSize(400, 350)

        layout = QVBoxLayout(self)

        title_label = QLabel("TransImage")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #F5A9B8;
            padding: 20px;
        """)
        layout.addWidget(title_label)

        subtitle = QLabel("Image Format Conversion & GIF Creation")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        desc = QTextEdit()
        desc.setReadOnly(True)
        desc.setHtml("""
            <p style="color: #ccc;">
            <b>TransImage</b> is a Python tool for converting images between
            different formats and creating animated GIFs from image sequences,
            directories, or video files.
            </p>

            <p style="color: #ccc;"><b>Features:</b></p>
            <ul style="color: #ccc;">
                <li>Convert images between JPG, PNG, BMP, and WebP formats</li>
                <li>Batch conversion of multiple images</li>
                <li>Create GIFs from images or videos</li>
                <li>Configurable GIF parameters (FPS, size, crop, colors)</li>
                <li>Video trimming and frame skipping</li>
            </ul>

            <p style="color: #ccc;"><b>Dependencies:</b></p>
            <ul style="color: #ccc;">
                <li>Pillow - Image processing</li>
                <li>OpenCV (optional) - Video frame extraction</li>
                <li>PySide6 - GUI framework</li>
            </ul>
            """)
        layout.addWidget(desc)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent=None, reset_on_startup=False):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        startup_group = QGroupBox("Startup Behavior")
        startup_layout = QVBoxLayout(startup_group)

        self._reset_check = QCheckBox(
            "Reset all options to defaults every time the app opens"
        )
        self._reset_check.setChecked(reset_on_startup)
        startup_layout.addWidget(self._reset_check)

        hint = QLabel(
            "When unchecked, the format, quality, GIF parameters, and output "
            "paths you used last will be restored on the next launch."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px; padding-left: 26px;")
        startup_layout.addWidget(hint)

        layout.addWidget(startup_group)
        layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    @property
    def reset_on_startup(self) -> bool:
        return self._reset_check.isChecked()


class TransImageWindow(QMainWindow):
    """Main application window for TransImage GUI."""

    def __init__(self):
        super().__init__()

        self._setup_ui()
        self._create_menus()
        self._create_status_bar()
        self._reset_on_startup = False
        self._load_settings()

        self.setWindowTitle("TransImage - Image Conversion & GIF Creation")
        self.setMinimumSize(900, 700)

    def _setup_ui(self):
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._conversion_tab = ImageConversionTab()
        self._gif_tab = GIFCreationTab()

        self._tabs.addTab(self._conversion_tab, "Image Conversion")
        self._tabs.addTab(self._gif_tab, "GIF Creation")

        self._tabs.setTabIcon(0, QIcon.fromTheme("image-x-generic"))
        self._tabs.setTabIcon(1, QIcon.fromTheme("video-x-generic"))

        # GIF Creation is the tab that opens by default.
        self._tabs.setCurrentIndex(1)

        self.setCentralWidget(self._tabs)

        # Global stylesheet applied to every widget in the window.
        # Light Pink (#F5A9B8) is used for section headings; Light Blue
        # (#5BCEFA) is used for interactive accent elements.
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }

            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-size: 13px;
            }

            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #252525;
                border-radius: 4px;
            }

            QTabBar::tab {
                background-color: #2a2a2a;
                color: #aaa;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }

            QTabBar::tab:selected {
                background-color: #252525;
                color: #fff;
                border-bottom: 2px solid #5BCEFA;
            }

            QTabBar::tab:hover:!selected {
                background-color: #333;
            }

            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #2a2a2a;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #F5A9B8;
            }

            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
                selection-background-color: #5BCEFA;
                selection-color: #1e1e1e;
            }

            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #5BCEFA;
            }

            QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
                background-color: #2a2a2a;
                color: #666;
            }

            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #888;
                margin-right: 5px;
            }

            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px 16px;
                color: #e0e0e0;
            }

            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #555;
            }

            QPushButton:pressed {
                background-color: #2a2a2a;
            }

            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666;
                border-color: #333;
            }

            QListWidget {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px;
            }

            QListWidget::item {
                padding: 4px;
                border-radius: 2px;
            }

            QListWidget::item:selected {
                background-color: #5BCEFA;
                color: #1e1e1e;
            }

            QListWidget::item:hover:!selected {
                background-color: #3a3a3a;
            }

            QProgressBar {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                color: #fff;
            }

            QProgressBar::chunk {
                background-color: #5BCEFA;
                border-radius: 3px;
            }

            QCheckBox {
                spacing: 8px;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #333;
            }

            QCheckBox::indicator:checked {
                background-color: #5BCEFA;
                border-color: #5BCEFA;
            }

            QRadioButton {
                spacing: 8px;
            }

            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555;
                border-radius: 9px;
                background-color: #333;
            }

            QRadioButton::indicator:checked {
                background-color: #5BCEFA;
                border-color: #5BCEFA;
            }

            QLabel {
                color: #ccc;
            }

            QMenuBar {
                background-color: #2a2a2a;
                color: #e0e0e0;
            }

            QMenuBar::item:selected {
                background-color: #3a3a3a;
            }

            QMenu {
                background-color: #2a2a2a;
                border: 1px solid #444;
                color: #e0e0e0;
            }

            QMenu::item:selected {
                background-color: #5BCEFA;
                color: #1e1e1e;
            }

            QStatusBar {
                background-color: #2a2a2a;
                color: #aaa;
            }

            QScrollArea {
                border: none;
            }

            QSplitter::handle {
                background-color: #444;
            }

            QSplitter::handle:hover {
                background-color: #5BCEFA;
            }

            QSlider::groove:horizontal {
                height: 6px;
                background: #333;
                border: 1px solid #444;
                border-radius: 3px;
            }

            QSlider::sub-page:horizontal {
                background: #5BCEFA;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                background: #e0e0e0;
                border: 1px solid #555;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }

            QSlider::handle:horizontal:hover {
                background: #5BCEFA;
                border-color: #5BCEFA;
            }

            QSlider::handle:horizontal:disabled {
                background: #555;
                border-color: #333;
            }
        """)

    def _create_menus(self):
        menubar = self.menuBar()

        # --- File menu ---
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_session)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Edit menu ---
        edit_menu = menubar.addMenu("&Edit")

        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        edit_menu.addAction(settings_action)

        # --- Tools menu ---
        tools_menu = menubar.addMenu("&Tools")

        open_output_action = QAction("Open Output Folder", self)
        open_output_action.triggered.connect(self._open_output_folder)
        tools_menu.addAction(open_output_action)

        # --- Help menu ---
        help_menu = menubar.addMenu("&Help")

        help_action = QAction("&TransImage Help", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)   # F1
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction("&About TransImage", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        about_qt_action = QAction("About &Qt", self)
        about_qt_action.triggered.connect(QApplication.aboutQt)
        help_menu.addAction(about_qt_action)

    def _create_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._status_label = QLabel("Ready")
        self._status_bar.addWidget(self._status_label)

        self._version_label = QLabel("v3.1.0")
        self._status_bar.addPermanentWidget(self._version_label)

    def _load_settings(self):
        settings = QSettings("TransImage", "GUI")

        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        self._reset_on_startup = settings.value(
            "reset_on_startup", False, type=bool
        )

        # When reset-on-startup is on, ignore any saved tab options.
        if self._reset_on_startup:
            return

        self._conversion_tab.load_settings(settings)
        self._gif_tab.load_settings(settings)

    def _save_settings(self):
        settings = QSettings("TransImage", "GUI")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("reset_on_startup", self._reset_on_startup)

        if self._reset_on_startup:
            # Clear any saved tab options so next launch starts fresh.
            for key in (
                "conv_format", "conv_quality", "conv_keep_original",
                "conv_output_path",
                "gif_input_type", "gif_fps", "gif_loop", "gif_colors",
                "gif_dither", "gif_size_mode", "gif_width", "gif_height",
                "gif_crop_l", "gif_crop_t", "gif_crop_r", "gif_crop_b",
                "gif_crop_overlay",
                "gif_start_time", "gif_end_time", "gif_skip_frames",
                "gif_output_path",
            ):
                settings.remove(key)
            return

        self._conversion_tab.save_settings(settings)
        self._gif_tab.save_settings(settings)

    def closeEvent(self, event):
        self._gif_tab.release_resources()
        self._save_settings()
        event.accept()

    @Slot()
    def _new_session(self):
        # Reset both tabs' visible fields to a fresh state.
        self._conversion_tab._input_path_edit.clear()
        self._conversion_tab._output_path_edit.clear()
        self._conversion_tab._file_list.clear()
        self._conversion_tab._preview.clear()
        self._conversion_tab._progress_bar.setValue(0)
        self._conversion_tab._progress_label.setText("Ready")

        self._gif_tab._input_path_edit.clear()
        self._gif_tab._output_path_edit.clear()
        self._gif_tab._files_list.clear()
        self._gif_tab._input_files.clear()
        self._gif_tab._preview.clear()
        self._gif_tab._progress_label.setText("Ready")

        self._status_label.setText("New session started")

    @Slot()
    def _show_settings(self):
        dialog = SettingsDialog(self, self._reset_on_startup)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reset_on_startup = dialog.reset_on_startup
            self._status_label.setText(
                "Settings saved"
                + (" (options will reset on next launch)"
                   if self._reset_on_startup else "")
            )

    @Slot()
    def _open_output_folder(self):
        # Prefer the conversion tab's output folder; fall back to the
        # GIF tab's parent folder.
        output_path = self._conversion_tab._output_path_edit.text()
        if not output_path:
            output_path = self._gif_tab._output_path_edit.text()
            if output_path:
                output_path = os.path.dirname(output_path)

        if output_path and os.path.exists(output_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))
        else:
            QMessageBox.information(
                self, "No Output Folder",
                "No output folder has been set yet."
            )

    @Slot()
    def _show_help(self):
        dialog = HelpDialog(self)
        dialog.exec()

    @Slot()
    def _show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()


def main():
    """Main entry point for the TransImage GUI application."""
    app = QApplication(sys.argv)

    app.setApplicationName("TransImage")
    app.setApplicationVersion("3.1.0")
    app.setOrganizationName("TransImage")
    app.setOrganizationDomain("transimage.local")

    app.setStyle("Fusion")

    window = TransImageWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()