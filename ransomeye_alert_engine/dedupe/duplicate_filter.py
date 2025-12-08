# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/dedupe/duplicate_filter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Exact (SHA256) and Fuzzy (SimHash) deduplication to prevent alert fatigue

import hashlib
from typing import Dict, Any, Optional, Tuple
import logging

from .dedupe_store import DedupeStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimHash:
    """64-bit SimHash implementation for text similarity."""
    
    @staticmethod
    def compute(text: str, hash_bits: int = 64) -> int:
        """
        Compute SimHash for text.
        
        Args:
            text: Input text
            hash_bits: Number of bits in hash (64 for 64-bit SimHash)
            
        Returns:
            SimHash value as integer
        """
        # Tokenize text (simple word-based)
        tokens = text.lower().split()
        
        # Initialize feature vector
        v = [0] * hash_bits
        
        # Hash each token and update feature vector
        for token in tokens:
            # Hash token to get bit positions
            token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16)
            
            for i in range(hash_bits):
                # Check if bit i is set in token_hash
                if token_hash & (1 << (i % 128)):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # Generate fingerprint: set bit i to 1 if v[i] > 0, else 0
        fingerprint = 0
        for i in range(hash_bits):
            if v[i] > 0:
                fingerprint |= (1 << i)
        
        return fingerprint
    
    @staticmethod
    def hamming_distance(hash1: int, hash2: int) -> int:
        """
        Calculate Hamming distance between two SimHashes.
        
        Args:
            hash1: First SimHash
            hash2: Second SimHash
            
        Returns:
            Hamming distance (number of differing bits)
        """
        return bin(hash1 ^ hash2).count('1')

class DuplicateFilter:
    """
    Filter for exact and fuzzy duplicate detection.
    Implements SHA256 for exact duplicates and SimHash for fuzzy duplicates.
    """
    
    def __init__(self, similarity_threshold: int = 3, ttl_seconds: int = 3600):
        """
        Initialize duplicate filter.
        
        Args:
            similarity_threshold: Hamming distance threshold for SimHash (lower = more similar)
            ttl_seconds: Time to live for stored hashes
        """
        self.similarity_threshold = similarity_threshold
        self.store = DedupeStore(ttl_seconds=ttl_seconds)
        self.simhash_store = {}  # Store SimHash values for comparison
    
    def _calculate_exact_hash(self, source: str, alert_type: str, target: str) -> str:
        """
        Calculate exact SHA256 hash of alert fields.
        
        Args:
            source: Alert source
            alert_type: Alert type
            target: Alert target
            
        Returns:
            SHA256 hash as hex string
        """
        content = f"{source}:{alert_type}:{target}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _calculate_simhash(self, source: str, alert_type: str, target: str,
                          metadata: Dict[str, Any]) -> int:
        """
        Calculate SimHash for fuzzy matching.
        
        Args:
            source: Alert source
            alert_type: Alert type
            target: Alert target
            metadata: Alert metadata
            
        Returns:
            SimHash value
        """
        # Combine all text fields
        text_parts = [source, alert_type, target]
        if metadata:
            text_parts.extend([str(v) for v in metadata.values() if isinstance(v, str)])
        
        text = " ".join(text_parts)
        return SimHash.compute(text)
    
    def check_duplicate(self, source: str, alert_type: str, target: str,
                      metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Check if alert is a duplicate (exact or fuzzy).
        
        Args:
            source: Alert source
            alert_type: Alert type
            target: Alert target
            metadata: Optional metadata
            
        Returns:
            Tuple of (is_duplicate, duplicate_type)
            duplicate_type: 'exact', 'fuzzy', or 'none'
        """
        metadata = metadata or {}
        
        # Check exact duplicate
        exact_hash = self._calculate_exact_hash(source, alert_type, target)
        if self.store.has_hash(exact_hash, 'exact'):
            logger.debug("Exact duplicate detected")
            return True, 'exact'
        
        # Check fuzzy duplicate (SimHash)
        simhash_value = self._calculate_simhash(source, alert_type, target, metadata)
        simhash_str = str(simhash_value)
        
        # Check against stored SimHashes
        for stored_simhash_str, stored_simhash_value in self.simhash_store.items():
            stored_value = int(stored_simhash_str)
            distance = SimHash.hamming_distance(simhash_value, stored_value)
            
            if distance <= self.similarity_threshold:
                logger.debug(f"Fuzzy duplicate detected (Hamming distance: {distance})")
                return True, 'fuzzy'
        
        # Not a duplicate, store hashes
        self.store.add_hash(exact_hash, 'exact')
        self.simhash_store[simhash_str] = simhash_value
        
        # Cleanup old SimHashes (simple: keep last N)
        if len(self.simhash_store) > 1000:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self.simhash_store.keys())[:-1000]
            for key in keys_to_remove:
                del self.simhash_store[key]
        
        return False, 'none'

