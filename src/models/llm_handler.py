from abc import ABC, abstractmethod
from typing import Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline
import os
import torch
import json

class BaseLLMHandler(ABC):
    """
    Base class for all LLM handlers.
    """

    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)

        self.model_name = self.config['model_name']
        self.max_tokens = self.config.get('max_new_tokens', 200)
        self.temperature = self.config.get('temperature', 0.7)
        self.top_p = self.config.get('top_p', 0.9)
        self.device = 0 if torch.cuda.is_available() else -1

        self.client = self.initialize_client()
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @abstractmethod
    def initialize_client(self):
        pass
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

class HuggingFaceLLMHandler(BaseLLMHandler):
    """
    HuggingFace Transformers-based LLM handler (4-bit quantized).
    """
    def initialize_client(self):
        # Quantization_config
        quant_cfg = self.config.get("quantization", {})

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=quant_cfg.get("load_in_4bit", True),
            bnb_4bit_use_double_quant=quant_cfg.get("bnb_4bit_use_double_quant", True),
            bnb_4bit_quant_type=quant_cfg.get("bnb_4bit_quant_type", "nf4"),
            bnb_4bit_compute_dtype=torch.float16
        )
        # load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map="auto",
            quantization_config=bnb_config
        )

        return pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer
        )

    def generate(self, prompt: str, **kwargs) -> str:

        output = self.client(
            prompt,
            max_new_tokens = kwargs.get("max_new_tokens", self.max_tokens),
            temperature = kwargs.get("temperature", self.temperature),
            top_p = kwargs.get("top_p", self.top_p),
            do_sample=True
        )
        return output[0]['generated_text']

class LLMFactory:

    CONFIG_PATHS = {
            'sahabat-ai': 'config/sahabat_ai_config.json',
            'komodo': 'config/komodo_ai_config.json',
            'cendol': 'config/cendol_config.json'
        }

    @staticmethod
    def create_handler(model_name: str) -> BaseLLMHandler:
        config_path = LLMFactory.CONFIG_PATHS.get(model_name.lower())
        if not config_path:
            raise ValueError(f"Unknown model: {model_name}")
        
        return HuggingFaceLLMHandler(config_path)