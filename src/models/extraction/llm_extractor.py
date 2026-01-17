from typing import Dict, List, Any
from models.response_parser import ExtractionParser
from src.models.llm_handler import BaseLLMHandler
import logging

logger = logging.getLogger(__name__)

class LLMExtractor:
    """
    Uses an LLM to extract Bible reference CANDIDATES.
    """
    def __init__(self, llm_handler: BaseLLMHandler, system_prompt: str):
        self.llm = llm_handler
        self.system_prompt = system_prompt
        logger.info("LLMExtractor initialized.")
    
    def extract(self, message: str) -> Dict[str, Any]:
        """Extract from a single message"""
        response = self.llm.generate(
            prompt=message,
            system_message=self.system_prompt,
            mode="extraction"
        )
        return ExtractionParser.parse(response)
    
    def extract_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        responses = self.llm.generate_batch(
            prompt=messages,
            system_message=self.system_prompt,
            mode="extraction"
        )
        
        return [ExtractionParser.parse(resp) for resp in responses]        