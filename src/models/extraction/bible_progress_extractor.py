from typing import List, Dict, Optional
from src.models.extraction.rule_based_extractor import RuleBasedExtractor
from src.models.extraction.llm_extractor import LLMExtractor
from src.models.llm_handler import BaseLLMHandler

class BibleProgressExtractor:

    def __init__(self, 
                 llm_handler: Optional[BaseLLMHandler] = None,
                 prompt_template: Optional[str] = None,
                 use_llm_first: bool = False
                 ):
        self.rule_extractor = RuleBasedExtractor()
        self.llm_extractor = None
        self.use_llm_first = use_llm_first

        if llm_handler and prompt_template:
            self.llm_extractor = LLMExtractor(llm_handler, prompt_template)
    
    def extract(self, message: str) -> List[Dict]:
         if self.use_llm_first and self.llm_extractor:
            try:
                llm_result = self.llm_extractor.extract(message)
                if llm_result.get('book_text'):
                    return [llm_result]
            except Exception:
                pass

         return self.rule_extractor.extract(message)
        
    def extract_batch(self, messages: List[str]) -> List[List[Dict]]:

        if not self.use_llm_first and not self.llm_extractor:
            return [self.rule_extractor.extract(msg) for msg in messages]
        
        try:
            llm_results = self.llm_extractor.extract_batch(messages)
        except Exception as e:
            print(f"LLM batch extraction failed: {e}")
            return [self.rule_extractor.extract(msg) for msg in messages]
        
        final_results = []
        for msg, result in zip(messages, llm_results):
            if result and result[0].get('book_text'):
                final_results.append([result])
            else:
                final_results.append(self.rule_extractor.extract(msg))
        
        return final_results