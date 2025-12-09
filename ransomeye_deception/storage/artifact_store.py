# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/storage/artifact_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Storage for generated decoy content and artifacts

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArtifactStore:
    """
    Storage for decoy artifacts and generated content.
    """
    
    def __init__(self):
        """Initialize artifact store."""
        self.storage_dir = Path(os.environ.get(
            'DECEPTION_ARTIFACT_DIR',
            str(Path(__file__).parent.parent.parent / 'ransomeye_deception' / 'artifacts')
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Artifact store initialized: {self.storage_dir}")
    
    def store_artifact(self, artifact_id: str, artifact_type: str,
                      content: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store artifact.
        
        Args:
            artifact_id: Artifact ID
            artifact_type: Type of artifact
            content: Artifact content (str, bytes, or dict)
            metadata: Optional metadata
            
        Returns:
            Path to stored artifact
        """
        try:
            # Create type-specific directory
            type_dir = self.storage_dir / artifact_type
            type_dir.mkdir(parents=True, exist_ok=True)
            
            artifact_path = type_dir / f"{artifact_id}.json"
            
            # Prepare storage data
            if isinstance(content, (dict, list)):
                data = {
                    'artifact_id': artifact_id,
                    'type': artifact_type,
                    'content': content,
                    'metadata': metadata or {},
                    'created_at': datetime.utcnow().isoformat()
                }
            else:
                data = {
                    'artifact_id': artifact_id,
                    'type': artifact_type,
                    'content': str(content),
                    'metadata': metadata or {},
                    'created_at': datetime.utcnow().isoformat()
                }
            
            # Write to file
            with open(artifact_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Artifact stored: {artifact_path}")
            return str(artifact_path)
            
        except Exception as e:
            logger.error(f"Error storing artifact: {e}")
            raise
    
    def get_artifact(self, artifact_id: str, artifact_type: str) -> Optional[Dict[str, Any]]:
        """
        Get artifact.
        
        Args:
            artifact_id: Artifact ID
            artifact_type: Type of artifact
            
        Returns:
            Artifact data dictionary or None
        """
        try:
            artifact_path = self.storage_dir / artifact_type / f"{artifact_id}.json"
            
            if not artifact_path.exists():
                return None
            
            with open(artifact_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error getting artifact: {e}")
            return None
    
    def list_artifacts(self, artifact_type: Optional[str] = None) -> List[str]:
        """
        List artifact IDs.
        
        Args:
            artifact_type: Optional filter by type
            
        Returns:
            List of artifact IDs
        """
        artifacts = []
        
        if artifact_type:
            type_dir = self.storage_dir / artifact_type
            if type_dir.exists():
                artifacts.extend([f.stem for f in type_dir.glob("*.json")])
        else:
            for type_dir in self.storage_dir.iterdir():
                if type_dir.is_dir():
                    artifacts.extend([f.stem for f in type_dir.glob("*.json")])
        
        return artifacts

