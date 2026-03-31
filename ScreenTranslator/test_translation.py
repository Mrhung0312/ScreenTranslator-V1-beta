import os
import sys
import logging

sys.path.insert(0, r"d:\ScreenTranslator")

from core.processor import TranslationProcessor

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

def test_translation():
    print("--- Testing Translation Logic ---")
    if "LANGBLY_API_KEY" in os.environ:
        del os.environ["LANGBLY_API_KEY"]

    processor = TranslationProcessor(None)

    print("\n[Test 1] Fallback translation without API key")
    result = processor.translate_langbly("Hello world")
    print(f"Result: {result}")

    print("\n[Test 2] Cache functionality")
    result_cached = processor.translate_langbly("Hello world")
    print(f"Result (cached): {result_cached}")

if __name__ == "__main__":
    test_translation()
