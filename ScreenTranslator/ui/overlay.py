from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen

import logging

logger = logging.getLogger(__name__)

class ScreenOverlay(QWidget):
    # Signal emitted when a region is successfully selected (x, y, width, height)
    rect_selected = pyqtSignal(int, int, int, int)

    def __init__(self):
        super().__init__()
        # Set window flags for an overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.is_drawing = False

        # Get all screens geometry to span across multiple monitors
        self.setup_geometry()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def setup_geometry(self):
        # We need the geometry of all screens combined
        screens = QApplication.screens()
        min_x = min([screen.geometry().x() for screen in screens])
        min_y = min([screen.geometry().y() for screen in screens])
        max_right = max([screen.geometry().right() for screen in screens])
        max_bottom = max([screen.geometry().bottom() for screen in screens])

        width = max_right - min_x
        height = max_bottom - min_y

        self.setGeometry(min_x, min_y, width, height)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent dark background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.is_drawing or not self.start_pos.isNull():
            # Calculate the current selection rectangle
            rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # Clear the area inside the selection
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # Draw a border around the selection
            pen = QPen(QColor(0, 120, 215, 255), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint()
            self.end_pos = self.start_pos
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end_pos = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.is_drawing = False
            self.end_pos = event.globalPosition().toPoint()
            self.update()

            rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # Ensure the rectangle isn't just a click
            if rect.width() > 5 and rect.height() > 5:
                # We hide the overlay right after selection so the screen capturer doesn't capture the overlay's border
                self.hide()
                # Use QTimer to slightly delay emission so the window is completely gone from the screen buffer
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, lambda: self.rect_selected.emit(rect.x(), rect.y(), rect.width(), rect.height()))
                logger.info(f"Region selected: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
            else:
                logger.debug("Selection too small, ignoring.")
                self.hide()

            # Reset points
            self.start_pos = QPoint()
            self.end_pos = QPoint()

    def keyPressEvent(self, event):
        # Escape key to cancel
        if event.key() == Qt.Key.Key_Escape:
            logger.debug("Overlay cancelled via Escape key.")
            self.hide()
            self.start_pos = QPoint()
            self.end_pos = QPoint()
            self.update()
