from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QApplication,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QKeyEvent, QKeySequence

import logging

logger = logging.getLogger(__name__)


class TypingAnimator:
    """Handles character-by-character typing animation for a QLabel."""

    def __init__(self, label: QLabel, on_complete=None, on_resize=None):
        self._label = label
        self._on_complete = on_complete
        self._on_resize = on_resize
        self._full_text = ""
        self._current_index = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

    def start(self, text: str, interval_ms: int = 28):
        """Begin typing animation with the given text."""
        self._full_text = text
        self._current_index = 0
        self._label.setText("")
        self._timer.start(interval_ms)

    def stop(self):
        """Stop the animation and show full text immediately."""
        self._timer.stop()
        self._label.setText(self._full_text)

    def _tick(self):
        self._current_index += 1
        self._label.setText(self._full_text[:self._current_index])

        if self._current_index >= len(self._full_text):
            self._timer.stop()
            if self._on_complete:
                self._on_complete()
        elif self._on_resize:
            self._on_resize()


class TooltipWindow(QWidget):
    window_moved = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._drag_pos = QPoint()
        self._user_moved = False  # Track if user manually moved the window
        self._full_original = ""
        self._full_translated = ""
        self._setup_ui()
        self._setup_animators()

    # ─── UI Setup ──────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(16, 12, 16, 12)

        self._container = QFrame()
        self._container.setObjectName("TooltipContainer")
        outer_layout.addWidget(self._container)

        # Inner layout
        inner_layout = QVBoxLayout(self._container)
        inner_layout.setContentsMargins(20, 16, 20, 16)
        inner_layout.setSpacing(0)

        # Font
        font = QFont("Segoe UI", 11)

        # Original text label
        self._label_original = QLabel("")
        self._label_original.setFont(font)
        self._label_original.setWordWrap(True)
        self._label_original.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # Enable text selection
        self._label_original.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._label_original.setCursor(Qt.CursorShape.IBeamCursor)
        self._label_original.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self._label_original.setStyleSheet("color: #000000; background-color: transparent; border-radius: 6px; padding: 4px;")

        # Divider
        self._divider = QFrame()
        self._divider.setFrameShape(QFrame.Shape.HLine)
        self._divider.setFixedHeight(1)
        self._divider.setStyleSheet("background-color: #d4d4d4; border: none;")

        # Translated text label
        self._label_translated = QLabel("")
        self._label_translated.setFont(font)
        self._label_translated.setWordWrap(True)
        self._label_translated.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # Enable text selection
        self._label_translated.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._label_translated.setCursor(Qt.CursorShape.IBeamCursor)
        self._label_translated.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self._label_translated.setStyleSheet("color: #000000; background-color: transparent; border-radius: 6px; padding: 4px;")

        inner_layout.addWidget(self._label_original)
        inner_layout.addSpacing(6)
        inner_layout.addWidget(self._divider)
        inner_layout.addSpacing(6)
        inner_layout.addWidget(self._label_translated)

        # Sizing — expand horizontally first, wrap only at max width
        self.setMaximumWidth(400)
        outer_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        # Stylesheet — pure white, black text, rounded corners
        self.setStyleSheet("""
            #TooltipContainer {
                background-color: #ffffff;
                border-radius: 14px;
                border: 1px solid #e0e0e0;
            }
            QLabel {
                color: #000000;
                background-color: transparent;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self._container)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        self._container.setGraphicsEffect(shadow)

    def _setup_animators(self):
        self._anim_original = TypingAnimator(
            self._label_original,
            on_complete=self._on_original_typing_done,
            on_resize=self._auto_resize,
        )
        self._anim_translated = TypingAnimator(
            self._label_translated,
            on_complete=self._auto_resize,
            on_resize=self._auto_resize,
        )

        self._pending_translated = ""

    # ─── Public API ────────────────────────────────────────────

    def update_content(self, original: str, translated: str, error: str = ""):
        """Update both labels with typing animation (original first, then translated)."""
        # Stop any running animations
        self._anim_original.stop()
        self._anim_translated.stop()

        if error:
            original = "Error"
            translated = error

        self._full_original = original
        self._full_translated = translated

        # Store translated text to animate after original finishes
        self._pending_translated = translated

        # Pre-set the full text invisibly so Qt can compute proper sizes
        self._label_original.setText(original)
        self._label_translated.setText(translated)
        self.adjustSize()

        # Only reposition if the user hasn't moved it themselves
        if not self._user_moved:
            self._position_bottom_center()

        self.show()
        self.raise_()

        # Now clear and start typing animations
        self._label_original.setText("")
        self._label_translated.setText("")
        self._anim_original.start(original)

    # ─── Animation Callbacks ──────────────────────────────────

    def _on_original_typing_done(self):
        """Called when the original text typing is complete; starts translated text."""
        self._auto_resize()
        self._anim_translated.start(self._pending_translated)

    def _auto_resize(self):
        """Recalculate window size to fit current content."""
        self.adjustSize()

    # ─── Window Positioning ───────────────────────────────────

    def _position_bottom_center(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geom = screen.geometry()
        x = geom.x() + (geom.width() - self.width()) // 2
        y = geom.y() + geom.height() - self.height() - 48
        self.move(x, y)
        self.window_moved.emit()

    # ─── Drag Support ─────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if we clicked on a label.
            child = self.childAt(event.pos())
            if child in (self._label_original, self._label_translated):
                # If clicking on text, we allow the label to handle it (for selection)
                # But we still want to allow dragging if the user moves the mouse.
                pass 
            
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            # Simple compromise: allow dragging if not clicking directly on a label
            child = self.childAt(event.pos())
            if child not in (self._label_original, self._label_translated):
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                self._user_moved = True # Mark that user has manually moved the window
                self.window_moved.emit()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = QPoint()
        self.window_moved.emit()
        event.accept()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.window_moved.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.window_moved.emit()

    def keyPressEvent(self, event: QKeyEvent):
        # Default behavior handles Ctrl+C automatically for selectable QLabels
        super().keyPressEvent(event)