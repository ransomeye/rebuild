# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/ml/incremental_trainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Updates model weights based on hit rates for Autolearn functionality

import os
import sys
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .placement_model import PlacementModel
from ..storage.config_store import ConfigStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncrementalTrainer:
    """
    Incremental trainer for placement model.
    Updates weights based on recent hit rates (Autolearn).
    """
    
    def __init__(self):
        """Initialize incremental trainer."""
        self.config_store = ConfigStore()
        self.model_path = os.environ.get(
            'DECEPTION_MODEL_PATH',
            str(Path(__file__).parent / 'placement_model.pkl')
        )
        
        # Training window (days)
        self.training_window_days = int(os.environ.get('AUTOLEARN_WINDOW_DAYS', '7'))
        
        logger.info("Incremental trainer initialized")
    
    async def autolearn_update(self) -> Dict[str, Any]:
        """
        Perform incremental learning update based on recent hits.
        
        Returns:
            Update results
        """
        try:
            # Get recent decoy performance data
            recent_data = await self._get_recent_performance()
            
            if len(recent_data) < 5:
                logger.info("Insufficient recent data for autolearn update")
                return {
                    'status': 'skipped',
                    'reason': 'Insufficient data',
                    'samples': len(recent_data)
                }
            
            # Extract features and hit rates
            X_new = np.array([d['features'] for d in recent_data])
            y_new = np.array([d['hit_rate'] for d in recent_data])
            
            # Load current model
            model = PlacementModel(model_path=self.model_path)
            
            if model.model is None:
                return {
                    'status': 'skipped',
                    'reason': 'Model not available'
                }
            
            # Update model (in production, use warm_start for retraining)
            # For now, we'll retrain on combined data
            model.update_model(X_new, y_new)
            
            logger.info(f"Autolearn update completed with {len(recent_data)} samples")
            
            return {
                'status': 'success',
                'samples': len(recent_data),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in autolearn update: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _get_recent_performance(self) -> List[Dict[str, Any]]:
        """
        Get recent decoy performance data.
        
        Returns:
            List of performance samples
        """
        # In production, query database for:
        # - Decoys deployed in last N days
        # - Hit counts per decoy
        # - Feature vectors
        
        # For now, return empty
        return []

