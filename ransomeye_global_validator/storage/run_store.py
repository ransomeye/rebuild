# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/storage/run_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Persists run artifacts (PDFs, logs, manifests) to disk

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RunStore:
    """Stores validation run artifacts."""
    
    def __init__(self):
        """Initialize run store."""
        self.storage_dir = Path(os.environ.get(
            'VALIDATOR_RUN_STORE_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/storage/runs'
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Run store initialized at {self.storage_dir}")
    
    def store_run(self, run_id: str, run_data: Dict[str, Any]):
        """
        Store validation run data.
        
        Args:
            run_id: Run identifier
            run_data: Run data dictionary
        """
        run_file = self.storage_dir / f"{run_id}_run.json"
        
        with open(run_file, 'w') as f:
            json.dump(run_data, f, indent=2)
        
        logger.info(f"Run data stored: {run_file}")
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve run data.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Run data or None if not found
        """
        run_file = self.storage_dir / f"{run_id}_run.json"
        
        if not run_file.exists():
            return None
        
        try:
            with open(run_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading run file: {e}")
            return None
    
    def get_pdf_path(self, run_id: str) -> str:
        """
        Get PDF path for a run.
        
        Args:
            run_id: Run identifier
            
        Returns:
            PDF file path
        """
        return str(self.storage_dir / f"{run_id}_report.pdf")
    
    def get_manifest_path(self, run_id: str) -> str:
        """
        Get manifest path for a run.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Manifest file path
        """
        return str(self.storage_dir / f"{run_id}_manifest.json")
    
    def list_runs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all stored runs.
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of run metadata
        """
        runs = []
        
        for run_file in sorted(self.storage_dir.glob("*_run.json"), reverse=True)[:limit]:
            try:
                with open(run_file, 'r') as f:
                    run_data = json.load(f)
                    runs.append({
                        "run_id": run_data.get("run_id"),
                        "start_time": run_data.get("start_time"),
                        "scenario_type": run_data.get("scenario_type"),
                        "status": "PASSED" if run_data.get("summary", {}).get("failed_scenarios", 0) == 0 else "FAILED"
                    })
            except Exception as e:
                logger.warning(f"Error reading run file {run_file}: {e}")
        
        return runs

