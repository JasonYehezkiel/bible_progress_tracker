from typing import Optional

INVISIBLE_CHARS = [
    '\u200e',
    '\u200f',
    '\u202a',
    '\u202b',
    '\u202c',
    '\u202d',
    '\u202e',
    '\ufeff'
]

def clean_text(text: Optional[str]) -> Optional[str]:

    if text is None:
        return None
    
    for ch in INVISIBLE_CHARS:
        text = text.replace(ch, '')
    
    return text.strip()
