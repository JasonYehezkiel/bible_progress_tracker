from typing import List, Dict
from src.extraction.rule_based_extractor import RuleBasedExtractor
from src.extraction.llm_extractor import LLMExtractor
from src.models.llm_handler import BaseLLMHandler

class BibleProgressExtractor:

    def __init__(self, 
                 llm_handler: BaseLLMHandler = None,
                 prompt_template: str = None
                 ):
        self.rule_extractor = RuleBasedExtractor()
        self.use_llm = llm_handler is not None and prompt_template is not None

        if self.use_llm:
            self.llm_extractor = LLMExtractor(llm_handler, prompt_template)
    
    def extract(self, message: str) -> List[Dict]:
        candidates = []

        # rule-based extraction
        candidates.extend(self.rule_extractor.extract(message))

        # LLM extraction
        if self.use_llm:
            llm_candidate = self.llm_extractor.extract(message)
            if llm_candidate:
                candidates.append(llm_candidate)
        
        return candidates