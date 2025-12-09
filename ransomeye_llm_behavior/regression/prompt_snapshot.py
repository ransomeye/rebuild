# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/regression/prompt_snapshot.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Tracks versions of prompts used during regression runs

import hashlib
from typing import Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptSnapshot:
    """
    Tracks prompt versions for regression testing.
    """
    
    def __init__(self):
        """Initialize prompt snapshot tracker."""
        self.snapshots: Dict[str, Dict] = {}
    
    def snapshot_prompt(self, prompt: str, version: str = None) -> str:
        """
        Create snapshot of prompt.
        
        Args:
            prompt: Prompt text
            version: Optional version string (auto-generated if None)
            
        Returns:
            Snapshot ID
        """
        prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        
        if version is None:
            version = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        snapshot_id = f"{version}_{prompt_hash[:8]}"
        
        self.snapshots[snapshot_id] = {
            'prompt': prompt,
            'hash': prompt_hash,
            'version': version,
            'created_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Created prompt snapshot: {snapshot_id}")
        return snapshot_id
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Get snapshot by ID."""
        return self.snapshots.get(snapshot_id)
    
    def verify_prompt(self, prompt: str, snapshot_id: str) -> bool:
        """
        Verify prompt matches snapshot.
        
        Args:
            prompt: Prompt to verify
            snapshot_id: Snapshot ID
            
        Returns:
            True if matches
        """
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            return False
        
        prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        return prompt_hash == snapshot['hash']

