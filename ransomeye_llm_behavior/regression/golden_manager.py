# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/regression/golden_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages storage and retrieval of golden master artifacts

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoldenManager:
    """
    Manages golden master artifacts for regression testing.
    Stores inputs + expected outputs with hashes.
    """
    
    def __init__(self, golden_dir: str = None):
        """
        Initialize golden manager.
        
        Args:
            golden_dir: Directory for storing golden artifacts
        """
        if golden_dir is None:
            golden_dir = os.environ.get(
                'GOLDEN_DIR',
                '/home/ransomeye/rebuild/ransomeye_llm_behavior/regression/goldens'
            )
        
        self.golden_dir = Path(golden_dir)
        self.golden_dir.mkdir(parents=True, exist_ok=True)
    
    def save_golden(
        self,
        test_id: str,
        input_data: Dict,
        expected_output: str,
        metadata: Dict = None
    ) -> str:
        """
        Save golden artifact.
        
        Args:
            test_id: Unique test identifier
            input_data: Input data dictionary
            expected_output: Expected output text
            metadata: Optional metadata
            
        Returns:
            Path to saved golden file
        """
        # Compute hash of expected output
        output_hash = hashlib.sha256(expected_output.encode('utf-8')).hexdigest()
        
        golden_data = {
            'test_id': test_id,
            'input': input_data,
            'expected_output': expected_output,
            'output_hash': output_hash,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Save to file
        golden_file = self.golden_dir / f"{test_id}.json"
        with open(golden_file, 'w') as f:
            json.dump(golden_data, f, indent=2)
        
        logger.info(f"Saved golden artifact: {test_id} (hash: {output_hash[:16]})")
        return str(golden_file)
    
    def load_golden(self, test_id: str) -> Optional[Dict]:
        """
        Load golden artifact.
        
        Args:
            test_id: Test identifier
            
        Returns:
            Golden data dictionary or None
        """
        golden_file = self.golden_dir / f"{test_id}.json"
        
        if not golden_file.exists():
            return None
        
        try:
            with open(golden_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading golden: {e}")
            return None
    
    def verify_output(self, test_id: str, actual_output: str) -> Dict:
        """
        Verify actual output against golden.
        
        Args:
            test_id: Test identifier
            actual_output: Actual output to verify
            
        Returns:
            Verification results
        """
        golden = self.load_golden(test_id)
        if not golden:
            return {
                'valid': False,
                'error': 'Golden not found',
                'test_id': test_id
            }
        
        expected_hash = golden['output_hash']
        actual_hash = hashlib.sha256(actual_output.encode('utf-8')).hexdigest()
        
        is_match = expected_hash == actual_hash
        
        return {
            'valid': is_match,
            'test_id': test_id,
            'expected_hash': expected_hash,
            'actual_hash': actual_hash,
            'match': is_match,
            'drift_detected': not is_match
        }
    
    def list_goldens(self) -> List[str]:
        """List all golden test IDs."""
        return [f.stem for f in self.golden_dir.glob('*.json')]

