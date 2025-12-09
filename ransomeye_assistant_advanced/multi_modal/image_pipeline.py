# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/multi_modal/image_pipeline.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Image preprocessing pipeline for OCR and Vision (resize, grayscale, normalization)

from pathlib import Path
from typing import Optional
import logging

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL/Pillow not available - image preprocessing disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImagePipeline:
    """Image preprocessing pipeline."""
    
    def __init__(self, max_size: int = 2048, target_size: Optional[tuple] = None):
        """
        Initialize image pipeline.
        
        Args:
            max_size: Maximum dimension for resizing
            target_size: Target size (width, height) or None for auto
        """
        self.max_size = max_size
        self.target_size = target_size
    
    def preprocess(self, image_path: Path) -> Path:
        """
        Preprocess image for OCR/Vision.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to preprocessed image (may be same file if no processing needed)
        """
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, returning original image path")
            return image_path
        
        try:
            # Load image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large
            if max(img.size) > self.max_size:
                ratio = self.max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {img.size} to {new_size}")
            
            # Apply target size if specified
            if self.target_size:
                img = img.resize(self.target_size, Image.Resampling.LANCZOS)
            
            # Save preprocessed image (overwrite original for simplicity)
            # In production, you might want to save to temp file
            img.save(image_path, 'PNG')
            
            return image_path
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}", exc_info=True)
            return image_path
    
    def to_grayscale(self, image_path: Path) -> Path:
        """
        Convert image to grayscale.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to grayscale image
        """
        if not PIL_AVAILABLE:
            return image_path
        
        try:
            img = Image.open(image_path)
            if img.mode != 'L':
                img = img.convert('L')
                img.save(image_path, 'PNG')
            return image_path
        except Exception as e:
            logger.error(f"Error converting to grayscale: {e}")
            return image_path

