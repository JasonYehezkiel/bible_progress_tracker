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

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.extraction.extractor')


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


    
    def extract(self, message: str, return_spans: bool = False) -> List[Dict]:
        return self.extract_batch([message], return_spans)[0]

    def extract_batch(self, messages: List[str], return_spans: bool = False) -> List[List[Dict]]:
        all_results = self.ner_pipeline(messages)
        ref_list = []
        for results in all_results:
            bible_hits = [r for r in results if r['entity_group'] == 'BIBLE_REF']
            for r in bible_hits:
                logger.debug("  %-12s | %-20s | score: %.4f", 
                             r['entity_group'], r['word'], r['score'])
            if return_spans:
                refs = [
                    {'start': r['start'], 'end': r['end'],
                    'label': r['entity_group'], 'text': r['word']}
                    for r in bible_hits
                ]
            else:
                span_texts = [r['word'] for r in bible_hits]
                refs = parse_ner_response(span_texts) if span_texts else []
                if not refs and span_texts:
                    logger.warning('NER span produced no parsed ref: %r', r['word'])
            ref_list.append(refs)
        return ref_list
    