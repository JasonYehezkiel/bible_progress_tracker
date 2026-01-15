import json
import re
from typing import Dict
from src.models.llm_handler import BaseLLMHandler

class LLMIntentClassifier:
    """
    Binary intent classifier using strict JSON mode.
    """

    def __init__(self, llm_handler: BaseLLMHandler, prompt_template: str):
        self.llm_handler = llm_handler
        self.prompt =  prompt_template

    def classify(self, message: str) -> bool:
        prompt = self.prompt.format(message=message)
        response = self.llm_handler.generate(prompt, mode="intent")
        data = json.loads(self.extract_json(response))
        return bool(data.get('is_progress', False))
    
    @staticmethod
    def extract_json(text: str) -> str:
        matches = re.findall(r"\{[\s\S]*?\}", text)
        if not matches:
            raise ValueError("No JSON found")
        return matches[-1]