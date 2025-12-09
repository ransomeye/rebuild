# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/dedup/deduper.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Exact dedup (check DB for existing Fingerprint) and Fuzzy dedup (Levenshtein/SimHash on metadata)

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

# Try to import fuzzy matching libraries
try:
    from Levenshtein import distance as levenshtein_distance
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False
    logger.warning("python-Levenshtein not available. Install: pip install python-Levenshtein")

try:
    import hashlib
    import binascii
    SIMHASH_AVAILABLE = True
except ImportError:
    SIMHASH_AVAILABLE = False

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .fingerprint import IOCFingerprint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IOCDeduplicator:
    """
    Deduplicates IOCs using exact and fuzzy matching.
    - Exact: Check database for existing fingerprint
    - Fuzzy: Use Levenshtein or SimHash on metadata descriptions
    """
    
    def __init__(self, db_store=None):
        """
        Initialize deduplicator.
        
        Args:
            db_store: Database store instance for checking existing IOCs
        """
        self.db_store = db_store
        self.fingerprint_cache: Dict[str, str] = {}  # fingerprint -> ioc_id
    
    def deduplicate(
        self,
        ioc: Dict[str, Any],
        fuzzy_threshold: float = 0.8
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Deduplicate an IOC.
        
        Args:
            ioc: IOC dictionary
            fuzzy_threshold: Similarity threshold for fuzzy matching (0-1)
            
        Returns:
            Tuple of (is_duplicate, existing_ioc_id, match_info)
        """
        # Step 1: Exact deduplication
        fingerprint = IOCFingerprint.generate(ioc)
        exact_match = self._check_exact_duplicate(fingerprint)
        
        if exact_match:
            return True, exact_match, {'method': 'exact', 'fingerprint': fingerprint}
        
        # Step 2: Fuzzy deduplication
        fuzzy_match = self._check_fuzzy_duplicate(ioc, fuzzy_threshold)
        
        if fuzzy_match:
            return True, fuzzy_match[0], {
                'method': 'fuzzy',
                'similarity': fuzzy_match[1],
                'match_type': fuzzy_match[2]
            }
        
        return False, None, None
    
    def _check_exact_duplicate(self, fingerprint: str) -> Optional[str]:
        """
        Check for exact duplicate using fingerprint.
        
        Args:
            fingerprint: IOC fingerprint
            
        Returns:
            Existing IOC ID if found, None otherwise
        """
        # Check cache first
        if fingerprint in self.fingerprint_cache:
            return self.fingerprint_cache[fingerprint]
        
        # Check database if available
        if self.db_store:
            try:
                existing_ioc = self.db_store.get_ioc_by_fingerprint(fingerprint)
                if existing_ioc:
                    ioc_id = existing_ioc.get('id')
                    self.fingerprint_cache[fingerprint] = ioc_id
                    return ioc_id
            except Exception as e:
                logger.error(f"Error checking exact duplicate in DB: {e}")
        
        return None
    
    def _check_fuzzy_duplicate(
        self,
        ioc: Dict[str, Any],
        threshold: float
    ) -> Optional[Tuple[str, float, str]]:
        """
        Check for fuzzy duplicate using similarity matching.
        
        Args:
            ioc: IOC dictionary
            threshold: Similarity threshold
            
        Returns:
            Tuple of (existing_ioc_id, similarity_score, match_type) or None
        """
        if not self.db_store:
            return None
        
        description = ioc.get('description', '')
        value = ioc.get('value', '')
        tags = ioc.get('tags', [])
        
        if not description and not value:
            return None
        
        try:
            # Get similar IOCs from database
            similar_iocs = self.db_store.get_similar_iocs(
                ioc_type=ioc.get('type'),
                value=value,
                limit=100
            )
            
            best_match = None
            best_similarity = 0.0
            match_type = None
            
            for similar_ioc in similar_iocs:
                similar_desc = similar_ioc.get('description', '')
                similar_value = similar_ioc.get('value', '')
                similar_tags = similar_ioc.get('tags', [])
                
                # Calculate similarity scores
                desc_sim = 0.0
                value_sim = 0.0
                tag_sim = 0.0
                
                # Description similarity (Levenshtein)
                if description and similar_desc:
                    desc_sim = self._calculate_similarity(description, similar_desc)
                
                # Value similarity (for domains/URLs)
                if value and similar_value and ioc.get('type') in ['domain', 'url']:
                    value_sim = self._calculate_similarity(value, similar_value)
                
                # Tag similarity (Jaccard)
                if tags and similar_tags:
                    tag_sim = self._jaccard_similarity(tags, similar_tags)
                
                # Weighted combination
                combined_sim = (desc_sim * 0.5) + (value_sim * 0.3) + (tag_sim * 0.2)
                
                if combined_sim > best_similarity and combined_sim >= threshold:
                    best_similarity = combined_sim
                    best_match = similar_ioc.get('id')
                    
                    if desc_sim > value_sim and desc_sim > tag_sim:
                        match_type = 'description'
                    elif value_sim > tag_sim:
                        match_type = 'value'
                    else:
                        match_type = 'tags'
            
            if best_match:
                return (best_match, best_similarity, match_type)
            
        except Exception as e:
            logger.error(f"Error in fuzzy deduplication: {e}")
        
        return None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score (0-1)
        """
        if not str1 or not str2:
            return 0.0
        
        if str1 == str2:
            return 1.0
        
        # Use Levenshtein if available
        if LEVENSHTEIN_AVAILABLE:
            max_len = max(len(str1), len(str2))
            if max_len == 0:
                return 1.0
            
            distance = levenshtein_distance(str1.lower(), str2.lower())
            similarity = 1.0 - (distance / max_len)
            return max(0.0, similarity)
        else:
            # Fallback: simple character overlap
            set1 = set(str1.lower())
            set2 = set(str2.lower())
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            return intersection / union if union > 0 else 0.0
    
    def _jaccard_similarity(self, list1: List[str], list2: List[str]) -> float:
        """
        Calculate Jaccard similarity between two lists.
        
        Args:
            list1: First list
            list2: Second list
            
        Returns:
            Jaccard similarity (0-1)
        """
        set1 = set(list1)
        set2 = set(list2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _simhash(self, text: str) -> int:
        """
        Generate SimHash for text.
        
        Args:
            text: Text to hash
            
        Returns:
            SimHash integer
        """
        # Simplified SimHash implementation
        words = text.lower().split()
        hash_bits = [0] * 64
        
        for word in words:
            word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for i in range(64):
                if word_hash & (1 << i):
                    hash_bits[i] += 1
                else:
                    hash_bits[i] -= 1
        
        simhash = 0
        for i in range(64):
            if hash_bits[i] > 0:
                simhash |= (1 << i)
        
        return simhash
    
    def _simhash_similarity(self, hash1: int, hash2: int) -> float:
        """
        Calculate similarity between two SimHashes.
        
        Args:
            hash1: First SimHash
            hash2: Second SimHash
            
        Returns:
            Similarity score (0-1)
        """
        xor = hash1 ^ hash2
        hamming_distance = bin(xor).count('1')
        similarity = 1.0 - (hamming_distance / 64.0)
        return max(0.0, similarity)

