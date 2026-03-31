import sys
import logging
import keyboard
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject


from ui.overlay import ScreenOverlay
from ui.tooltip import TooltipWindow
from ui.language_panel import LanguagePanel
from core.capture import ScreenCapture
from core.processor import TranslationProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HotkeySignaler(QObject):
    capture_signal = pyqtSignal()
    toggle_visibility_signal = pyqtSignal()
    toggle_language_panel_signal = pyqtSignal()

class ScreenTranslatorApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.overlay = ScreenOverlay()
        self.tooltip = TooltipWindow()
        self.capturer = ScreenCapture()
        self.processor_thread = None

        self.target_lang = "vi"
        self.language_panel = LanguagePanel(parent=self.tooltip)
        self.language_panel.language_selected.connect(self.on_language_selected)
        self.tooltip.window_moved.connect(self.language_panel.reposition)
        self.language_panel.attach_to_parent(spacing=10)
        self.language_panel.hide()

        self.signaler = HotkeySignaler()
        self.setup_signals()
        self.setup_hotkeys()
        
        self.is_processing = False

    def setup_signals(self):
        self.signaler.capture_signal.connect(self.start_capture)
        self.signaler.toggle_visibility_signal.connect(self.toggle_visibility)
        self.signaler.toggle_language_panel_signal.connect(self.toggle_language_panel)
        self.overlay.rect_selected.connect(self.on_region_selected)

    def setup_hotkeys(self):
        keyboard.add_hotkey('alt+q', lambda: self.signaler.capture_signal.emit())
        keyboard.add_hotkey('alt+w', lambda: self.signaler.toggle_visibility_signal.emit())
        keyboard.add_hotkey('alt+l', lambda: self.signaler.toggle_language_panel_signal.emit())
        logger.info("Global hotkeys registered (Alt+Q, Alt+W, Alt+L).")

    def start_capture(self):
        if self.is_processing:
            logger.warning("Already processing a translation.")
            return

        logger.info("Ctrl+Q pressed. Showing selection overlay.")
        # Ensure overlay is top and takes focus (might require activateWindow)
        self.overlay.show()
        self.overlay.activateWindow()
        self.overlay.setFocus()
        
        # Hide tooltip during capture to prevent it from obstructing
        self.tooltip.hide()

    def on_region_selected(self, x, y, width, height):
        logger.info(f"Region captured from UI: {x}, {y}, {width}x{height}")
        
        # 1. Capture screen data
        img_np = self.capturer.capture_region(x, y, width, height)
        if img_np is None:
            logger.error("Failed to capture screen data.")
            return

        # 2. Show a loading state on tooltip immediately
        self.tooltip.update_content("Processing image...", "Translating...")
        
        # 3. Start processing in background thread
        self.is_processing = True
        self.processor_thread = TranslationProcessor(img_np, self.target_lang)
        self.processor_thread.finished_processing.connect(self.on_translation_finished)
        self.processor_thread.start()

    def on_translation_finished(self, original, translated, error):
        logger.info("Translation finished via threaded processor.")
        self.is_processing = False
        
        self.tooltip.update_content(original, translated, error)
        self.language_panel.reposition()



    def toggle_visibility(self):
        logger.info("Ctrl+O pressed. Toggling UI visibility.")
        if self.tooltip.isVisible():
            self.tooltip.hide()
            if self.language_panel.isVisible():
                self.language_panel.hide()
        else:
            # Only show if there's actually something to show (or let it show empty)
            self.tooltip.show()
            if self.language_panel.isVisible():
                self.language_panel.reposition()

    def on_language_selected(self, lang_code):
        self.target_lang = lang_code
        logger.info(f"Target language changed to: {lang_code}")

    def toggle_language_panel(self):
        logger.info("Alt+L pressed. Toggling language panel.")
        if self.language_panel.isVisible():
            self.language_panel.hide_with_animation()
        else:
            self.language_panel.show_with_animation()
            self.language_panel.setFocus()

    def run(self):
        logger.info("Screen Translator Application Started. Waiting for hotkeys...")
        return self.app.exec()

if __name__ == '__main__':
    app = ScreenTranslatorApp()
    sys.exit(app.run())
