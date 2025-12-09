# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/multi_modal/ocr/ocr_runner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: OCR runner using pytesseract wrapper for text extraction from images

import os
import subprocess
from pathlib import Path
from typing import Optional
import logging

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available - OCR disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRRunner:
    """OCR runner using Tesseract."""
    
    def __init__(self):
        """Initialize OCR runner."""
        self.available = self._check_tesseract()
        if not self.available:
            logger.warning("Tesseract not available - OCR will fail")
    
    def _check_tesseract(self) -> bool:
        """
        Check if Tesseract binary is available.
        
        Returns:
            True if Tesseract is available
        """
        if not TESSERACT_AVAILABLE:
            return False
        
        try:
            # Check if tesseract binary exists
            result = subprocess.run(
                ['which', 'tesseract'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Also try to get version
                version_result = subprocess.run(
                    ['tesseract', '--version'],
                    capture_output=True,
                    text=True
                )
                if version_result.returncode == 0:
                    logger.info(f"Tesseract available: {version_result.stdout.split()[1]}")
                    return True
            
            # Try Windows path
            if os.name == 'nt':
                tesseract_path = os.environ.get('TESSDATA_PREFIX', 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe')
                if os.path.exists(tesseract_path):
                    pytesseract.pytesseract.tesseract_cmd = tesseract_path
                    return True
            
            logger.error("Tesseract binary not found")
            return False
            
        except Exception as e:
            logger.error(f"Error checking Tesseract: {e}")
            return False
    
    def extract_text(self, image_path: Path, lang: str = 'eng') -> Optional[str]:
        """
        Extract text from image using OCR.
        
        Args:
            image_path: Path to image file
            lang: Language code (default: 'eng')
            
        Returns:
            Extracted text or None if OCR fails
        """
        if not self.available:
            logger.error("Tesseract not available - cannot extract text")
            raise RuntimeError("Tesseract OCR not available. Please install tesseract-ocr package.")
        
        try:
            # Extract text
            text = pytesseract.image_to_string(str(image_path), lang=lang)
            
            # Clean up text
            text = text.strip()
            
            if text:
                logger.info(f"Extracted {len(text)} characters from image")
                return text
            else:
                logger.warning("No text extracted from image")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting text with OCR: {e}", exc_info=True)
            return None
    
    def extract_with_boxes(self, image_path: Path, lang: str = 'eng') -> list:
        """
        Extract text with bounding boxes.
        
        Args:
            image_path: Path to image file
            lang: Language code
            
        Returns:
            List of dicts with text and bounding boxes
        """
        if not self.available:
            return []
        
        try:
            data = pytesseract.image_to_data(str(image_path), lang=lang, output_type=pytesseract.Output.DICT)
            
            boxes = []
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > 0:  # Confidence > 0
                    boxes.append({
                        'text': data['text'][i],
                        'confidence': int(data['conf'][i]),
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i]
                    })
            
            return boxes
            
        except Exception as e:
            logger.error(f"Error extracting text with boxes: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if OCR is available."""
        return self.available

