"""
Text cleaning utilities for OCR output.

Lightweight functions to improve raw OCR text quality before translation.
No heavy NLP dependencies — uses only stdlib `re`.
"""

import re

# ── Precompiled patterns (compiled once, reused every call) ──────────────

# Matches sequences of single letters separated by single spaces (≥3 letters).
# "H e l l o" matches.  Need ≥3 to avoid matching things like "I a".
_SPACED_LETTERS_RE = re.compile(
    r'(?:(?<=\s)|(?<=^))'                      # after whitespace / start
    r'(?:[A-Za-z\u00C0-\u024F] ){2,}'          # 2+ single letters each followed by space
    r'[A-Za-z\u00C0-\u024F]'                   # final letter (no trailing space)
    r'(?=\s|$)'                                 # before whitespace / end
)

# Matches short fragments (1-2 chars each) separated by single spaces.
# "wor ld" — two fragments each 2-3 chars, likely a broken word.
_SHORT_FRAGMENT_RE = re.compile(
    r'(?:(?<=\s)|(?<=^))'
    r'(?:[A-Za-z\u00C0-\u024F]{2,3} )'         # first fragment 2-3 chars + space
    r'[A-Za-z\u00C0-\u024F]{2,3}'              # second fragment 2-3 chars
    r'(?=\s|$)'
)

# Multiple whitespace → single space.
_MULTI_SPACE_RE = re.compile(r'[ \t]+')

# Noise characters: anything that is NOT a letter, digit, or common punctuation.
_NOISE_RE = re.compile(
    r'[^\w\s'
    r'.,;:!?\'"()\[\]{}\-–—/\\@#$%&*+=<>~`^'
    r'\u3000-\u303F'          # CJK punctuation
    r'\uFF00-\uFFEF'          # fullwidth forms
    r']',
    re.UNICODE,
)

# Spaces around punctuation that shouldn't have a leading space.
_SPACE_BEFORE_PUNCT_RE = re.compile(r'\s+([.,;:!?)\]}])')
_SPACE_AFTER_OPEN_RE   = re.compile(r'([(\[{])\s+')

# Allowed characters checklist for filter_text based on user specifications:
# Letters, numbers, spaces (\w, \s), punctuation, and useful math/currency symbols.
_FILTER_TEXT_RE = re.compile(
    r'[^\w\s.,!?:;\'"()\[\]{}%+\-*/=<>$\-]', 
    re.UNICODE
)

# Common short words (1-3 chars) that should NOT be merged with neighbours.
_COMMON_SHORT_WORDS = frozenset({
    'a', 'i', 'an', 'am', 'as', 'at', 'be', 'by', 'do', 'go', 'he', 'if',
    'in', 'is', 'it', 'me', 'my', 'no', 'of', 'on', 'or', 'so', 'to', 'up',
    'us', 'we', 'ok', 'oh', 'the', 'and', 'for', 'are', 'but', 'not', 'you',
    'all', 'any', 'can', 'had', 'her', 'his', 'how', 'its', 'may', 'new',
    'now', 'old', 'our', 'out', 'own', 'say', 'she', 'too', 'use', 'was',
    'way', 'who', 'did', 'get', 'has', 'him', 'let', 'one', 'two', 'set',
    'try', 'ask', 'own', 'why', 'big', 'few', 'got', 'per', 'put', 'run',
    'top', 'yet',
})


def _merge_spaced_letters(match: re.Match) -> str:
    """Merge single-char-spaced sequences, respecting common short words.

    For "a t e s t" → check if "a" is a common word. If so, split:
    keep "a" separate and merge the rest → "a test".
    """
    fragment = match.group(0)
    chars = fragment.split(' ')

    # If first char is a common short word, keep it separate and merge rest
    if chars[0].lower() in _COMMON_SHORT_WORDS and len(chars) > 3:
        return chars[0] + ' ' + ''.join(chars[1:])

    # If last char is a common short word, keep it separate
    if chars[-1].lower() in _COMMON_SHORT_WORDS and len(chars) > 3:
        return ''.join(chars[:-1]) + ' ' + chars[-1]

    return ''.join(chars)


def _merge_short_fragments(match: re.Match) -> str:
    """Merge short OCR fragments like 'wor ld' → 'world'.

    Skip merging if both fragments are common standalone words.
    """
    fragment = match.group(0)
    parts = fragment.split(' ')
    lower_parts = [p.lower() for p in parts]

    # If ALL parts are common words, don't merge ("to be" should stay)
    if all(p in _COMMON_SHORT_WORDS for p in lower_parts):
        return fragment

    # If any part is a common word AND the other parts are also common → skip
    # Otherwise merge (at least one fragment looks like a broken piece)
    common_count = sum(1 for p in lower_parts if p in _COMMON_SHORT_WORDS)
    if common_count == len(parts):
        return fragment

    return ''.join(parts)


def _fix_broken_words(text: str) -> str:
    """Fix OCR-broken words using a multi-strategy approach.

    Strategy 1: Merge runs of single letters separated by single spaces.
                "H e l l o" → "Hello"

    Strategy 2: Merge pairs of very short fragments (2-3 chars each) that
                are likely halves of a broken word.
                "wor ld" → "world"
    """
    # Strategy 1: Single-letter sequences (high confidence)
    prev = None
    while prev != text:
        prev = text
        text = _SPACED_LETTERS_RE.sub(_merge_spaced_letters, text)

    # Strategy 2: Short-fragment two-piece merging (moderate confidence)
    text = _SHORT_FRAGMENT_RE.sub(_merge_short_fragments, text)

    return text


def clean_text(text: str) -> str:
    """Clean raw OCR text for translation.

    Pipeline (order matters):
    1. Replace newlines / carriage returns with spaces.
    2. Remove obvious noise characters.
    3. Normalize whitespace to single spaces.
    4. Fix broken (single-char-spaced) words and short fragments.
    5. Collapse spaces again after merging.
    6. Fix punctuation spacing.
    7. Strip leading / trailing whitespace.

    The function is intentionally lightweight — no NLP, no network calls.

    Parameters
    ----------
    text : str
        Raw OCR string.

    Returns
    -------
    str
        Cleaned text ready for translation.

    Examples
    --------
    >>> clean_text("H e l l o   wor ld \\n this   is  a t e s t")
    'Hello world this is a test'
    """
    if not text:
        return ""


    result = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

    result = _NOISE_RE.sub('', result)

    result = _MULTI_SPACE_RE.sub(' ', result)

    result = _fix_broken_words(result)

    result = _MULTI_SPACE_RE.sub(' ', result)

    result = _SPACE_BEFORE_PUNCT_RE.sub(r'\1', result)
    result = _SPACE_AFTER_OPEN_RE.sub(r'\1', result)

    return result.strip()


def filter_text(text: str) -> str:
    """
    Loại bỏ các emoji, ký hiệu UI, và ký tự thừa khỏi văn bản đầu ra của OCR.
    Giữ lại nội dung văn bản có ý nghĩa, số, khoảng trắng, dấu chấm câu thông dụng,
    và các ký tự hữu ích. Tối ưu bằng re.

    Ví dụ:
    >>> filter_text("Hello ❤️ world ► 100% ready!!!")
    'Hello world 100% ready!!!'
    """
    if not text:
        return ""

    # Loại bỏ các ký tự không thuộc danh sách cho phép (whitelist)
    filtered = _FILTER_TEXT_RE.sub('', text)

    # Thay thế nhiều khoảng trắng thành một khoảng trắng duy nhất
    filtered = _MULTI_SPACE_RE.sub(' ', filtered)

    # Loại bỏ khoảng trắng thừa ở hai đầu
    return filtered.strip()
