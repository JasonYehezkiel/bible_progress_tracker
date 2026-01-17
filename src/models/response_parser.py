from typing import List, Dict, Any
import json
import re
import logging

logger = logging.getLogger(__name__)

class BaseParser:
    """
    Base class for all response parsers
    """

    @staticmethod
    def remove_markdown(text: str) -> str:
        """Remove markdown code blocks from text"""
        cleaned = text.strip()
        match = re.search(
            r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", 
            cleaned,
            re.DOTALL
        )
        return match.group(1) if match else cleaned
    
    @staticmethod
    def extract_json_object(text: str) -> str:
        """Extract first complete JSON object from text"""
        cleaned = text.strip()
        
        start = cleaned.find("{")
        if start == -1:
            raise ValueError("No JSON Object found")
        
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(cleaned)):
            ch = cleaned[i]

            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue

            if not in_string:
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return cleaned[start:i+1]
            
        raise ValueError("Unmatched braces in JSON object")
    
    @staticmethod
    def extract_json_array(text: str) -> str:
        """Extract first complete JSON array from text"""
        cleaned = text.strip()

        start = cleaned.find("[")
        if start == -1:
            raise ValueError("No JSON array found")
        
        bracket_count = 0
        in_string = False
        escape_next = False

        for i in range(start, len(cleaned)):
            ch = cleaned[i]

            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue

            if not in_string:
                if ch == "[":
                    bracket_count += 1
                elif ch == "]":
                    bracket_count -= 1
                    if bracket_count == 0:
                        return cleaned[start:i+1]
            
        raise ValueError("Unmatched brackets in JSON array")


class IntentParser(BaseParser):
    """
    Parser for intent classification responses.
    """
    @staticmethod
    def parse(response: str) -> Dict[str, Any]:
        """
        Parse intent classification output.

        Args:
            response: Raw LLM output string
        Returns:
            {"is_progress_report": bool, "confidence": float}
        """
        try:
            cleaned = IntentParser.remove_markdown(response)
            json_text = IntentParser.extract_json_object(cleaned)
            data = json.loads(json_text)
            
            if not isinstance(data, dict):
                raise ValueError("Intent output is not a JSON Object")

            return {
                "is_progress_report": bool(data.get("is_progress_report", False)),
                "confidence": float(data.get("confidence", 0.0))
            }
            
        except Exception as e:
            logger.warning(f"Unexpected error in parse_response: {e}")
            logger.debug(f"Raw intent response: \n{response}")
            return {"is_progress_report": False, "confidence": 0.0}


class ExtractionParser(BaseParser):
    """
    Parser for Bible reference extraction responses.
    """
    @staticmethod
    def parse(response: str) -> List[Dict[str, Any]]:
        """
        Parse extraction output.

        Args:
            response: Raw LLM output string
        Returns:
            List of references: [{"book_text": str, "start_chapter: int, ... }]
        """
        try:
            cleaned = ExtractionParser.remove_markdown(response)
            json_text = ExtractionParser.extract_json_array(cleaned)
            data = json.loads(json_text)
            
            if not isinstance(data, list):
                raise ValueError("Extraction output is not a JSON array")
            
            results = []
            for item in data:
                if isinstance(item, Dict):
                    results.append({
                        "book_text": item.get("book_text", ""),
                        "start_chapter": item.get("start_chapter", 0),
                        "end_chapter": item.get("end_chapter", 0),
                        "raw_text": item.get("raw_text", ""),
                        "confidence": float(item.get("confidence", 1.0)),
                        "source": item.get("source", "llm")
                    })

            return results
            
        except Exception as e:
            logger.warning(f"Unexpected error in parse_response: {e}")
            logger.debug(f"Raw extraction response: \n{response}")
            return []