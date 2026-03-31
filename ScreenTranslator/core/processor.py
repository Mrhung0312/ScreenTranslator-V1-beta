import os
import requests
from dotenv import load_dotenv
import logging
import cv2
import pytesseract
import shutil
from deep_translator import GoogleTranslator
from core.text_cleaner import clean_text, filter_text

# Configure Tesseract path
tesseract_cmd = shutil.which("tesseract")
if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
else:
    pytesseract.pytesseract.tesseract_cmd = r"D:\tesseract\tesseract.exe"
from PyQt6.QtCore import QThread, pyqtSignal

load_dotenv()

logger = logging.getLogger(__name__)

class TranslationProcessor(QThread):
    _translation_cache = {}
    _MAX_CACHE_SIZE = 100

    finished_processing = pyqtSignal(str, str, str)

    def __init__(self, image_np, target_lang="vi"):
        super().__init__()
        self.image_np = image_np
        self.target_lang = target_lang
        self.reader = None

    def extract_text(self, image):
        """
        Extracts text from the given image using Tesseract OCR.
        """
        if len(image.shape) == 3 and image.shape[2] == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        else:
            bgr = image

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
        
        text = pytesseract.image_to_string(gray, lang='eng+jpn')
        
        return text.strip()

    def run(self):
        """
        Main executing logic in the worker thread.
        """
        if self.image_np is None:
            self.finished_processing.emit("", "", "Invalid image data.")
            return

        try:
    
            logger.info("Running Tesseract OCR...")
            raw_text = self.extract_text(self.image_np)
            
            if not raw_text:
                logger.warning("OCR found no text.")
                self.finished_processing.emit("", "", "No text detected.")
                return

            logger.info(f"OCR Result: {raw_text}")
            
            clean = clean_text(raw_text)
            clean = filter_text(clean)
            
            if len(clean) < 2:
                logger.info(f"Text too short to translate: '{clean}'")
                self.finished_processing.emit(clean, clean, "")
                return

            translated_text = self.translate_langbly(clean)

            logger.info("Translation complete.")
            self.finished_processing.emit(clean, translated_text, "")

        except Exception as e:
            logger.error(f"Error in processor thread: {e}", exc_info=True)
            self.finished_processing.emit("", "", f"Processing Error: {str(e)}")

    def _cache_result(self, text, translated_text):
        if len(self.__class__._translation_cache) >= self.__class__._MAX_CACHE_SIZE:
            oldest_key = next(iter(self.__class__._translation_cache))
            del self.__class__._translation_cache[oldest_key]
        self.__class__._translation_cache[text] = translated_text
        return translated_text

    def _call_langbly_api(self, api_key, text):
        url = "https://api.langbly.com/translate"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "source": "auto",
            "target": self.target_lang
        }
        
        logger.info("Sending request to Langbly API...")
        response = requests.post(url, headers=headers, json=data, timeout=5)
        logger.info(f"Langbly API response status: {response.status_code}")
        response.raise_for_status()
        
        result = response.json()
        return result.get("translated_text", result.get("translation", ""))

    def translate_langbly(self, text):
        if text in self.__class__._translation_cache:
            logger.info("Using cached translation.")
            return self.__class__._translation_cache[text]

        api_key = os.environ.get("LANGBLY_API_KEY")
        if not api_key:
            logger.warning("LANGBLY_API_KEY not found. Falling back to GoogleTranslator.")
            return self._cache_result(text, self.fallback_translation(text))

        try:
            translated_text = self._call_langbly_api(api_key, text)
            
            if not translated_text:
                logger.warning("Langbly API returned empty translation. Falling back.")
                return self._cache_result(text, self.fallback_translation(text))

            return self._cache_result(text, translated_text)

        except Exception as e:
            logger.warning(f"Langbly API request failed: {e}. Processing fallback...")
            return self._cache_result(text, self.fallback_translation(text))

    def fallback_translation(self, text):
        logger.info("Using fallback translation (GoogleTranslator).")
        try:
            translator = GoogleTranslator(source='auto', target=self.target_lang)
            return translator.translate(text)
        except Exception as e:
            logger.error(f"Fallback GoogleTranslator failed: {e}")
            return f"[Translation Error] {str(e)}"
