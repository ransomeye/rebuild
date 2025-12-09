# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/storage/manifest_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Creates canonical JSON manifests for uploaded chunks

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ManifestBuilder:
    """Builds canonical JSON manifests for chunks."""
    
    def __init__(self, probe_id: str = None):
        """
        Initialize manifest builder.
        
        Args:
            probe_id: Probe identifier
        """
        self.probe_id = probe_id or os.environ.get('PROBE_ID', 'unknown')
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def build_manifest(self, chunk_path: Path, flow_data: List[Dict[str, Any]] = None,
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Build manifest for a chunk.
        
        Args:
            chunk_path: Path to chunk file
            flow_data: List of flow statistics dictionaries
            metadata: Additional metadata
            
        Returns:
            Manifest dictionary
        """
        chunk_hash = self._calculate_file_hash(chunk_path)
        chunk_size = chunk_path.stat().st_size
        chunk_mtime = datetime.fromtimestamp(chunk_path.stat().st_mtime)
        
        manifest = {
            'probe_id': self.probe_id,
            'chunk_filename': chunk_path.name,
            'chunk_hash': chunk_hash,
            'chunk_size': chunk_size,
            'created_at': chunk_mtime.isoformat(),
            'manifest_version': '1.0',
            'flow_count': len(flow_data) if flow_data else 0,
            'flows': flow_data or [],
            'metadata': metadata or {}
        }
        
        return manifest
    
    def save_manifest(self, manifest: Dict[str, Any], output_dir: Path):
        """
        Save manifest to JSON file.
        
        Args:
            manifest: Manifest dictionary
            output_dir: Output directory
            
        Returns:
            Path to saved manifest file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_filename = manifest['chunk_filename']
        manifest_filename = f"{Path(chunk_filename).stem}.manifest.json"
        manifest_path = output_dir / manifest_filename
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.debug(f"Saved manifest: {manifest_path}")
        return manifest_path
    
    def load_manifest(self, manifest_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load manifest from file.
        
        Args:
            manifest_path: Path to manifest file
            
        Returns:
            Manifest dictionary or None
        """
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading manifest {manifest_path}: {e}")
            return None
    
    def verify_manifest(self, manifest: Dict[str, Any], chunk_path: Path) -> bool:
        """
        Verify manifest matches chunk file.
        
        Args:
            manifest: Manifest dictionary
            chunk_path: Path to chunk file
            
        Returns:
            True if manifest is valid, False otherwise
        """
        if not chunk_path.exists():
            return False
        
        # Verify hash
        expected_hash = manifest.get('chunk_hash')
        actual_hash = self._calculate_file_hash(chunk_path)
        
        if expected_hash != actual_hash:
            logger.error(f"Manifest hash mismatch: expected {expected_hash}, got {actual_hash}")
            return False
        
        # Verify size
        expected_size = manifest.get('chunk_size')
        actual_size = chunk_path.stat().st_size
        
        if expected_size != actual_size:
            logger.error(f"Manifest size mismatch: expected {expected_size}, got {actual_size}")
            return False
        
        return True

