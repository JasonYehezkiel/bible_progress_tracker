from typing import Optional
from pathlib import Path
import logging

from model_loader import ModelLoader
from llm_handler import LLMHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMFactory:

    PROJECT_ROOT = Path(__file__).parent.parent
    CONFIG_DIR = PROJECT_ROOT / "config"

    CONFIG_PATHS = {
            'sahabat-ai': 'sahabat_ai_config.json',
            'komodo': '..komodo_7b_config.json',
            'cendol': '.cendol_config.json'
        }

    @staticmethod
    def create_handler(model_name: str) -> ModelLoader:
        config_path = LLMFactory.CONFIG_PATHS.get(model_name.lower())
        if not config_path:
            raise ValueError(f"Unknown model: {model_name}")
        
        return LLMHandler(config_path)