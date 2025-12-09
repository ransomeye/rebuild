# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/regression/golden_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages ephemeral reference data (Golden Master) for regression testing

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoldenManager:
    """
    Manages Golden Master reference data for regression testing.
    Stores expected outputs for deterministic queries.
    """
    
    def __init__(self, golden_dir: Optional[str] = None):
        """
        Initialize Golden Manager.
        
        Args:
            golden_dir: Directory to store golden master files
        """
        self.golden_dir = golden_dir or os.environ.get(
            'GOLDEN_MASTER_DIR',
            str(Path(__file__).parent.parent / 'data' / 'golden_master')
        )
        os.makedirs(self.golden_dir, exist_ok=True)
    
    def _get_query_hash(self, query: str) -> str:
        """Generate hash for query."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]
    
    def save_golden(
        self,
        query: str,
        expected_output: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save golden master reference.
        
        Args:
            query: Query string
            expected_output: Expected output dictionary
            metadata: Optional metadata
            
        Returns:
            Path to saved golden master file
        """
        query_hash = self._get_query_hash(query)
        golden_file = Path(self.golden_dir) / f"{query_hash}.json"
        
        golden_data = {
            'query': query,
            'query_hash': query_hash,
            'expected_output': expected_output,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        with open(golden_file, 'w') as f:
            json.dump(golden_data, f, indent=2)
        
        logger.info(f"Saved golden master for query hash: {query_hash}")
        return str(golden_file)
    
    def load_golden(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Load golden master reference.
        
        Args:
            query: Query string
            
        Returns:
            Golden master data or None if not found
        """
        query_hash = self._get_query_hash(query)
        golden_file = Path(self.golden_dir) / f"{query_hash}.json"
        
        if not golden_file.exists():
            return None
        
        try:
            with open(golden_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading golden master: {e}")
            return None
    
    def compare_output(
        self,
        query: str,
        actual_output: Dict[str, Any],
        tolerance: float = 0.0
    ) -> Dict[str, Any]:
        """
        Compare actual output against golden master.
        
        Args:
            query: Query string
            actual_output: Actual output to compare
            tolerance: Tolerance for numeric comparisons
            
        Returns:
            Comparison result
        """
        golden = self.load_golden(query)
        
        if not golden:
            return {
                'match': False,
                'error': 'No golden master found',
                'query_hash': self._get_query_hash(query)
            }
        
        expected = golden['expected_output']
        
        # Compare outputs
        match, differences = self._compare_dicts(expected, actual_output, tolerance)
        
        return {
            'match': match,
            'query_hash': golden['query_hash'],
            'differences': differences,
            'expected': expected,
            'actual': actual_output
        }
    
    def _compare_dicts(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
        tolerance: float
    ) -> tuple[bool, List[str]]:
        """Compare two dictionaries recursively."""
        differences = []
        match = True
        
        # Check all keys in expected
        for key in expected:
            if key not in actual:
                differences.append(f"Missing key: {key}")
                match = False
                continue
            
            exp_val = expected[key]
            act_val = actual[key]
            
            if isinstance(exp_val, dict) and isinstance(act_val, dict):
                sub_match, sub_diffs = self._compare_dicts(exp_val, act_val, tolerance)
                if not sub_match:
                    match = False
                    differences.extend([f"{key}.{d}" for d in sub_diffs])
            elif isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)):
                if abs(exp_val - act_val) > tolerance:
                    differences.append(f"{key}: expected {exp_val}, got {act_val}")
                    match = False
            elif isinstance(exp_val, str) and isinstance(act_val, str):
                # For strings, compare hashes for deterministic comparison
                if hashlib.sha256(exp_val.encode()).hexdigest() != hashlib.sha256(act_val.encode()).hexdigest():
                    differences.append(f"{key}: string mismatch (length: {len(exp_val)} vs {len(act_val)})")
                    match = False
            else:
                if exp_val != act_val:
                    differences.append(f"{key}: expected {exp_val}, got {act_val}")
                    match = False
        
        # Check for extra keys in actual
        for key in actual:
            if key not in expected:
                differences.append(f"Extra key: {key}")
                match = False
        
        return match, differences
    
    def list_golden_masters(self) -> List[Dict[str, Any]]:
        """List all golden masters."""
        golden_files = list(Path(self.golden_dir).glob('*.json'))
        masters = []
        
        for golden_file in golden_files:
            try:
                with open(golden_file, 'r') as f:
                    data = json.load(f)
                    masters.append({
                        'query_hash': data.get('query_hash', ''),
                        'query': data.get('query', '')[:50],
                        'created_at': data.get('created_at', '')
                    })
            except Exception as e:
                logger.error(f"Error reading {golden_file}: {e}")
        
        return masters

