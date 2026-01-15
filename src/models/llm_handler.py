from abc import ABC, abstractmethod
from typing import Dict, List, Any
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline
from transformers.pipelines.pt_utils import KeyDataset
from datasets import Dataset
from tqdm import tqdm
import logging
import torch
import json

logger = logging.getLogger(__name__)

class BaseLLMHandler(ABC):
    """
    Base class for all LLM handlers.
    Supports tasks-specific generation modes.
    """

    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)

        self.model_name = self.config['model_name']
        self.modes = self.config.get('modes', {})
        self.batch_size = self.config.get('batch_size', 4)

        torch.set_grad_enabled(False)
        self.client = self.initialize_client()
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generation_config(self, mode: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
        cfg = self.modes.get(mode, {}).copy()
        cfg.update(overrides)
        
        return cfg

    @abstractmethod
    def initialize_client(self):
        pass
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def generate_batch(self, prompt: List[str], **kwargs) -> str:
        pass

class HuggingFaceLLMHandler(BaseLLMHandler):
    """
    HuggingFace Transformers-based LLM handler (4-bit quantized).
    """
    def initialize_client(self):

        # load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "left"

        # Check if quantization is enabled
        quant_cfg = self.config.get("quantization", {})
        use_quantization = quant_cfg.get("enabled", False)

        if use_quantization:

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=quant_cfg.get("load_in_4bit", True),
                bnb_4bit_use_double_quant=quant_cfg.get("bnb_4bit_use_double_quant", True),
                bnb_4bit_quant_type=quant_cfg.get("bnb_4bit_quant_type", "nf4"),
                bnb_4bit_compute_dtype=torch.bfloat16,
            )

            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                quantization_config=bnb_config,
                trust_remote_code=True,
                offload_folder="./offload"
            )
        
        else:

            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                trust_remote_code=True,
                offload_folder="./offload",
                dtype="auto"
            )


        model.config.pad_token_id = tokenizer.pad_token_id
        model.generation_config.pad_token_id = tokenizer.pad_token_id

        return pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer
        )
    
    def format_prompt(self, user_text: str, system_msg: str = "") -> str:
        if system_msg:
            return f"""Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{system_msg}
### Input:
{user_text}
### Response:
"""
        else:
            return user_text


    def generate(self, prompt: str, system_message: str, mode: str = "chat", **kwargs) -> str:
        
        return self.generate_batch([prompt], system_message=system_message, mode=mode, **kwargs)[0]
    
    def generate_batch(self, 
                   prompts: List[str], 
                   system_message: str = "", 
                   mode: str = "chat", 
                   **overrides) -> List[str]:
        
        import time 

        start = time.time()
    
        gen_cfg = self.generation_config(mode, overrides)
        gen_cfg['return_full_text'] = False

        if not gen_cfg.get("do_sample", False):
            gen_cfg.pop("temperature", None)
            gen_cfg.pop("top_p", None)
            gen_cfg.pop("top_k", None)

        formatted = [self.format_prompt(p, system_message) for p in prompts]

        logger.info(f"Config time: {time.time() - start:.2f}s")
        logger.info(f"Batch size: {self.batch_size}, Num prompts: {len(prompts)}")
        logger.info(f"Gen config: {gen_cfg}")

        dataset = Dataset.from_dict({"prompt": formatted})

        results = []
        for out in tqdm(
            self.client(
                KeyDataset(dataset, "prompt"),
                batch_size=self.batch_size,
                **gen_cfg
            ),
            total=len(dataset),
            desc="Processing batches",
            unit="msg"
        ):
            results.append(out[0]["generated_text"].strip())
            
        logger.info(f"Total generation: {time.time() - start:.2f}s")
        return results


class LLMFactory:

    CONFIG_PATHS = {
            'sahabat-ai': '../config/sahabat_ai_config.json',
            'komodo': '../config/komodo_7b_config.json',
            'cendol': '../config/cendol_config.json'
        }

    @staticmethod
    def create_handler(model_name: str) -> BaseLLMHandler:
        config_path = LLMFactory.CONFIG_PATHS.get(model_name.lower())
        if not config_path:
            raise ValueError(f"Unknown model: {model_name}")
        
        return HuggingFaceLLMHandler(config_path)