# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/multi_modal/multi_modal.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Multi-modal orchestrator that routes files to OCR, Vision, and captioning pipelines

import os
import mimetypes
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .image_pipeline import ImagePipeline
from .ocr.ocr_runner import OCRRunner
from .vision.det_runner import VisionDetector
from .image_captioner.captioner import ImageCaptioner

# Import metrics (with safe fallback)
try:
    from ..metrics.exporter import record_ocr_latency, record_vision_latency
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiModalOrchestrator:
    """Orchestrates multi-modal processing (OCR, Vision, Captioning)."""
    
    def __init__(self):
        """Initialize multi-modal orchestrator."""
        self.image_pipeline = ImagePipeline()
        self.ocr_runner = OCRRunner()
        self.vision_detector = VisionDetector()
        self.captioner = ImageCaptioner()
    
    def process_artifact(self, file_path: Path, artifact_id: str) -> Dict[str, Any]:
        """
        Process an artifact through multi-modal pipeline.
        
        Args:
            file_path: Path to artifact file
            artifact_id: Unique artifact identifier
            
        Returns:
            Dictionary with OCR text, detected objects, and scene description
        """
        result = {
            'artifact_id': artifact_id,
            'ocr_text': None,
            'detected_objects': [],
            'scene_description': None
        }
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Check if it's an image
        if mime_type and mime_type.startswith('image/'):
            result.update(self._process_image(file_path))
        elif mime_type == 'application/pdf':
            # Extract images from PDF and process
            result.update(self._process_pdf(file_path))
        else:
            logger.warning(f"Unsupported file type: {mime_type}")
        
        return result
    
    def _process_image(self, file_path: Path) -> Dict[str, Any]:
        """
        Process an image file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Processing results
        """
        result = {
            'ocr_text': None,
            'detected_objects': [],
            'scene_description': None
        }
        
        try:
            # Preprocess image
            processed_image = self.image_pipeline.preprocess(file_path)
            
            # Run OCR with timing
            ocr_start = time.time()
            ocr_text = self.ocr_runner.extract_text(processed_image)
            ocr_latency = time.time() - ocr_start
            result['ocr_text'] = ocr_text
            if METRICS_AVAILABLE:
                record_ocr_latency(ocr_latency)
            
            # Run vision detection with timing
            vision_start = time.time()
            detected_objects = self.vision_detector.detect(processed_image)
            vision_latency = time.time() - vision_start
            result['detected_objects'] = detected_objects
            if METRICS_AVAILABLE:
                record_vision_latency(vision_latency)
            
            # Generate scene description
            scene_description = self.captioner.caption(
                ocr_text=ocr_text,
                detected_objects=detected_objects
            )
            result['scene_description'] = scene_description
            
        except Exception as e:
            logger.error(f"Error processing image: {e}", exc_info=True)
        
        return result
    
    def _process_pdf(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a PDF file (extract images and process).
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Processing results
        """
        result = {
            'ocr_text': None,
            'detected_objects': [],
            'scene_description': None
        }
        
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text_parts = []
                    
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            text = page.extract_text()
                            if text:
                                text_parts.append(text)
                        except Exception as e:
                            logger.warning(f"Error extracting text from PDF page {page_num}: {e}")
                    
                    result['ocr_text'] = '\n\n'.join(text_parts)
                    result['scene_description'] = f"PDF document with {len(text_parts)} pages"
            except ImportError:
                logger.warning("PyPDF2 not available, falling back to OCR-only")
                # Fallback: treat as image and OCR
                result.update(self._process_image(file_path))
        except Exception as e:
            logger.error(f"Error processing PDF: {e}", exc_info=True)
        
        return result
    
    def is_ocr_available(self) -> bool:
        """Check if OCR is available."""
        return self.ocr_runner.is_available()
    
    def is_vision_available(self) -> bool:
        """Check if vision detection is available."""
        return self.vision_detector.is_available()

