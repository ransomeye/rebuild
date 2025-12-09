# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/multi_modal/image_captioner/captioner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Image captioner that combines OCR text and detected objects into scene descriptions

from typing import Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageCaptioner:
    """Image captioner that combines OCR and vision detections."""
    
    def __init__(self):
        """Initialize image captioner."""
        pass
    
    def caption(self, ocr_text: Optional[str] = None, detected_objects: Optional[List[str]] = None) -> str:
        """
        Generate scene description from OCR text and detected objects.
        
        Args:
            ocr_text: Extracted OCR text
            detected_objects: List of detected object class names
            
        Returns:
            Scene description string
        """
        parts = []
        
        # Add detected objects description
        if detected_objects:
            if len(detected_objects) == 1:
                parts.append(f"Contains {detected_objects[0]}")
            else:
                parts.append(f"Contains: {', '.join(detected_objects)}")
        
        # Add OCR text summary
        if ocr_text:
            # Extract key phrases (first 200 chars or first sentence)
            text_summary = ocr_text[:200].strip()
            if len(ocr_text) > 200:
                text_summary += "..."
            
            # Look for security-relevant keywords
            security_keywords = self._extract_security_keywords(ocr_text)
            if security_keywords:
                parts.append(f"Security keywords: {', '.join(security_keywords)}")
            
            parts.append(f"Text content: {text_summary}")
        
        # Combine into description
        if parts:
            description = ". ".join(parts)
        else:
            description = "Image processed (no significant content detected)"
        
        return description
    
    def _extract_security_keywords(self, text: str) -> List[str]:
        """
        Extract security-relevant keywords from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of security keywords found
        """
        keywords = []
        text_lower = text.lower()
        
        # Security-relevant keyword patterns
        security_patterns = {
            'ransom': ['ransom', 'encrypt', 'decrypt', 'bitcoin', 'payment'],
            'malware': ['malware', 'virus', 'trojan', 'backdoor', 'rootkit'],
            'error': ['error', 'failed', 'denied', 'access denied', 'permission'],
            'network': ['connection', 'firewall', 'blocked', 'port', 'ip address'],
            'system': ['registry', 'task manager', 'cmd', 'powershell', 'terminal']
        }
        
        for category, patterns in security_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    keywords.append(category)
                    break  # Only add category once
        
        return keywords

