# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/storage/artifact_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Chunked storage for uploaded images/logs with metadata

import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArtifactStore:
    """Chunked storage for artifacts."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize artifact store.
        
        Args:
            storage_dir: Storage directory path
        """
        self.storage_dir = Path(storage_dir or os.environ.get('ARTIFACT_STORAGE_DIR', '/var/lib/ransomeye/assistant_advanced/artifacts'))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata file
        self.metadata_file = self.storage_dir / 'metadata.json'
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """Save metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def store_artifact(self, artifact_id: str, file_path: str, mime_type: str, metadata: Dict[str, Any]):
        """
        Store artifact.
        
        Args:
            artifact_id: Unique artifact identifier
            file_path: Path to source file
            mime_type: MIME type
            metadata: Additional metadata
        """
        # Create artifact directory
        artifact_dir = self.storage_dir / artifact_id
        artifact_dir.mkdir(exist_ok=True)
        
        # Copy file to storage
        source_path = Path(file_path)
        dest_path = artifact_dir / source_path.name
        
        try:
            shutil.copy2(source_path, dest_path)
            
            # Calculate file hash
            file_hash = self._calculate_hash(dest_path)
            
            # Store metadata
            self.metadata[artifact_id] = {
                'file_path': str(dest_path),
                'mime_type': mime_type,
                'file_hash': file_hash,
                'size': dest_path.stat().st_size,
                'metadata': metadata,
                'stored_at': str(Path(dest_path).stat().st_mtime)
            }
            
            self._save_metadata()
            
            logger.info(f"Stored artifact: {artifact_id} ({dest_path.name})")
            
        except Exception as e:
            logger.error(f"Error storing artifact: {e}", exc_info=True)
            raise
    
    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get artifact metadata.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            Artifact metadata or None
        """
        return self.metadata.get(artifact_id)
    
    def get_artifact_file(self, artifact_id: str) -> Optional[Path]:
        """
        Get artifact file path.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            Path to artifact file or None
        """
        artifact_info = self.metadata.get(artifact_id)
        if artifact_info:
            file_path = Path(artifact_info['file_path'])
            if file_path.exists():
                return file_path
        return None
    
    def _calculate_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash hex string
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def list_artifacts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all artifacts.
        
        Args:
            limit: Maximum number of artifacts to return
            
        Returns:
            List of artifact metadata
        """
        artifacts = []
        for artifact_id, info in list(self.metadata.items())[:limit]:
            artifacts.append({
                'artifact_id': artifact_id,
                **info
            })
        return artifacts

