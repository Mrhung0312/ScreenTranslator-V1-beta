from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QPoint, QPropertyAnimation, QEasingCurve, QAbstractAnimation, pyqtProperty
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QColor

LANGUAGES = [
    ("Vietnamese", "vi"),
    ("English", "en"),
    ("Chinese", "zh"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("French", "fr"),
    ("Russian", "ru")
]

class LanguagePanel(QWidget):
    language_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_index = 0
        self._labels = []
        self._spacing = 10
        self._animation_duration_ms = 200
        self._panel_height = 0
        self._full_height = 0
        self._pending_hide = False
        self._setup_ui()

        # Dropdown animation: keep position fixed, only animate height.
        self.setFixedHeight(0)
        self.container.setFixedHeight(0)

        self._height_animation = QPropertyAnimation(self, b"panelHeight")
        self._height_animation.setDuration(self._animation_duration_ms)
        self._height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._height_animation.finished.connect(self._on_animation_finished)

    def setPanelHeight(self, h: int):
        h = max(0, int(h))
        if h == self._panel_height:
            return
        self._panel_height = h
        # Maintain "roller shutter" effect by constraining layout height while animating.
        self.setFixedHeight(h)
        if hasattr(self, "container"):
            self.container.setFixedHeight(h)

    @pyqtProperty(int, fset=setPanelHeight)
    def panelHeight(self) -> int:
        return self._panel_height

    def _setup_ui(self):
        # Keep this as a tool window (even with parent) so it can be placed
        # outside the parent's rect while still staying logically attached.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame()
        self.container.setObjectName("InnerContainer")
        outer_layout.addWidget(self.container)

        self.setStyleSheet("""
            #InnerContainer {
                background-color: #ffffff;
                border-radius: 14px;
                border: 1px solid #e0e0e0;
            }
            QLabel {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                border: none;
                background-color: transparent;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        for name, code in LANGUAGES:
            label = QLabel(f"{name} ({code})")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            label.installEventFilter(self)
            self._labels.append(label)
            layout.addWidget(label)

        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        self._update_selection_ui()

    def _update_selection_ui(self):
        for i, label in enumerate(self._labels):
            if i == self._selected_index:
                label.setStyleSheet("""
                    background-color: #e5e5e5;
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: #000000;
                """)
            else:
                label.setStyleSheet("""
                    background-color: transparent;
                    padding: 6px 12px;
                    color: #000000;
                """)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.Enter and isinstance(source, QLabel) and source in self._labels:
            self._selected_index = self._labels.index(source)
            self._update_selection_ui()
            return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Up:
            self._selected_index = (self._selected_index - 1) % len(self._labels)
            self._update_selection_ui()
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self._selected_index = (self._selected_index + 1) % len(self._labels)
            self._update_selection_ui()
            event.accept()
        elif event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self._select_current()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide_with_animation()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            clicked_widget = self.childAt(event.pos())
            if isinstance(clicked_widget, QLabel) and clicked_widget in self._labels:
                self._selected_index = self._labels.index(clicked_widget)
                self._update_selection_ui()
                self._select_current()
                event.accept()
                return
        super().mousePressEvent(event)

    def _select_current(self):
        code = LANGUAGES[self._selected_index][1]
        self.language_selected.emit(code)

    def attach_to_parent(self, spacing: int = 10):
        self._spacing = spacing
        # Initial state: hidden + height=0 at the correct anchored position.
        self.setPanelHeight(0)
        self.reposition()

    def _get_visible_pos(self) -> QPoint:
        parent = self.parentWidget()
        if parent is None:
            return self.pos()
        anchor = getattr(parent, "_container", parent)
        top_left_global = anchor.mapToGlobal(anchor.rect().topLeft())
        x = top_left_global.x() + anchor.width() + self._spacing
        y = top_left_global.y()
        return QPoint(x, y)

    def _compute_full_height(self) -> int:
        """
        Temporarily remove fixed-height constraints so Qt can compute natural size,
        then restore collapsed state (height=0) for the start of the animation.
        """
        if not hasattr(self, "container"):
            return 0

        # Allow Qt to compute natural height.
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
        self.container.setMinimumHeight(0)
        self.container.setMaximumHeight(16777215)

        self.adjustSize()
        h = int(self.sizeHint().height())
        if h <= 0:
            h = int(self.container.sizeHint().height())

        # Restore collapsed constraint for consistent animation start.
        self.setFixedHeight(0)
        self.container.setFixedHeight(0)
        self._panel_height = 0
        return max(0, h)

    def show_with_animation(self):
        self._pending_hide = False
        self._height_animation.stop()

        visible_pos = self._get_visible_pos()

        # Ensure top edge stays fixed while height grows.
        self.move(visible_pos)
        self.show()
        self.raise_()

        self._full_height = self._compute_full_height()

        # Start collapsed (height=0) then grow downward.
        self.setPanelHeight(0)
        self._height_animation.setStartValue(0)
        self._height_animation.setEndValue(self._full_height)
        self._height_animation.start()

    def hide_with_animation(self):
        if not self.isVisible():
            return
        self._pending_hide = True
        self._height_animation.stop()

        visible_pos = self._get_visible_pos()
        self.move(visible_pos)

        if self._full_height <= 0:
            # Fallback if content size changed while hidden.
            self._full_height = self._compute_full_height()

        start_h = int(self.panelHeight)
        if start_h <= 0:
            start_h = int(self._full_height)

        # Roll up: shrink down to height=0; then hide().
        self._height_animation.setStartValue(start_h)
        self._height_animation.setEndValue(0)
        self._height_animation.start()

    def _on_animation_finished(self):
        if self._pending_hide:
            self._pending_hide = False
            self.setPanelHeight(0)
            self.hide()

    def reposition(self):
        # Keep X position and top alignment stable while parent moves.
        self.move(self._get_visible_pos())
