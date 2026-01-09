from typing import List, Dict
from src.extraction.bible_progress_extractor import BibleProgressExtractor
from src.preprocessing.normalization.bible_reference_normalizer import BibleReferenceNormalizer
from src.models.llm_handler import BaseLLMHandler

class BibleProgressPipeline:
    """
    Full Pipeline for Bible reading progress (rule-based for now)
    """

    def __init__(self, llm_handler: BaseLLMHandler = None, prompt_template: str =None, json_path=None):
        
        self.extractor = BibleProgressExtractor(llm_handler, prompt_template)

        self.normalizer = BibleReferenceNormalizer(json_path)

    
    def process_messages(self, message: str):
        candidates = self.extractor.extract(message)

        normalized = self.normalizer.normalize(candidates)

        return normalized

    def process_messages_batch(self, messages: List[str]) -> List[Dict]:
        all_results = []
        for msg in messages:
            all_results.extend(self.process_messages(msg))
        return all_results