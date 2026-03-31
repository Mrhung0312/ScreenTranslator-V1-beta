"""Unit tests for core.text_cleaner.clean_text."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.text_cleaner import clean_text


def test_basic_example():
    inp = "H e l l o   wor ld \n this   is  a t e s t"
    out = clean_text(inp)
    assert out == "Hello world this is a test", f"Got: {out!r}"


def test_empty_and_whitespace():
    assert clean_text("") == ""
    assert clean_text("   ") == ""
    assert clean_text("\n\n\n") == ""


def test_newline_replacement():
    assert clean_text("hello\nworld") == "hello world"
    assert clean_text("hello\r\nworld") == "hello world"


def test_multi_space_collapse():
    assert clean_text("hello     world") == "hello world"


def test_broken_word_merge():
    assert clean_text("T e s t i n g") == "Testing"
    assert clean_text("A B C") == "ABC"


def test_mixed_broken_and_normal():
    result = clean_text("H e l l o world")
    assert result == "Hello world", f"Got: {result!r}"


def test_noise_removal():
    result = clean_text("Hello§ world¬")
    assert "§" not in result
    assert "¬" not in result
    assert "Hello" in result
    assert "world" in result


def test_punctuation_preserved():
    result = clean_text("Hello, world! How are you?")
    assert result == "Hello, world! How are you?"


def test_punctuation_spacing():
    result = clean_text("Hello ,  world !")
    assert result == "Hello, world!"


def test_keeps_numbers():
    result = clean_text("Item 42 costs $9.99")
    assert "42" in result
    assert "9.99" in result


def test_cjk_passthrough():
    """CJK text should pass through unharmed."""
    result = clean_text("こんにちは 世界")
    assert "こんにちは" in result
    assert "世界" in result


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
