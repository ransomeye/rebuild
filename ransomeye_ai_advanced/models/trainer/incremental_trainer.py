# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/models/trainer/incremental_trainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Autolearn loop for incremental model training from feedback

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .train_validator import ValidatorTrainer
from .train_reranker import RerankerTrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncrementalTrainer:
    """
    Incremental trainer that continuously learns from feedback.
    Implements autolearn loop for model improvement.
    """
    
    def __init__(
        self,
        feedback_dir: Optional[str] = None,
        validator_model_path: Optional[str] = None,
        reranker_model_path: Optional[str] = None,
        retrain_interval_hours: int = 24
    ):
        """
        Initialize incremental trainer.
        
        Args:
            feedback_dir: Directory containing feedback JSONL files
            validator_model_path: Path to validator model
            reranker_model_path: Path to reranker model
            retrain_interval_hours: Hours between retraining
        """
        self.feedback_dir = feedback_dir or os.environ.get(
            'FEEDBACK_DIR',
            str(Path(__file__).parent.parent.parent / 'data' / 'feedback')
        )
        self.validator_model_path = validator_model_path
        self.reranker_model_path = reranker_model_path
        self.retrain_interval_hours = retrain_interval_hours
        
        self.validator_trainer = ValidatorTrainer(model_output_path=validator_model_path)
        self.reranker_trainer = RerankerTrainer(model_output_path=reranker_model_path)
        
        self.last_retrain_time = None
        self.is_running = False
    
    def load_feedback(self) -> List[Dict]:
        """
        Load feedback from JSONL files.
        
        Expected format (one JSON per line):
        {"query": "...", "answer": "...", "context": "...", "feedback": 1, "timestamp": "..."}
        
        Returns:
            List of feedback records
        """
        feedback_records = []
        
        if not os.path.exists(self.feedback_dir):
            logger.warning(f"Feedback directory not found: {self.feedback_dir}")
            return feedback_records
        
        # Find all JSONL files
        jsonl_files = list(Path(self.feedback_dir).glob('*.jsonl'))
        
        for jsonl_file in jsonl_files:
            try:
                with open(jsonl_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            feedback_records.append(record)
            except Exception as e:
                logger.error(f"Error reading {jsonl_file}: {e}")
        
        logger.info(f"Loaded {len(feedback_records)} feedback records")
        return feedback_records
    
    def convert_feedback_to_training_data(
        self,
        feedback_records: List[Dict],
        model_type: str = 'validator'
    ) -> List[Dict]:
        """
        Convert feedback records to training data format.
        
        Args:
            feedback_records: List of feedback records
            model_type: 'validator' or 'reranker'
            
        Returns:
            Training data in appropriate format
        """
        if model_type == 'validator':
            training_data = []
            for record in feedback_records:
                # feedback: 1 = good, 0 = bad/hallucination
                label = 1 if record.get('feedback', 0) > 0 else 0
                training_data.append({
                    'answer': record.get('answer', ''),
                    'context': record.get('context', ''),
                    'label': label
                })
            return training_data
        
        elif model_type == 'reranker':
            # Group by query
            query_groups = {}
            for record in feedback_records:
                query = record.get('query', '')
                if query not in query_groups:
                    query_groups[query] = []
                
                relevance_score = record.get('feedback', 0.5)  # Use feedback as relevance
                query_groups[query].append({
                    'text': record.get('context', ''),
                    'relevance_score': relevance_score
                })
            
            # Convert to reranker format
            training_data = []
            for query, chunks in query_groups.items():
                training_data.append({
                    'query': query,
                    'chunks': chunks
                })
            return training_data
        
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    async def retrain_models(self) -> Dict[str, Any]:
        """
        Retrain models from accumulated feedback.
        
        Returns:
            Training results
        """
        logger.info("Starting incremental retraining...")
        
        # Load feedback
        feedback_records = self.load_feedback()
        if len(feedback_records) < 10:
            logger.info("Insufficient feedback for retraining (need at least 10 records)")
            return {'status': 'insufficient_data', 'records': len(feedback_records)}
        
        results = {}
        
        # Retrain validator
        try:
            logger.info("Retraining validator model...")
            validator_data = self.convert_feedback_to_training_data(feedback_records, 'validator')
            
            # Save to temporary file for trainer
            temp_data_path = str(Path(self.feedback_dir).parent / 'temp_validator_data.json')
            with open(temp_data_path, 'w') as f:
                json.dump(validator_data, f)
            
            self.validator_trainer.training_data_path = temp_data_path
            validator_results = self.validator_trainer.train()
            results['validator'] = validator_results
            logger.info(f"Validator retrained: accuracy={validator_results['accuracy']:.2%}")
        except Exception as e:
            logger.error(f"Error retraining validator: {e}")
            results['validator'] = {'error': str(e)}
        
        # Retrain reranker
        try:
            logger.info("Retraining reranker model...")
            reranker_data = self.convert_feedback_to_training_data(feedback_records, 'reranker')
            
            temp_data_path = str(Path(self.feedback_dir).parent / 'temp_reranker_data.json')
            with open(temp_data_path, 'w') as f:
                json.dump(reranker_data, f)
            
            self.reranker_trainer.training_data_path = temp_data_path
            reranker_results = self.reranker_trainer.train()
            results['reranker'] = reranker_results
            logger.info(f"Reranker retrained: accuracy={reranker_results['accuracy']:.2%}")
        except Exception as e:
            logger.error(f"Error retraining reranker: {e}")
            results['reranker'] = {'error': str(e)}
        
        self.last_retrain_time = datetime.utcnow()
        results['status'] = 'success'
        results['timestamp'] = self.last_retrain_time.isoformat()
        
        return results
    
    async def autolearn_loop(self):
        """
        Main autolearn loop that periodically retrains models.
        """
        self.is_running = True
        logger.info("Starting autolearn loop...")
        
        while self.is_running:
            try:
                # Check if it's time to retrain
                should_retrain = False
                if self.last_retrain_time is None:
                    should_retrain = True
                else:
                    hours_since_retrain = (
                        datetime.utcnow() - self.last_retrain_time
                    ).total_seconds() / 3600
                    if hours_since_retrain >= self.retrain_interval_hours:
                        should_retrain = True
                
                if should_retrain:
                    await self.retrain_models()
                
                # Wait before next check (check every hour)
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in autolearn loop: {e}")
                await asyncio.sleep(3600)
    
    def stop(self):
        """Stop the autolearn loop."""
        self.is_running = False
        logger.info("Autolearn loop stopped")


def main():
    """Main script for incremental training."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Incremental model trainer')
    parser.add_argument('--feedback-dir', type=str, help='Feedback directory')
    parser.add_argument('--validator-model', type=str, help='Validator model path')
    parser.add_argument('--reranker-model', type=str, help='Reranker model path')
    parser.add_argument('--interval', type=int, default=24, help='Retrain interval (hours)')
    parser.add_argument('--once', action='store_true', help='Run once instead of loop')
    
    args = parser.parse_args()
    
    trainer = IncrementalTrainer(
        feedback_dir=args.feedback_dir,
        validator_model_path=args.validator_model,
        reranker_model_path=args.reranker_model,
        retrain_interval_hours=args.interval
    )
    
    if args.once:
        # Run once
        results = asyncio.run(trainer.retrain_models())
        print(json.dumps(results, indent=2))
    else:
        # Run loop
        try:
            asyncio.run(trainer.autolearn_loop())
        except KeyboardInterrupt:
            trainer.stop()


if __name__ == '__main__':
    main()

