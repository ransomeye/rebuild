# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/dna/dna_serializer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Serialize DNA features into deterministic canonical JSON format

import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DNASerializer:
    """
    Serialize DNA features into deterministic, canonical JSON format.
    Ensures consistent serialization for comparison and hashing.
    """
    
    def __init__(self):
        """Initialize DNA serializer."""
        pass
    
    def serialize(self, dna_data: Dict[str, Any], include_raw: bool = False) -> str:
        """
        Serialize DNA data to canonical JSON string.
        
        Args:
            dna_data: DNA feature dictionary
            include_raw: Whether to include raw binary data (default: False)
            
        Returns:
            Canonical JSON string
        """
        # Create serializable copy
        serializable = self._make_serializable(dna_data, include_raw)
        
        # Sort keys for canonical format
        canonical = self._sort_dict(serializable)
        
        # Serialize with consistent formatting
        return json.dumps(canonical, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    
    def serialize_to_dict(self, dna_data: Dict[str, Any], include_raw: bool = False) -> Dict:
        """
        Serialize DNA data to dictionary (without JSON string conversion).
        
        Args:
            dna_data: DNA feature dictionary
            include_raw: Whether to include raw binary data
            
        Returns:
            Canonical dictionary
        """
        serializable = self._make_serializable(dna_data, include_raw)
        return self._sort_dict(serializable)
    
    def compute_dna_hash(self, dna_data: Dict[str, Any]) -> str:
        """
        Compute deterministic hash of DNA signature.
        
        Args:
            dna_data: DNA feature dictionary
            
        Returns:
            SHA256 hash of canonical DNA
        """
        canonical_json = self.serialize(dna_data, include_raw=False)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    def _make_serializable(self, obj: Any, include_raw: bool = False) -> Any:
        """Convert object to JSON-serializable format."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Skip raw binary data unless explicitly requested
                if key == 'raw_data' and not include_raw:
                    continue
                result[key] = self._make_serializable(value, include_raw)
            return result
        
        elif isinstance(obj, list):
            return [self._make_serializable(item, include_raw) for item in obj]
        
        elif isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        
        elif isinstance(obj, bytes):
            if include_raw:
                return obj.hex()
            else:
                return f"<binary_data:{len(obj)}_bytes>"
        
        elif isinstance(obj, datetime):
            return obj.isoformat()
        
        else:
            # Try to convert to string
            return str(obj)
    
    def _sort_dict(self, obj: Any) -> Any:
        """Recursively sort dictionary keys for canonical format."""
        if isinstance(obj, dict):
            return {k: self._sort_dict(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [self._sort_dict(item) for item in obj]
        else:
            return obj
    
    def compare_dna(self, dna_a: Dict, dna_b: Dict) -> Dict:
        """
        Compare two DNA signatures and return similarity metrics.
        
        Args:
            dna_a: First DNA signature
            dna_b: Second DNA signature
            
        Returns:
            Comparison results with similarity scores
        """
        hash_a = self.compute_dna_hash(dna_a)
        hash_b = self.compute_dna_hash(dna_b)
        
        # Exact match
        if hash_a == hash_b:
            return {
                'identical': True,
                'similarity': 1.0,
                'hash_a': hash_a,
                'hash_b': hash_b
            }
        
        # Feature-based comparison
        similarity_scores = {}
        
        # Compare hashes
        if 'hashes' in dna_a and 'hashes' in dna_b:
            hash_matches = sum(
                1 for key in ['md5', 'sha1', 'sha256']
                if dna_a['hashes'].get(key) == dna_b['hashes'].get(key)
            )
            similarity_scores['hash_similarity'] = hash_matches / 3.0
        
        # Compare strings
        if 'strings' in dna_a and 'strings' in dna_b:
            strings_a = set(s.get('value', '') for s in dna_a['strings'].get('all', []))
            strings_b = set(s.get('value', '') for s in dna_b['strings'].get('all', []))
            
            if strings_a or strings_b:
                intersection = strings_a & strings_b
                union = strings_a | strings_b
                similarity_scores['string_similarity'] = len(intersection) / len(union) if union else 0.0
        
        # Compare imports
        if 'imports' in dna_a and 'imports' in dna_b:
            imports_a = set(i.get('dll', i.get('library', i.get('function', ''))) for i in dna_a['imports'])
            imports_b = set(i.get('dll', i.get('library', i.get('function', ''))) for i in dna_b['imports'])
            
            if imports_a or imports_b:
                intersection = imports_a & imports_b
                union = imports_a | imports_b
                similarity_scores['import_similarity'] = len(intersection) / len(union) if union else 0.0
        
        # Overall similarity (weighted average)
        if similarity_scores:
            overall_similarity = sum(similarity_scores.values()) / len(similarity_scores)
        else:
            overall_similarity = 0.0
        
        return {
            'identical': False,
            'similarity': overall_similarity,
            'hash_a': hash_a,
            'hash_b': hash_b,
            'feature_similarities': similarity_scores
        }

