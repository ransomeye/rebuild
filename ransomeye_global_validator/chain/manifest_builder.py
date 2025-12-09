# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/chain/manifest_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Creates run manifest JSON with start time, scenarios, and results

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManifestBuilder:
    """Builds validation run manifests for chain of custody."""
    
    def __init__(self):
        """Initialize manifest builder."""
        logger.info("Manifest builder initialized")
    
    def build_manifest(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build run manifest from validation run data.
        
        Args:
            run_data: Complete validation run data
            
        Returns:
            Manifest dictionary
        """
        manifest = {
            "manifest_version": "1.0",
            "run_id": run_data.get("run_id"),
            "start_time": run_data.get("start_time"),
            "end_time": run_data.get("end_time"),
            "scenario_type": run_data.get("scenario_type"),
            "scenario_id": run_data.get("scenario_id"),
            "scenario_name": run_data.get("scenario_name"),
            "summary": run_data.get("summary", {}),
            "scenarios": run_data.get("scenarios", []),
            "metrics": run_data.get("metrics", {}),
            "ml_result": run_data.get("ml_result", {}),
            "created_at": datetime.utcnow().isoformat(),
            "artifacts": {
                "pdf_path": run_data.get("pdf_path"),
                "manifest_path": run_data.get("manifest_path")
            }
        }
        
        # Calculate manifest hash
        manifest_json = json.dumps(manifest, sort_keys=True)
        manifest_hash = hashlib.sha256(manifest_json.encode()).hexdigest()
        manifest["manifest_hash_sha256"] = manifest_hash
        
        logger.info(f"Manifest built for run {run_data.get('run_id')}")
        return manifest
    
    def save_manifest(self, manifest: Dict[str, Any], output_path: str):
        """
        Save manifest to file.
        
        Args:
            manifest: Manifest dictionary
            output_path: Output file path
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Manifest saved to {output_path}")

