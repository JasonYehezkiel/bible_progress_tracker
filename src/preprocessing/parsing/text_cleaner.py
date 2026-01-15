import re
import unicodedata

def clean_text(text: str) -> str:
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
    ]

    for char in invisible_chars:
        text = text.replace(char, '')
    
    zero_width_chars = [
        '\u200B', # ZWSP
        '\u200C', # ZWNJ
        '\u200D', # ZWJ
        '\uFEFF' # BOM
    ]

    for char in zero_width_chars:
        text = text.replace(char, '')
    
    text = ''.join(
        char for char in text
        if unicodedata.category(char)[0] != 'C' or char in '\n\t'
    )

    text = re.sub(r'[^\S\n]+', ' ', text)

    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)

    text = text.strip('\n')

    return text
    