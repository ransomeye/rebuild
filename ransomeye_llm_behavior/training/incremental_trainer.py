# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/training/incremental_trainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Autolearn loop for incremental model updates from feedback

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncrementalTrainer:
    """
    Incremental trainer for autolearn functionality.
    Updates models based on operator feedback.
    """
    
    def __init__(self, feedback_dir: str = None):
        """Initialize incremental trainer."""
        if feedback_dir is None:
            feedback_dir = os.environ.get(
                'FEEDBACK_DIR',
                '/home/ransomeye/rebuild/ransomeye_llm_behavior/feedback'
            )
        
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
    
    def record_feedback(
        self,
        feedback_id: str,
        query: str,
        output: str,
        operator_rating: float,
        operator_notes: Optional[str] = None
    ) -> str:
        """
        Record operator feedback.
        
        Args:
            feedback_id: Unique feedback ID
            query: Original query
            output: LLM output
            operator_rating: Rating (0-1, where 1 is perfect)
            operator_notes: Optional notes
            
        Returns:
            Feedback entry ID
        """
        feedback_entry = {
            'feedback_id': feedback_id,
            'query': query,
            'output': output,
            'operator_rating': operator_rating,
            'operator_notes': operator_notes,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        feedback_file = self.feedback_dir / f"{feedback_id}.json"
        with open(feedback_file, 'w') as f:
            json.dump(feedback_entry, f, indent=2)
        
        logger.info(f"Recorded feedback: {feedback_id}")
        return feedback_id
    
    def load_feedback(self, limit: Optional[int] = None) -> List[Dict]:
        """Load feedback entries."""
        feedback_files = sorted(self.feedback_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if limit:
            feedback_files = feedback_files[:limit]
        
        feedback_entries = []
        for feedback_file in feedback_files:
            try:
                with open(feedback_file, 'r') as f:
                    feedback_entries.append(json.load(f))
            except Exception as e:
                logger.error(f"Error loading feedback: {e}")
        
        return feedback_entries

