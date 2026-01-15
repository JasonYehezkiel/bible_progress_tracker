from typing import List, Dict
from src.models.extraction.bible_progress_extractor import BibleProgressExtractor
from src.preprocessing.normalization.bible_reference_normalizer import BibleReferenceNormalizer
from src.models.llm_handler import BaseLLMHandler

class BibleProgressPipeline:
    """
    Full Pipeline for Bible reading progress
    """

    def __init__(self, 
                 llm_handler: BaseLLMHandler = None, 
                 prompt_template: str =None, json_path=None):
        
        self.extractor = BibleProgressExtractor(
            llm_handler, 
            prompt_template)

        self.normalizer = BibleReferenceNormalizer(json_path)

    
    def process_message(self, message: str):
        candidates = self.extractor.extract(message)
        normalized = self.normalizer.normalize(candidates)
        return normalized

    def process_messages(self, messages: List[str]) -> List[Dict]:
        all_candidates = self.extractor.extract_batch(messages)

        all_results = []
        for candidates in all_candidates:
            normalized_results = []
            for candidate in candidates:
                normalized = self.normalizer.normalize(candidate)
                if normalized:
                    normalized_results.extend(normalized if isinstance(normalized, list) else [normalized])
            all_results.append(normalized_results)
        
        return all_results