import re
import emoji
import json
import logging
from pathlib import Path
from typing import List, Dict, Union

from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline
    )

from logger import setup_logger
from config.settings import CONFIG_PATH, AGGREGATION_STRATEGY, BATCH_SIZE
from extraction.ner_parser import parse_ner_response
from preprocessing.normalization.normalizer import BibleReferenceNormalizer

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.extraction.extractor')

BARE_RANGE = re.compile(r'^\d+\s*[-–]\s*\d+')
BOOK_NAME = re.compile(r'^((?:\d+\s*)?[A-Za-z]+(?:[-\s][A-Za-z]+)*)\.?\s*\d')

def load_ner_model(config_path: str, saved_path:str = None):
    config_path = Path(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    model_name = config["model_name"]

    if saved_path:
        logger.info('Loading model from saved path: %s', saved_path)
        tokenizer = AutoTokenizer.from_pretrained(saved_path)
        model = AutoModelForTokenClassification.from_pretrained(saved_path)
    else:
        logger.info('Loading pretrained model: %s', model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        labels = config["labels"]
        model = AutoModelForTokenClassification.from_pretrained(
            model_name, num_labels=len(labels)
        )
        model.config.id2label = {i: l for i, l in enumerate(labels)}
        model.config.label2id = {l: i for i, l in enumerate(labels)}
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = config.get("padding_side", "right")

    return model, tokenizer

def inject_book_context(message: str) -> str:
    """Carry forward the exact book name used in previous lines."""
    lines = message.splitlines()
    last_book = None
    result = []

    for line in lines:
        stripped = line.strip()
        book_match = BOOK_NAME.match(stripped)
        if book_match:
            last_book = book_match.group(1).strip()
            result.append(line)
        elif BARE_RANGE.match(stripped) and last_book:
            result.append(f"{last_book} {stripped}")
        else:
            result.append(line)
    
    return '\n'.join(result)

def preprocess(message) -> str:
    """Normalize a message before NER: coerce type,  expand emoji, collapse whitespace."""
    if isinstance(message, list):
        message = ' '.join(str(x) for x in message)
    elif not isinstance(message, str):
        message = str(message)
    
    message = emoji.replace_emoji(message, replace=lambda s, _: f" {s} ")
    message = inject_book_context(message)
    message = message.replace("\n", " ")
    message = re.sub(r" {2,}", " ", message).strip()

    return message

class BibleReferenceExtractor:
    """
    NER-model-based Bible reference extractor for chat messages.
    Handles preprocessing, entity extraction, parsing, and normalization.
    """

    def __init__(
            self, 
            saved_path: Union[str, Path],
            config_path: Union[str, Path] = CONFIG_PATH,
            aggregation_strategy: str = AGGREGATION_STRATEGY,
        ):

        model, tokenizer = load_ner_model(config_path, saved_path)

        self.ner_pipeline = pipeline(
            task='ner',
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy=aggregation_strategy,
            batch_size=BATCH_SIZE,
        )

        self.normalizer = BibleReferenceNormalizer()

    
    def extract(self, message: str) -> List[Dict]:
        return self.extract_batch([message])[0]

    def extract_batch(self, messages: List[str]) -> List[List[Dict]]:
        preprocessed = [preprocess(msg) for msg in messages]
        all_results = self.ner_pipeline(preprocessed)
        ref_list = []
        for results in all_results:
            refs = []
            for r in results:
                logger.debug("  %-12s | %-20s | score: %.4f", r['entity_group'], r['word'], r['score'])
                if r['entity_group'] == 'BIBLE_REF':
                    parsed = parse_ner_response(r['word'])
                    if not parsed:
                        logger.warning('NER span produced no parsed ref: %r', r['word'])
                        continue
                    refs.extend(self.normalizer.normalize(parsed))
            ref_list.append(refs)
        return ref_list
    
    def get_stats(self):
        return self.normalizer.get_stats()
    