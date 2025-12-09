# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/llm_core/response_postproc.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Normalizes JSON output if LLM output is malformed

import json
import re
from typing import Dict, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponsePostprocessor:
    """
    Post-processes LLM responses to normalize JSON and fix common issues.
    """
    
    def __init__(self):
        """Initialize postprocessor."""
        pass
    
    def process(self, text: str, expected_format: str = 'text') -> Dict:
        """
        Process LLM output.
        
        Args:
            text: Raw LLM output
            expected_format: Expected format ('text', 'json', 'auto')
            
        Returns:
            Dictionary with processed text and metadata
        """
        processed = text.strip()
        format_detected = 'text'
        is_valid_json = False
        json_data = None
        
        # Try to detect and extract JSON
        if expected_format in ['json', 'auto']:
            json_result = self._extract_json(processed)
            if json_result:
                processed = json_result['text']
                format_detected = 'json'
                is_valid_json = json_result['valid']
                json_data = json_result.get('data')
        
        return {
            'text': processed,
            'format': format_detected,
            'is_valid_json': is_valid_json,
            'json_data': json_data,
            'original_length': len(text),
            'processed_length': len(processed)
        }
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """
        Extract and validate JSON from text.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Dictionary with extracted JSON info or None
        """
        # Try to find JSON object
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested objects
            r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # Arrays
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                json_str = match.group()
                try:
                    json_data = json.loads(json_str)
                    return {
                        'text': json_str,
                        'valid': True,
                        'data': json_data
                    }
                except json.JSONDecodeError:
                    continue
        
        # Try to fix common JSON issues
        fixed = self._fix_json_common_issues(text)
        if fixed:
            try:
                json_data = json.loads(fixed)
                return {
                    'text': fixed,
                    'valid': True,
                    'data': json_data
                }
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _fix_json_common_issues(self, text: str) -> Optional[str]:
        """
        Fix common JSON formatting issues.
        
        Args:
            text: Text with potential JSON
            
        Returns:
            Fixed JSON string or None
        """
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON-like structure
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return None
        
        json_str = json_match.group()
        
        # Fix common issues
        # 1. Trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # 2. Single quotes to double quotes
        json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
        
        # 3. Unquoted keys
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        
        return json_str

