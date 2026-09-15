"""
Speech Normalizer for DeepCore TTS Pipeline.

Translates visual Markdown formatting, bullet points, asterisks, and symbols
into clean, natural spoken text before phonetic analysis by Kokoro/espeak-ng.
Zero cloud dependencies; pure deterministic regex transformations.
"""
import re

# Markdown formatting regexes
_BOLD_ASTERISK = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_ASTERISK = re.compile(r"\*([^*]+)\*")
_BOLD_UNDERSCORE = re.compile(r"__([^_]+)__")
_ITALIC_UNDERSCORE = re.compile(r"_([^_]+)_")
_HEADERS = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_INLINE_CODE = re.compile(r"`([^`]+)`")
_CODE_BLOCKS = re.compile(r"```[\s\S]*?```")
_MARKDOWN_LINKS = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_BULLETS = re.compile(r"^[ \t]*[-*•]\s+", re.MULTILINE)
_NUMBERED_LISTS = re.compile(r"^[ \t]*\d+\.\s+", re.MULTILINE)
_STRAY_ASTERISKS = re.compile(r"\*+")
_EXCESS_WHITESPACE = re.compile(r"[ \t]+")
_MULTIPLE_NEWLINES = re.compile(r"\n{2,}")

# Symbol substitutions for speech clarity
_SYMBOL_MAP = [
    (re.compile(r"\s*->\s*"), " to "),
    (re.compile(r"\s*-->\s*"), " to "),
    (re.compile(r"\s*=>\s*"), " leads to "),
    (re.compile(r"\s*&\s*"), " and "),
    (re.compile(r"(\d+)%"), r"\1 percent"),
    (re.compile(r"\b(e\.g\.|eg)\b", re.IGNORECASE), "for example"),
    (re.compile(r"\b(i\.e\.|ie)\b", re.IGNORECASE), "that is"),
    (re.compile(r"\bvs\.?\b", re.IGNORECASE), "versus"),
    (re.compile(r"\bw/\s*"), "with "),
    (re.compile(r"\bw/o\s*"), "without "),
]


def clean_text_for_speech(text: str) -> str:
    """
    Sanitize text to make it suitable for neural speech synthesis.
    Strips asterisks, markdown syntax, and visual formatting that causes
    phonemizers to pronounce 'asterisk asterisk' or stumble on symbols.
    """
    if not text:
        return ""

    # 1. Remove multi-line code blocks
    cleaned = _CODE_BLOCKS.sub("", text)

    # 2. Extract link text from markdown links: [text](url) -> text
    cleaned = _MARKDOWN_LINKS.sub(r"\1", cleaned)

    # 3. Extract text from inline code: `code` -> code
    cleaned = _INLINE_CODE.sub(r"\1", cleaned)

    # 4. Strip markdown bold and italics
    cleaned = _BOLD_ASTERISK.sub(r"\1", cleaned)
    cleaned = _ITALIC_ASTERISK.sub(r"\1", cleaned)
    cleaned = _BOLD_UNDERSCORE.sub(r"\1", cleaned)
    cleaned = _ITALIC_UNDERSCORE.sub(r"\1", cleaned)

    # 5. Remove headers (# Header -> Header)
    cleaned = _HEADERS.sub("", cleaned)

    # 6. Remove bullet indicators (- item -> item)
    cleaned = _BULLETS.sub("", cleaned)
    cleaned = _NUMBERED_LISTS.sub("", cleaned)

    # 7. Apply symbol substitutions
    for pattern, replacement in _SYMBOL_MAP:
        cleaned = pattern.sub(replacement, cleaned)

    # 8. Clean any remaining stray asterisks or brackets
    cleaned = _STRAY_ASTERISKS.sub("", cleaned)
    cleaned = re.sub(r"[\[\]{}|<>]", " ", cleaned)

    # 9. Clean up spacing and newlines
    cleaned = _EXCESS_WHITESPACE.sub(" ", cleaned)
    cleaned = _MULTIPLE_NEWLINES.sub(". ", cleaned)

    return cleaned.strip()
