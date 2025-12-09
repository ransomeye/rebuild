# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/trust/incremental_trainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Autolearn loop (Analyst Feedback -> Model Update)

import os
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .train_trust_model import TrustModelTrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrustIncrementalTrainer:
    """
    Incremental trainer for trust model from analyst feedback.
    """
    
    def __init__(
        self,
        feedback_dir: Optional[str] = None,
        model_path: Optional[str] = None,
        retrain_interval_hours: int = 24
    ):
        """
        Initialize incremental trainer.
        
        Args:
            feedback_dir: Directory with feedback JSONL files
            model_path: Path to trust model
            retrain_interval_hours: Hours between retraining
        """
        self.feedback_dir = feedback_dir or os.environ.get('TI_FEEDBACK_DIR')
        self.model_path = model_path
        self.retrain_interval_hours = retrain_interval_hours
        self.last_retrain_time = None
        self.is_running = False
    
    def load_feedback(self) -> List[Dict[str, Any]]:
        """Load feedback from JSONL files."""
        feedback_records = []
        
        if not self.feedback_dir or not os.path.exists(self.feedback_dir):
            return feedback_records
        
        for jsonl_file in Path(self.feedback_dir).glob('*.jsonl'):
            try:
                with open(jsonl_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            feedback_records.append(json.loads(line))
            except Exception as e:
                logger.error(f"Error reading {jsonl_file}: {e}")
        
        return feedback_records
    
    async def retrain(self) -> Dict[str, Any]:
        """Retrain model from feedback."""
        feedback = self.load_feedback()
        
        if len(feedback) < 10:
            return {'status': 'insufficient_data', 'records': len(feedback)}
        
        # Convert feedback to training data
        training_data = []
        for record in feedback:
            training_data.append({
                'source_reputation': record.get('source_reputation', 0.5),
                'age_days': record.get('age_days', 0),
                'sightings_count': record.get('sightings_count', 0),
                'trust_label': 1 if record.get('feedback', 0) > 0 else 0
            })
        
        # Save to temp file
        temp_data_path = str(Path(self.feedback_dir).parent / 'temp_trust_data.json')
        with open(temp_data_path, 'w') as f:
            json.dump(training_data, f)
        
        # Train
        trainer = TrustModelTrainer(model_output_path=self.model_path)
        trainer.training_data_path = temp_data_path
        metrics = trainer.train()
        
        self.last_retrain_time = datetime.utcnow()
        return {'status': 'success', 'metrics': metrics}
    
    async def autolearn_loop(self):
        """Main autolearn loop."""
        self.is_running = True
        
        while self.is_running:
            try:
                should_retrain = (
                    self.last_retrain_time is None or
                    (datetime.utcnow() - self.last_retrain_time).total_seconds() / 3600 >= self.retrain_interval_hours
                )
                
                if should_retrain:
                    await self.retrain()
                
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                logger.error(f"Error in autolearn loop: {e}")
                await asyncio.sleep(3600)
    
    def stop(self):
        """Stop autolearn loop."""
        self.is_running = False


def main():
    """Main script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Incremental trust model trainer')
    parser.add_argument('--feedback-dir', type=str, help='Feedback directory')
    parser.add_argument('--model-path', type=str, help='Model path')
    parser.add_argument('--once', action='store_true', help='Run once')
    
    args = parser.parse_args()
    
    trainer = TrustIncrementalTrainer(
        feedback_dir=args.feedback_dir,
        model_path=args.model_path
    )
    
    if args.once:
        result = asyncio.run(trainer.retrain())
        print(json.dumps(result, indent=2))
    else:
        try:
            asyncio.run(trainer.autolearn_loop())
        except KeyboardInterrupt:
            trainer.stop()

if __name__ == '__main__':
    main()

