"""
Model loader - Handles loading models, tokenizers, and configurations
Support:

- Decoder-only models (LLMs) with Optional LoRA adapters
- Encoder-only models for:
    - Token classification (NER)
    - Sequence classification (Intent)
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

import torch

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    AutoModelForTokenClassification,
    AutoModelForSequenceClassification,
    PreTrainedModel,
    PreTrainedTokenizerBase
)
from peft import (
    LoraConfig, 
    get_peft_model, 
    PeftModel
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseModelLoader:
    """
    Base class for loading and managing LLM models.
    Handles Config/tokenizer initialization and LoRA adapters.
    """

    def __init__(self, config_path: str):
        """
        Initialize BaseModelLoader
        
        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        self.config = self.load_config()
        self.model_name = self.config['model_name']
        self.tokenizer: Optional[PreTrainedTokenizerBase] = None
        self.model: Optional[PreTrainedModel] = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        logger.info(f"Loading config from: {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load()
    
    def load_tokenizer(self, padding_side: str = "left") -> PreTrainedTokenizerBase:
        """
        Load and configure tokenizer.

        Args:
            padding_side: Side to pad tokens ('left' or 'right')
        
        Returns:
            Loaded Tokenizer
        """
        logger.info(f"Loading tokenizer: {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )

        # ensure padding token exists
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.tokenizer.padding_side = padding_side
        logger.info(f"Tokenizer loaded with padding_side={padding_side}")
        return self.tokenizer
    
class DecoderOnlyLoader(BaseModelLoader):
    """
    Loader for decoder-only language models.

    Support optional LoRA adapters for fine-tuning.
    """

    def load_model(
            self, 
            for_training: bool = False, 
            adapter_path: Optional[str] = None,
            **kwargs
            ) -> PreTrainedModel:
        """
        load decoder-only model

        Args:
            for_training: if True, prepare model for training with LoRA
            adapter_path: Path to pre-trained LoRA adapters
            **model_kwargs: Additional argument passed to from_pretrained()
                            (e.g., quantization config, torch_dtype, etc)
        
        Returns:
            Loaded decoder-only model
        """
        if self.tokenizer is None:
            self.load_tokenizer(padding_side="right" if for_training else "left")
        

        logger.info(f"Loading decoder-only model: {self.model_name}")
        logger.info(f"Model load kwargs: {kwargs}")

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            **kwargs,
        )

        # Apply LoRA if needed
        if adapter_path:
            logger.info(f"Loading LoRA adapters from: {adapter_path}")
            self.model = PeftModel.from_pretrained(self.model, adapter_path)
        
        elif for_training:
            logger.info("Preparing model for training with LoRA")
            self.model = self.add_lora_adapters(self.model)

        logger.info("Decoder-only model loaded successfully")
        return self.model
    
    def add_lora_adapters(self) -> PreTrainedModel:
        """Add LoRA adapters for decoder-only models"""

        lora_cfg = self.config.get("lora", {})
        
        lora_conifg = LoraConfig(
            r=lora_cfg.get("r", 8),
            lora_alpha=lora_cfg.get("lora_alpha", 16),
            lora_dropout=lora_cfg.get("lora_dropout", 0.05),
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=lora_cfg.get(
                "target_modules", 
                ["q_proj", "v_proj"]
            ),
        )

        model = get_peft_model(self.model, lora_conifg)
        model.print_trainable_parameters()
        return model

class EncoderNERLoader(BaseModelLoader):
    """
    Loads encoder-only language models for NER (Token Classification).
    """

    def load_model(self, num_labels: int) -> PreTrainedModel:
        """
        load encoder-only model

        Args:
            num_labels: Number of labels for token classification
        
        Returns:
            Loaded encoder-only model for NER
        """
        if self.tokenizer is None:
            self.load_tokenizer(padding_side="right")
        
        logger.info(f"Loading encoder-only NERmodel: {self.model_name}")


        self.model = AutoModelForTokenClassification.from_pretrained(
            self.model_name,
            num_labels=num_labels,
        )


        logger.info("Encoder-only NER model loaded successfully")
        return self.model
    
class EncoderIntentLoader(BaseModelLoader):
    """
    Loads encoder-only language models for Intent Classification (Sequence Classification).
    """

    def load_model(self, num_labels: int) -> PreTrainedModel:
        """
        load encoder-only model

        Args:
            num_labels: Number of labels for sequence classification
        
        Returns:
            Loaded encoder-only model for Intent Classification
        """
        if self.tokenizer is None:
            self.load_tokenizer(padding_side="right")
        
        logger.info(f"Loading encoder-only Intent model: {self.model_name}")


        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=num_labels,
        )


        logger.info("Encoder-only Intent model loaded successfully")
        return self.model