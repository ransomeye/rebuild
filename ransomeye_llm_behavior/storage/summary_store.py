# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/storage/summary_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Persistence for behavioral summaries

import os
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SummaryStore:
    """
    Stores behavioral summaries with metadata.
    """
    
    def __init__(self, storage_dir: str = None):
        """Initialize summary store."""
        if storage_dir is None:
            storage_dir = os.environ.get(
                'SUMMARY_STORAGE_DIR',
                '/home/ransomeye/rebuild/ransomeye_llm_behavior/storage/summaries'
            )
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save_summary(
        self,
        summary_id: str,
        query: str,
        summary: str,
        confidence: float,
        metadata: Dict = None
    ):
        """Save summary to storage."""
        summary_data = {
            'summary_id': summary_id,
            'query': query,
            'summary': summary,
            'confidence': confidence,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        summary_file = self.storage_dir / f"{summary_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        logger.info(f"Saved summary: {summary_id}")
    
    def load_summary(self, summary_id: str) -> Optional[Dict]:
        """Load summary from storage."""
        summary_file = self.storage_dir / f"{summary_id}.json"
        
        if not summary_file.exists():
            return None
        
        try:
            with open(summary_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading summary: {e}")
            return None

