# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/registry/model_storage.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Filesystem management for model storage with atomic writes

import os
import shutil
import tempfile
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelStorage:
    """Manages filesystem storage for model files with atomic operations."""
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize model storage.
        
        Args:
            storage_dir: Base directory for model storage (defaults to MODEL_STORAGE_DIR env var)
        """
        self.storage_dir = Path(storage_dir or os.environ.get(
            'MODEL_STORAGE_DIR', 
            '/home/ransomeye/rebuild/ransomeye_ai_core/storage/model_files'
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Model storage initialized at: {self.storage_dir}")
    
    def get_model_path(self, model_id: int, filename: str = None) -> Path:
        """
        Get the storage path for a model.
        
        Args:
            model_id: Model ID
            filename: Optional filename within the model directory
            
        Returns:
            Path to the model file or directory
        """
        model_dir = self.storage_dir / str(model_id)
        if filename:
            return model_dir / filename
        return model_dir
    
    def store_model_atomic(self, source_path: Path, model_id: int, 
                          final_filename: str = "model.bundle") -> Path:
        """
        Store a model file atomically (upload to temp -> verify -> rename).
        
        Args:
            source_path: Path to the source file to store
            model_id: Model ID for directory organization
            final_filename: Final filename for the stored file
            
        Returns:
            Path to the stored file
        """
        model_dir = self.get_model_path(model_id)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        final_path = model_dir / final_filename
        temp_path = model_dir / f".{final_filename}.tmp"
        
        try:
            # Copy to temporary location
            logger.info(f"Storing model {model_id} atomically from {source_path}")
            shutil.copy2(source_path, temp_path)
            
            # Verify file was copied successfully
            if not temp_path.exists() or temp_path.stat().st_size == 0:
                raise IOError(f"Failed to copy file to temporary location: {temp_path}")
            
            # Atomic rename (this is atomic on most filesystems)
            temp_path.rename(final_path)
            
            logger.info(f"Model stored successfully at: {final_path}")
            return final_path
            
        except Exception as e:
            # Clean up on failure
            if temp_path.exists():
                temp_path.unlink()
            if final_path.exists():
                final_path.unlink()
            logger.error(f"Failed to store model atomically: {e}")
            raise
    
    def extract_model_bundle(self, bundle_path: Path, model_id: int) -> Path:
        """
        Extract a model bundle to a directory.
        
        Args:
            bundle_path: Path to the .tar.gz bundle
            model_id: Model ID for directory organization
            
        Returns:
            Path to the extracted directory
        """
        import tarfile
        
        extract_dir = self.get_model_path(model_id)
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        temp_extract = extract_dir / ".extracting"
        
        try:
            logger.info(f"Extracting model bundle {bundle_path} to {temp_extract}")
            
            # Extract to temporary directory first
            with tarfile.open(bundle_path, 'r:gz') as tar:
                tar.extractall(temp_extract)
            
            # Verify extraction
            if not temp_extract.exists() or not any(temp_extract.iterdir()):
                raise IOError(f"Extraction failed or resulted in empty directory: {temp_extract}")
            
            # Move extracted files to final location
            for item in temp_extract.iterdir():
                dest = extract_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest))
            
            temp_extract.rmdir()
            
            logger.info(f"Model bundle extracted successfully to: {extract_dir}")
            return extract_dir
            
        except Exception as e:
            # Clean up on failure
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            logger.error(f"Failed to extract model bundle: {e}")
            raise
    
    def delete_model_files(self, model_id: int) -> bool:
        """
        Delete all files for a model.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if deletion successful, False otherwise
        """
        model_dir = self.get_model_path(model_id)
        
        if not model_dir.exists():
            logger.warning(f"Model directory does not exist: {model_dir}")
            return False
        
        try:
            shutil.rmtree(model_dir)
            logger.info(f"Deleted model files for model ID {model_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete model files: {e}")
            return False
    
    def get_model_file_path(self, model_id: int, relative_path: str) -> Path:
        """
        Get the full path to a file within a model's directory.
        
        Args:
            model_id: Model ID
            relative_path: Relative path within the model directory
            
        Returns:
            Full path to the file
        """
        model_dir = self.get_model_path(model_id)
        file_path = model_dir / relative_path
        
        # Security check: ensure the path is within the model directory
        try:
            file_path.resolve().relative_to(model_dir.resolve())
        except ValueError:
            raise ValueError(f"Path {relative_path} is outside model directory")
        
        return file_path
    
    def list_model_files(self, model_id: int) -> list:
        """
        List all files in a model's directory.
        
        Args:
            model_id: Model ID
            
        Returns:
            List of relative file paths
        """
        model_dir = self.get_model_path(model_id)
        
        if not model_dir.exists():
            return []
        
        files = []
        for root, dirs, filenames in os.walk(model_dir):
            root_path = Path(root)
            for filename in filenames:
                rel_path = root_path.relative_to(model_dir) / filename
                files.append(str(rel_path))
        
        return sorted(files)

