from typing import Dict, List, Any, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline
from transformers.pipelines.pt_utils import KeyDataset
from datasets import Dataset
from tqdm import tqdm
import logging
import torch

from model_loader import ModelLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMHandler:
    """
    inference handler that uses ModelLoader.
    Support single and batch generation.
    """
    def  __init__(self, model_loader: ModelLoader, adapter_path: Optional[str] = None):
        """
        Initialize LLM inference handler.

        Args: 
            model_loader: ModelLoader instance
            adapter_path: Optional path to LoRA adapters for fine-tuned model
        """
        self.loader = model_loader
        self.config = model_loader.config

        # Load model for inference if not already loaded
        if self.loader.model is None:
            self.loader.load_model(for_training=False, adapter_path=adapter_path)
        
        self.model = self.loader.model
        self.tokenizer = self.loader.tokenizer
        self.pipeline = self.loader.create_pipeline()

        # Disable gradient for inference
        torch.set_grad_enabled(False)
        self.model.eval()

        logger.info("LLM handler initialized and ready!")

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
    
    def generation_config(self, mode: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get generation config for specified mode.

        Args:
            mode: Generation mode.
            overrides: Dictionary of config values to override
        
        Returns:
            Merged configuration dictionary
        """
        modes = self.config.get("mode", {})
        cfg = modes.get(mode, {}).copy()
        cfg.update(overrides)
        return cfg


    def generate(self, 
                 prompt: str, 
                 system_message: str, 
                 mode: str = "chat", 
                 **kwargs) -> str:
        """
        Generate single response.

        Args:
            prompt: Input prompt
            system_message: system instruction
            mode: Generation mode
            **kwargs: Additional generation params
        """
        return self.generate_batch([prompt], system_message=system_message, mode=mode, **kwargs)[0]
    
    def generate_batch(self, 
                   prompts: List[str], 
                   system_message: str = "", 
                   mode: str = "chat", 
                   **overrides) -> List[str]:
        
        """
        Generate batch response.

        Args:
            prompt: List of input prompts
            system_messages: system instruction for all prompts
            mode: Generation mode
            **overrides: Additional generation params
        """

        # Get generation config
        gen_cfg = self.generation_config(mode, overrides)
        gen_cfg['return_full_text'] = False

        # Remove sampling params if not using sampling
        if not gen_cfg.get("do_sample", False):
            gen_cfg.pop("temperature", None)
            gen_cfg.pop("top_p", None)
            gen_cfg.pop("top_k", None)

        # format prompts
        formatted = [self.format_prompt(p, system_message) for p in prompts]

        batch_size = self.config.get("batch_size", 4)
        logger.info(f"Generating {len(prompts)} prompts with batch_size={batch_size}, mode='{mode}'")
        logger.info(f"Generation config: {gen_cfg}")

        # Create dataset for batching
        dataset = Dataset.from_dict({"prompt": formatted})

        # Generate
        results = []
        for out in tqdm(
            self.client(
                KeyDataset(dataset, "prompt"),
                batch_size=batch_size,
                **gen_cfg
            ),
            total=len(dataset),
            desc="Processing batches",
            unit="msg"
        ):
            results.append(out[0]["generated_text"].strip())
            
        return results