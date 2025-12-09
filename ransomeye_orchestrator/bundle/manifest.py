# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/bundle/manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates canonical JSON manifest with sorted keys

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """Generates canonical JSON manifest with sorted keys."""
    
    @staticmethod
    def generate_manifest(
        incident_id: str,
        files: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate canonical manifest.
        
        Args:
            incident_id: Incident identifier
            files: List of file information dictionaries
            chunks: Optional list of chunk information
            metadata: Optional metadata dictionary
        
        Returns:
            Canonical manifest dictionary
        """
        manifest = {
            "version": "1.0.0",
            "incident_id": incident_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "files": sorted(files, key=lambda x: x.get('path', '')),
            "metadata": metadata or {}
        }
        
        if chunks:
            manifest["chunks"] = sorted(chunks, key=lambda x: x.get('index', 0))
        
        # Calculate manifest hash
        manifest_json = json.dumps(manifest, sort_keys=True, separators=(',', ':'))
        manifest_hash = hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()
        manifest["manifest_hash"] = manifest_hash
        
        return manifest
    
    @staticmethod
    def save_manifest(manifest: Dict[str, Any], output_path: Path):
        """
        Save manifest to file in canonical format.
        
        Args:
            manifest: Manifest dictionary
            output_path: Path to save manifest
        """
        # Ensure sorted keys for canonical format
        manifest_json = json.dumps(manifest, sort_keys=True, indent=2)
        
        with open(output_path, 'w') as f:
            f.write(manifest_json)
        
        logger.info(f"Manifest saved to {output_path}")
    
    @staticmethod
    def load_manifest(manifest_path: Path) -> Dict[str, Any]:
        """
        Load manifest from file.
        
        Args:
            manifest_path: Path to manifest file
        
        Returns:
            Manifest dictionary
        """
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        return manifest
    
    @staticmethod
    def verify_manifest_integrity(manifest: Dict[str, Any]) -> bool:
        """
        Verify manifest integrity by recalculating hash.
        
        Args:
            manifest: Manifest dictionary
        
        Returns:
            True if integrity is valid
        """
        # Get stored hash
        stored_hash = manifest.get('manifest_hash')
        if not stored_hash:
            logger.warning("Manifest missing hash")
            return False
        
        # Remove hash for recalculation
        manifest_copy = manifest.copy()
        manifest_copy.pop('manifest_hash', None)
        
        # Recalculate
        manifest_json = json.dumps(manifest_copy, sort_keys=True, separators=(',', ':'))
        calculated_hash = hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()
        
        if calculated_hash != stored_hash:
            logger.error(f"Manifest integrity check failed: {calculated_hash} != {stored_hash}")
            return False
        
        return True

