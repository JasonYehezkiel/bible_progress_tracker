from typing import Dict, List, Any
from src.models.llm_handler import BaseLLMHandler
import re
import json
import logging

logger = logging.getLogger(__name__)

class LLMExtractor:
    """
    Uses an LLM to extract Bible reference CANDIDATES.
    """
    def __init__(self, llm_handler: BaseLLMHandler, prompt_template: str):
        self.llm = llm_handler
        self.prompt = prompt_template
        logger.info("LLMExtractor initialized.")
    
    def extract(self, message: str) -> Dict[str, Any]:
        """Extract from a single message"""
        prompt = self.prompt.format(message=message)
        response = self.llm.generate(prompt, mode="extraction")
        return response
    
    def extract_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        prompts = [self.prompt.format(message=msg) for msg in messages]
        responses = self.llm.generate_batch(prompts, mode="extraction")
        return [
            self.parse_response(resp, msg)
            for resp, msg in zip(responses, messages)
        ]
    
    def parse_response(self, response: str, message: str) -> Dict[str, Any]:
        
        if not response or not response.strip():
            return [self.empty_result(message)]
        try:
            json_text = self.extract_json(response)
            logger.debug(f"Extracted JSON text: {json_text}")

            data = json.loads(json_text)
            
            if isinstance(data, list):
                if not data:
                    return [self.empty_result(message)]
                
                results = []
                for item in data:
                    results.append({
                        "book_text": item.get("book_text"),
                        "start_chapter": item.get("start_chapter"),
                        "end_chapter": item.get("end_chapter"),
                        "raw_text": message,
                        "confidence": item.get("confidence", 0.7),
                        "source": "llm"
                    })
                return results
            
        except Exception:
            return [self.empty_result(message)]
    
    @staticmethod
    def extract_json(text: str) -> str:
        matches = re.findall(r"\{[\s\S]*?\}", text)
        if not matches:
            raise ValueError("No JSON Object found")
        return matches[-1]
    
    @staticmethod
    def empty_result(message: str) -> Dict[str, Any]:
        return {
                "book_text": None,
                "start_chapter": None,
                "end_chapter": None,
                "raw_text": message,
                "confidence": 0.0,
                "source": "llm"
            }
            