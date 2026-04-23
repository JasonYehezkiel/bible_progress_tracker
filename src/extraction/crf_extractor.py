import joblib
import logging
import numpy as np
from gensim.models import Word2Vec
from pathlib import Path
from typing import Any, Dict, List, Tuple

from logger import setup_logger
from extraction.ner_parser import parse_ner_response

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.extraction.crf_extractor')

BOOK_SEEDS = [
    'kej', 'kel', 'im', 'bil', 'ul',
    'yos', 'hak', 'rut', 'sam', 'raj',
    'mat', 'mar', 'luk', 'yoh', 'kis',
    'rom', 'kor', 'gal', 'ef', 'kol'
]

CHAPTER_SEEDS = ['1','2','3','4','5','6','7','8','9']

class CRFBibleReferenceExtractor:
    def __init__(self, crf_path: Path, w2v_path: Path):
        self.crf = joblib.load(crf_path)
        self.wv = Word2Vec.load(str(w2v_path)).wv
        logger.info(
            'CRFBibleReferenceExtractor ready — model: %s | W2V vocab: %d',
            crf_path.name, len(self.wv),
        )
    
    def w2v_sim(self, token: str, seeds: List[str]) -> float:
        """Average cosine similarity between a token and a list of seed words"""
        t = token.lower()
        if t not in self.wv:
            return 0.0
        sims = [self.wv.similarity(t, s) for s in seeds if s in self.wv]
        return float(np.mean(sims)) if sims else 0.0
    
    def featurize_token(self, tokens: List[str], i: int) -> Dict[str, Any]:
        """Feature dict for token at position i"""

        token = tokens[i]
        t = token.lower()

        features = {
            # Token shape
            'token.lower': t,
            'token.is_upper': token.isupper(),
            'token.is_title': token.istitle(),
            'token.is_digit': token.isdigit(),
            'token.has_hyphen': '-' in token,
            'token.has_digit': any(c.isdigit() for c in token),
            'token.prefix2': t[:2],
            'token.prefix3': t[:3],
            'token.suffix2': t[-2:],
            'token.suffix3': t[-3:],
            'token.length': len(token),
            'token.is_first': i == 0,
            'token.is_last': i == len(tokens) - 1,
            # Word2Vec Similarity
            'w2v.book_sim': round(self.w2v_sim(t, BOOK_SEEDS), 2),
            'w2v.chapter_sim': round(self.w2v_sim(t, CHAPTER_SEEDS), 2),
        }
        if i > 0:
            prev = tokens[i - 1]
            features.update({
                '-1:token.lower': prev.lower(),
                '-1:token.is_title': prev.istitle(),
                '-1:token.is_digit': prev.isdigit(),
                '-1:w2v.book_sim': round(self.w2v_sim(prev, BOOK_SEEDS), 2),
            })
        else:
            features['BOS'] = True
        
        if i < len(tokens) - 1:
            next = tokens[i + 1]
            features.update({
                '+1:token.lower': next.lower(),
                '+1:token.is_title': next.istitle(),
                '+1:token.is_digit': next.isdigit(),
                '+1:w2v.book_sim': round(self.w2v_sim(next, BOOK_SEEDS), 2),
            })
        else:
            features['EOS'] = True
        
        return features
    
    def featurize_sentence(self, tokens: List[str]) -> List[Dict[str, Any]]:
        return [self.featurize_token(tokens, i) for i in range(len(tokens))]
    
    def bio_to_token_spans(
            self, tokens: List[str], tags: List[str]
    ) -> List[Tuple[int, int, str]]:
        """Convert a BIO tag sequence to (start_idx, end_idx, span_text) tuple"""
        spans = []
        start = None

        for i, tag in enumerate(tags):
            if tag.startswith('B-'):
                if start is not None:
                    spans.append((start, i, ' '.join(tokens[start:i])))
                start = i
            elif tag.startswith('I-'):
                if start is None:
                    start = i
            else:
                if start is not None:
                    spans.append((start, i, ' '.join(tokens[start:i])))
                    start = None
            
        if start is not None:
            spans.append((start, len(tokens), ' '.join(tokens[start:])))
        
        return spans

    def predict_line(self, line: str) -> List[Tuple[str, str]]:
        """Tokenize a single line a return (token, BIO_tag) pairs."""
        tokens = line.split()
        if not tokens:
            return []
        tags = self.crf.predict([self.featurize_sentence(tokens)])[0]
        return list(zip(tokens, tags))
    
    @staticmethod
    def token_char_offsets(tokens: List[str]) -> List[int]:
        """Return the start character offset of each token assuming single-space"""
        offsets, pos = [], 0
        for tok in tokens:
            offsets.append(pos)
            pos += len(tok) + 1
        return offsets
    
    def extract_ner_spans(self, text: str) -> List[Dict[str, Any]]:
        result = []
        char_offset = 0

        for line in text.splitlines():
            token_tag_pairs = self.predict_line(line)

            if token_tag_pairs:
                tokens = [t for t, _ in token_tag_pairs]
                tags = [t for _, t in token_tag_pairs]
                offsets = self.token_char_offsets(tokens)
                tok_spans = self.bio_to_token_spans(tokens, tags)

                for start_idx, _, span_text in tok_spans:
                    abs_start = char_offset + offsets[start_idx]
                    result.append({
                        'start': abs_start,
                        'end': abs_start + len(span_text),
                        'label': 'BIBLE_REF',
                        'text': span_text,
                    })
            
            char_offset += len(line) + 1
        
        return result
    
    def extract_structure(self, text: str) -> List[Dict[str, Any]]:
        spans = self.extract_ner_spans(text)
        span_texts = [s['text'] for s in spans]

        if not span_texts:
            return []
        
        parsed = parse_ner_response(span_texts)     

        if not parsed:
            for s in spans:
                first_tok = s['text'].split()
                if first_tok:
                    logger.debug('CRF span not regex-parseable: %r', s['text'])
                    parsed.append({
                        'book_start': first_tok[0],
                        'start_chapter': None,
                        'book_end': None,
                        'end_chapter': None,
                    })
 
        return parsed
    
