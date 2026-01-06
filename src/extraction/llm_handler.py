from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import json

class BaseLLMHandler(ABC):
    """Base class for all LLM handlers"""

    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.model_name = self.config['model_name']
        self.max_tokens = self.config.get('max_tokens', 512)
        self.temperature = self.config.get('temperature', 0.1)
    
    def load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def extract_bible_reference(self, message: str) -> Dict:
        pass

class SahabatAIHandler(BaseLLMHandler):
    """Handler for Sahabat-AI model"""

    def __init__(self, config_path: str = 'config/sahabat_ai_config.json'):
        super().__init__(config_path)
        self.client - self.initialize_client()
    
    def initialize_client(self):
        pass

    def generate(self, prompt: str,  **kwargs) -> str:
        pass

    def extract_bible_reference(self, message) -> Dict:
        pass

    def parse_response(self, response: str) -> Dict:
        pass

class KomodoHandler(BaseLLMHandler):
    """Handler for Komodo-7B model"""

    def __init__(self, config_path: str = 'config/sahabat_ai_config.json'):
        super().__init__(config_path)
        self.client - self.initialize_client()
    
    def initialize_client(self):
        pass

    def generate(self, prompt: str,  **kwargs) -> str:
        pass

    def extract_bible_reference(self, message) -> Dict:
        pass

    def parse_response(self, response: str) -> Dict:
        pass

class CendolHandler(BaseLLMHandler):
    """Handler for Cendol model"""

    def __init__(self, config_path: str = 'config/sahabat_ai_config.json'):
        super().__init__(config_path)
        self.client - self.initialize_client()
    
    def initialize_client(self):
        pass

    def generate(self, prompt: str,  **kwargs) -> str:
        pass

    def extract_bible_reference(self, message) -> Dict:
        pass

    def parse_response(self, response: str) -> Dict:
        pass

class LLMFactory:

    @staticmethod
    def create_hander(model_name: str) -> BaseLLMHandler:
        handlers = {
            'sahabat-ai': SahabatAIHandler,
            'komodo': KomodoHandler,
            'cendol': CendolHandler
        }
        handler_class = handlers.get(model_name.lower())
        if not handler_class:
            raise ValueError(f"Unknown model: {model_name}")
        
        return handler_class()