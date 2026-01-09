from typing import Dict, Any
from src.models.llm_handler import BaseLLMHandler
import json

class LLMExtractor:
    """
    Uses an LLM to extract Bible reference CANDIDATES.
    """
    def __init__(self, llm_handler: BaseLLMHandler, prompt_template: str):
        self.llm = llm_handler
        self.prompt = prompt_template
    
    def extract(self, message: str) -> Dict[str, Any]:
        prompt = self.prompt.format(message=message)
        response = self.llm.generate(prompt)
        return self.parse_response(response, message)
    
    def parse_response(self, response: str, message: str) -> Dict[str, Any]:
        try:
            json_text = self.extract_json(response)
            data = json.loads(json_text)

            return {
                "book_text": data.get("book"),
                "start_chapter": data.get("start_chapter"),
                "end_chapter": data.get("end_chapter"),
                "raw_text": message,
                "confidence": data.get("confidence", 0.7),
                "source": "llm"
            }
            

        except Exception:
            return self.empty_result(message)
    
    @staticmethod
    def extract_json(text: str) -> str:
        start = text.find("{")
        end = text.find("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON Object found")
        return text[start:end + 1]
    
    @staticmethod
    def empty_result(message: str) -> Dict[str, Any]:
        return {
                "book_text": None,
                "start_chapter": None,
                "end_chapter": None,
                "raw_text": message,
                "confidence": 0.7,
                "source": "llm"
            }
            