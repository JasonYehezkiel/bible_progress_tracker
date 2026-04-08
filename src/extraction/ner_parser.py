import re
from typing import Dict, List, Optional, Tuple

Token = Tuple[str, str]

def build_reference(
        book_start: str,
        start_chapter: Optional[int],
        book_end: Optional[str],
        end_chapter: Optional[int]
        ) -> Dict:
    """Helper function to build a reference dictionary"""
    return {
        'book_start': book_start,
        'start_chapter': start_chapter,
        'book_end': book_end,
        'end_chapter': end_chapter,
    }

# Tokenizer

TOKEN_RE = re.compile(
    r"(?P<RANGE>[—–]|s\s*/\s*d)"
    r"|(?P<COLON>:)"
    r"|(?P<SEMI>;)"
    r"|(?P<COMMA>,)"
    r"|(?P<REDUPLICATED>[a-z]+2\b)"
    r"|(?P<NUM>\d+)"
    r"|(?P<WORD>[a-z]+(?:-[a-z]+)*)"
    r"|(?P<HYPHEN>-)"
    r"|(?P<SKIP>\s+|.)",
    re.IGNORECASE,
)

def tokenize(text: str) -> List[Token]:
    tokens = []
    for m in TOKEN_RE.finditer(text.lower()):
        kind = m.lastgroup
        if kind == "SKIP":
            continue
        value = m.group()
        if kind == "REDUPLICATED":
            root = value[:-1]
            kind, value = "WORD", f"{root}-{root}"
        if kind == "HYPHEN":
            kind, value = "RANGE", "-"
        tokens.append((kind, value))
    return tokens

# Book span reader
def read_book(tokens: List[Token], pos: int) -> Optional[Tuple[str, int]]:
    """Consume a book-name span. Returns (raw_string, next_pos) or None"""
    n = len(tokens)
    if pos >= n:
        return None
    
    parts: List[str] = []
    idx = pos

    # Optional prefix
    if idx < n and tokens[idx][0] == "NUM" and tokens[idx][1] in ("1", "2", "3"):
        parts.append(tokens[idx][1])
        idx +=1
    elif tokens[idx][0] == "WORD" and tokens[idx][1] in ("1", "2", "3"):
        parts.append(tokens[idx][1])
        idx +=1
    
    # At least one WORD required
    word_count = 0
    while idx < n and tokens[idx][0] == "WORD" and word_count < 3:
        parts.append(tokens[idx][1])
        idx +=1
        word_count += 1
    
    if word_count == 0:
        return None
    
    compound_roots = {"raja", "hakim"}
    last_word = parts[-1]
    if (idx + 1 < n
            and tokens[idx][0] == "RANGE"
            and idx + 1 < n
            and tokens[idx + 1][0] == "WORD"):
        next_word = tokens[idx + 1][1]
        if last_word == next_word or last_word in compound_roots or next_word in compound_roots:
            parts[-1] = f"{last_word}-{next_word}"
            idx += 2
            
    return " ".join(parts), idx


# Segement Parser
def parse_segment(
        tokens: List[Token],
        pos: int,
        ctx_book: Optional[str],
) -> Tuple[List[Dict], int, Optional[str]]:
    n = len(tokens)

    # "[NUM] - [NUM] [BOOK]"
    if (pos + 3 <= n
            and tokens[pos][0] == "NUM"
            and tokens[pos + 1][0] == "RANGE"
            and tokens[pos + 2][0] == "NUM"):
        start_n = tokens[pos][1]
        end_n = tokens[pos + 2][1]
        bm = read_book(tokens, pos + 3)
        if bm and not bm[0][0].isdigit():
            bare, new_pos = bm
            book_start = f"{start_n} {bare}"
            book_end = f"{end_n} {bare}"
            return [build_reference(book_start, None, book_end, None)], new_pos, book_end
    
    # Standard: [BOOK] [chapter_info]
    bm = read_book(tokens, pos)
    if bm:
        book_start, pos = bm
    elif ctx_book:
        book_start = ctx_book
    else:
        return [], pos + 1, ctx_book
    
    start_chapter: Optional[int] = None
    book_end: Optional[str] = None
    end_chapter: Optional[int] = None

    if pos < n and tokens[pos][0] == "NUM":
        start_chapter = int(tokens[pos][1])
        pos += 1

        # Consume verse annotation
        if pos < n and tokens[pos][0] == "COLON":
            pos += 1
            if pos < n and tokens[pos][0] == "NUM":
                pos += 1
            if pos < n and tokens[pos][0] == "RANGE":
                pos += 1
                if pos < n and tokens[pos][0] == "NUM":
                    pos += 1
        
        # Range operator
        if pos < n and tokens[pos][0] == "RANGE":
            pos += 1
            next_bm = read_book(tokens, pos)
            if next_bm:
                # Cross-book: "gal 6 - ef 2"
                book_end, pos = next_bm
                if pos < n and tokens[pos][0] == "NUM":
                    end_chapter = int(tokens[pos][1])
                    pos += 1
                # same book repeated
                if book_end == book_start:
                    book_end = None
            elif pos < n and tokens[pos][0] == "NUM":
                end_chapter = int(tokens[pos][1])
                pos += 1
        
        # Comma list -> One ref per chapter
        elif pos < n and tokens[pos][0] == "COMMA":
            chapters = [start_chapter]
            while pos < n and tokens[pos][0] == "COMMA":
                pos += 1
                if pos <  n and tokens[pos][0] == "NUM":
                    chapters.append(int(tokens[pos][1]))
                    pos += 1
            refs = [build_reference(book_start, ch, None, None) for ch in chapters]

            return refs, pos, book_start
    
    # Bare cross-book range with no chapters
    elif pos < n and tokens[pos][0] == "RANGE":
        pos += 1
        next_bm = read_book(tokens, pos)
        if next_bm:
            book_end, pos = next_bm
        
    ctx_out = book_end or book_start
    return [build_reference(book_start, start_chapter, book_end, end_chapter)], pos, ctx_out


def parse_ner_response(ner_text: str) -> List[Dict]:
    """
    Parse a BIBLE_REF NER extraction string into structured reference dict.

    Args:
        ner_text: NER output string
 
    Returns:
        List of build_reference() dicts. Empty list if input is unrecognised
    """
    tokens = tokenize(ner_text)
    refs: List[Dict] = []
    pos = 0
    ctx_book: Optional[str] = None

    while pos < len(tokens):
        if tokens[pos][0] == "SEMI":
            pos += 1
            continue
        new_refs, pos, ctx_book = parse_segment(tokens, pos, ctx_book)
        refs.extend(new_refs)
    
    return refs
