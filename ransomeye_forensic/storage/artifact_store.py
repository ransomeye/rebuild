# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/storage/artifact_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Filesystem management for chunked forensic artifacts

import os
import shutil
from pathlib import Path
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArtifactStore:
    """Manages storage of chunked forensic artifacts."""
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize artifact store.
        
        Args:
            storage_dir: Base directory for artifact storage
        """
        self.storage_dir = Path(storage_dir or os.environ.get(
            'ARTIFACT_STORAGE_DIR',
            '/home/ransomeye/rebuild/ransomeye_forensic/storage/artifacts'
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Artifact store initialized at: {self.storage_dir}")
    
    def get_artifact_dir(self, artifact_id: str) -> Path:
        """
        Get directory for an artifact.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            Path to artifact directory
        """
        return self.storage_dir / artifact_id
    
    def store_chunk(self, artifact_id: str, chunk_index: int, chunk_data: bytes) -> Path:
        """
        Store a chunk of an artifact.
        
        Args:
            artifact_id: Artifact identifier
            chunk_index: Chunk index
            chunk_data: Chunk data bytes
            
        Returns:
            Path to stored chunk file
        """
        artifact_dir = self.get_artifact_dir(artifact_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_path = artifact_dir / f"chunk_{chunk_index:06d}.zst"
        
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)
        
        logger.debug(f"Stored chunk {chunk_index} for artifact {artifact_id}")
        return chunk_path
    
    def store_chunks(self, artifact_id: str, chunks: List[tuple]) -> List[Path]:
        """
        Store multiple chunks.
        
        Args:
            artifact_id: Artifact identifier
            chunks: List of (chunk_index, chunk_data) tuples
            
        Returns:
            List of paths to stored chunk files
        """
        paths = []
        for chunk_index, chunk_data in chunks:
            path = self.store_chunk(artifact_id, chunk_index, chunk_data)
            paths.append(path)
        
        return paths
    
    def get_chunk_path(self, artifact_id: str, chunk_index: int) -> Path:
        """
        Get path to a chunk file.
        
        Args:
            artifact_id: Artifact identifier
            chunk_index: Chunk index
            
        Returns:
            Path to chunk file
        """
        artifact_dir = self.get_artifact_dir(artifact_id)
        return artifact_dir / f"chunk_{chunk_index:06d}.zst"
    
    def list_chunks(self, artifact_id: str) -> List[int]:
        """
        List all chunk indices for an artifact.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            List of chunk indices (sorted)
        """
        artifact_dir = self.get_artifact_dir(artifact_id)
        
        if not artifact_dir.exists():
            return []
        
        chunks = []
        for chunk_file in artifact_dir.glob("chunk_*.zst"):
            try:
                chunk_index = int(chunk_file.stem.split('_')[1])
                chunks.append(chunk_index)
            except (ValueError, IndexError):
                continue
        
        return sorted(chunks)
    
    def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete all chunks for an artifact.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            True if deletion successful, False otherwise
        """
        artifact_dir = self.get_artifact_dir(artifact_id)
        
        if not artifact_dir.exists():
            return False
        
        try:
            shutil.rmtree(artifact_dir)
            logger.info(f"Deleted artifact: {artifact_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete artifact {artifact_id}: {e}")
            return False
    
    def get_artifact_size(self, artifact_id: str) -> int:
        """
        Get total size of all chunks for an artifact.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            Total size in bytes
        """
        artifact_dir = self.get_artifact_dir(artifact_id)
        
        if not artifact_dir.exists():
            return 0
        
        total_size = 0
        for chunk_file in artifact_dir.glob("chunk_*.zst"):
            total_size += chunk_file.stat().st_size
        
        return total_size

