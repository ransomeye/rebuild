# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/multi_modal/ocr/train_ocr.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Script to fine-tune Tesseract OCR configuration and language models

import os
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRTrainer:
    """Tesseract OCR trainer and configuration manager."""
    
    def __init__(self, tesseract_data_dir: str = None):
        """
        Initialize OCR trainer.
        
        Args:
            tesseract_data_dir: Custom Tesseract data directory
        """
        self.tesseract_data_dir = tesseract_data_dir or os.environ.get('TESSDATA_PREFIX', '/usr/share/tesseract-ocr/5/tessdata')
    
    def create_config_file(self, config_name: str, settings: dict) -> Path:
        """
        Create a Tesseract configuration file.
        
        Args:
            config_name: Name of config file
            settings: Dictionary of Tesseract settings
            
        Returns:
            Path to created config file
        """
        config_dir = Path('/tmp/tesseract_configs')
        config_dir.mkdir(exist_ok=True)
        
        config_path = config_dir / f"{config_name}.config"
        
        with open(config_path, 'w') as f:
            for key, value in settings.items():
                f.write(f"{key} {value}\n")
        
        logger.info(f"Created Tesseract config: {config_path}")
        return config_path
    
    def train_language_model(self, training_data_dir: Path, lang_code: str) -> bool:
        """
        Train a custom Tesseract language model (simplified interface).
        
        Args:
            training_data_dir: Directory containing training images and ground truth
            lang_code: Language code (e.g., 'eng', 'custom')
            
        Returns:
            True if training successful
        """
        # Note: Full Tesseract training requires:
        # 1. Training images (.tif)
        # 2. Ground truth text files (.gt.txt)
        # 3. Box files (.box)
        # 4. Running tesstrain.sh or manual training commands
        
        logger.info(f"Training language model '{lang_code}' from {training_data_dir}")
        logger.warning("Full Tesseract training requires manual setup - this is a placeholder interface")
        
        # Check if training data exists
        if not training_data_dir.exists():
            logger.error(f"Training data directory not found: {training_data_dir}")
            return False
        
        # In production, you would:
        # 1. Generate .box files from images
        # 2. Run tesstrain.sh or equivalent
        # 3. Combine traineddata files
        # 4. Install to tessdata directory
        
        return False
    
    def optimize_for_domain(self, domain: str) -> Path:
        """
        Create optimized config for specific domain (security screenshots, logs, etc.).
        
        Args:
            domain: Domain name ('security', 'log', 'general')
            
        Returns:
            Path to config file
        """
        domain_settings = {
            'security': {
                'tessedit_char_whitelist': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?/~`',
                'tessedit_pageseg_mode': '6',  # Uniform block of text
                'preserve_interword_spaces': '1'
            },
            'log': {
                'tessedit_char_whitelist': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:[]().-/_',
                'tessedit_pageseg_mode': '6',
                'preserve_interword_spaces': '1'
            },
            'general': {
                'tessedit_pageseg_mode': '3',  # Fully automatic
            }
        }
        
        settings = domain_settings.get(domain, domain_settings['general'])
        return self.create_config_file(f"{domain}_optimized", settings)

