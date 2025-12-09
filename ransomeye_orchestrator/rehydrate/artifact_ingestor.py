# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/rehydrate/artifact_ingestor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Restores binary artifact files to Forensic Storage path

import os
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ArtifactIngestor:
    """Restores binary artifact files to Forensic Storage path."""
    
    def __init__(self):
        """Initialize artifact ingestor."""
        self.storage_base = Path(os.environ.get('FORENSIC_STORAGE_PATH', '/home/ransomeye/rebuild/data/forensic'))
        self.storage_base.mkdir(parents=True, exist_ok=True)
    
    def restore_artifacts(
        self,
        artifacts_dir: Path,
        manifest: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ):
        """
        Restore artifacts from bundle to storage.
        
        Args:
            artifacts_dir: Directory containing artifact files
            manifest: Manifest dictionary
            idempotency_key: Optional idempotency key
        """
        logger.info(f"Restoring artifacts from {artifacts_dir}")
        
        artifacts_restored = 0
        
        # Find all artifact files in manifest
        for file_info in manifest.get('files', []):
            file_path = file_info.get('path', '')
            
            if not file_path.startswith('artifacts/'):
                continue
            
            source_path = artifacts_dir / file_path
            if not source_path.exists():
                logger.warning(f"Artifact file not found: {source_path}")
                continue
            
            # Extract artifact ID from path
            # Path format: artifacts/{artifact_id}/{filename}
            parts = file_path.split('/')
            if len(parts) >= 3:
                artifact_id = parts[1]
                
                # Restore to storage
                dest_dir = self.storage_base / artifact_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / parts[-1]
                
                # Copy file
                shutil.copy2(source_path, dest_path)
                
                # Verify hash if provided
                expected_hash = file_info.get('sha256')
                if expected_hash:
                    import hashlib
                    with open(dest_path, 'rb') as f:
                        calculated_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    if calculated_hash != expected_hash:
                        logger.error(
                            f"Artifact hash mismatch: {file_path} "
                            f"(expected {expected_hash[:16]}..., got {calculated_hash[:16]}...)"
                        )
                        dest_path.unlink()  # Remove corrupted file
                        continue
                
                artifacts_restored += 1
                logger.debug(f"Artifact restored: {dest_path}")
        
        logger.info(f"Restored {artifacts_restored} artifacts")

