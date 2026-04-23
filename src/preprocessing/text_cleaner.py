import re
import unicodedata

# Low-Level Cleaning Utilities

def remove_invisible_chars(text: str) -> str:
    """
    Remove direction markers and control characters
    while preserving \n amd \t.
    """
    if not text:
        return ""

    invisible_chars = [
        '\u200E', # LRM
        '\u200F', # RLM
        '\u202A', # LRE
        '\u202B', # RLE
        '\u202C', # PDF
        '\u202D', # LRO
        '\u202E', # RLO
        '\u200B', # ZWSP
        '\u200C', # ZWNJ
        '\u200D', # ZWJ
        '\uFEFF' # BOM
    ]

    for char in invisible_chars:
        text = text.replace(char, '')
    
    # Remove other control chars except newline & tab
    text = ''.join(
        char for char in text
        if unicodedata.category(char)[0] != 'C' or char in '\n\t'
    )

    return text

def normalize_whitespace(text: str) -> str:
    """
    Normalize internal whitespace but preserve line breaks.
    """
    # replace multiple spaces (not newline)
    text = re.sub(r'[^\S\n]+', ' ', text)

    # Strip each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # remove leading/trailing newlines
    text = text.strip('\n')

    return text

def clean_text(text: str) -> str:
    """
    Universal cleaning safe for all downstream tasks.
    """
    if not text:
        return ""
    
    text = remove_invisible_chars(text)
    text = normalize_whitespace(text)
    return text

