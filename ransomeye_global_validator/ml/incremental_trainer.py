# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/ml/incremental_trainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Autolearn loop that retrains model periodically using new validation run data

import os
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from .train_validator import ValidatorTrainer
from .validator_model import ValidatorModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncrementalTrainer:
    """Autolearn loop for incremental model training."""
    
    def __init__(self):
        """Initialize incremental trainer."""
        self.trainer = ValidatorTrainer()
        self.validator_model = ValidatorModel()
        self.run_store_path = os.environ.get(
            'VALIDATOR_RUN_STORE_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/storage/runs'
        )
        self.retrain_interval_hours = int(os.environ.get('VALIDATOR_RETRAIN_INTERVAL_HOURS', '24'))
        self.min_samples_for_retrain = int(os.environ.get('VALIDATOR_MIN_SAMPLES', '10'))
        logger.info(f"Incremental trainer initialized (retrain interval: {self.retrain_interval_hours}h)")
    
    async def run_autolearn_loop(self):
        """Run continuous autolearn loop."""
        logger.info("Starting autolearn loop...")
        
        while True:
            try:
                # Check if we have enough new data
                new_runs = self._collect_new_runs()
                
                if len(new_runs) >= self.min_samples_for_retrain:
                    logger.info(f"Retraining model with {len(new_runs)} new runs")
                    self._retrain_with_new_data(new_runs)
                else:
                    logger.info(f"Not enough new data for retraining ({len(new_runs)} < {self.min_samples_for_retrain})")
                
                # Wait for next retrain interval
                await asyncio.sleep(self.retrain_interval_hours * 3600)
            
            except Exception as e:
                logger.error(f"Error in autolearn loop: {e}", exc_info=True)
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    def _collect_new_runs(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Collect new validation runs from storage.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of run data
        """
        runs = []
        run_store_path = Path(self.run_store_path)
        
        if not run_store_path.exists():
            return runs
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        for run_file in run_store_path.glob("*.json"):
            try:
                with open(run_file, 'r') as f:
                    run_data = json.load(f)
                
                start_time_str = run_data.get('start_time')
                if start_time_str:
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    if start_time >= cutoff_time:
                        runs.append(run_data)
            
            except Exception as e:
                logger.warning(f"Error reading run file {run_file}: {e}")
        
        return runs
    
    def _retrain_with_new_data(self, new_runs: List[Dict[str, Any]]):
        """
        Retrain model with new run data.
        
        Args:
            new_runs: List of new validation run data
        """
        # Append new data to training file
        training_data_path = Path(self.trainer.training_data_path)
        training_data_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(training_data_path, 'a') as f:
            for run in new_runs:
                metrics = run.get('metrics', {})
                ml_result = run.get('ml_result', {})
                is_healthy = ml_result.get('is_healthy', True)
                
                # Determine ground truth from actual run results
                summary = run.get('summary', {})
                actual_healthy = summary.get('failed_scenarios', 0) == 0
                
                training_sample = {
                    'metrics': metrics,
                    'is_healthy': actual_healthy,
                    'run_id': run.get('run_id'),
                    'timestamp': run.get('start_time')
                }
                
                f.write(json.dumps(training_sample) + '\n')
        
        # Retrain model
        results = self.trainer.train()
        logger.info(f"Model retrained: accuracy={results['accuracy']:.4f}")

