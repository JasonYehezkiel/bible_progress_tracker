import json
import logging
import re
from typing import Dict, List, Any
from src.models.llm_handler import BaseLLMHandler
from src.models.response_parser import IntentParser

logger = logging.getLogger(__name__)

class LLMIntentClassifier:
    """
    Binary intent classifier using strict JSON mode.
    """

    def __init__(self, llm_handler: BaseLLMHandler, system_prompt: str):
        self.llm = llm_handler
        self.system_prompt =  system_prompt
        logger.info("LLMIntentClassifier initialized.")
    

    def classify(self, message: str) -> bool:
        """Classify if the message a progress report or not"""
        response = self.llm.generate(
            prompt=message,
            system_message=self.system_prompt,
            mode="intent"
        )
        return IntentParser.parse(response)
    
    def classify_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        responses = self.llm.generate_batch(
            prompt=messages,
            system_message=self.system_prompt,
            mode="intent"
        )
        return [IntentParser.parse(resp) for resp in responses]
