# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/ml/inference/fingerprinter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generate Locality Sensitive Hash (LSH) or embedding for DNA clustering

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import ML libraries
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available for fingerprinting")


class DNAFingerprinter:
    """
    Generate fingerprints (LSH/embeddings) from DNA signatures for clustering.
    """
    
    def __init__(self, vectorizer: Optional[Any] = None):
        """
        Initialize fingerprinter.
        
        Args:
            vectorizer: Optional pre-trained vectorizer (TF-IDF or similar)
        """
        self.vectorizer = vectorizer
        if vectorizer is None and SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 3))
    
    def generate_fingerprint(self, dna_data: Dict, method: str = 'lsh') -> Dict:
        """
        Generate fingerprint from DNA data.
        
        Args:
            dna_data: DNA feature dictionary
            method: Fingerprinting method ('lsh', 'hash', 'embedding')
            
        Returns:
            Fingerprint dictionary
        """
        if method == 'lsh':
            return self._generate_lsh(dna_data)
        elif method == 'hash':
            return self._generate_hash(dna_data)
        elif method == 'embedding':
            return self._generate_embedding(dna_data)
        else:
            raise ValueError(f"Unknown fingerprinting method: {method}")
    
    def _generate_lsh(self, dna_data: Dict) -> Dict:
        """
        Generate Locality Sensitive Hash fingerprint.
        
        Args:
            dna_data: DNA feature dictionary
            
        Returns:
            LSH fingerprint
        """
        # Extract key features for LSH
        features = []
        
        # Hash values
        hashes = dna_data.get('hashes', {})
        features.append(hashes.get('md5', '')[:16])  # First 16 chars
        features.append(hashes.get('sha256', '')[:32])  # First 32 chars
        
        # Entropy signature
        entropy = dna_data.get('entropy', {})
        features.append(f"ent_{entropy.get('overall', 0):.2f}")
        features.append(f"ent_max_{entropy.get('max', 0):.2f}")
        
        # Import signatures
        imports = dna_data.get('imports', [])
        import_names = [i.get('dll', i.get('library', i.get('function', ''))) for i in imports[:10]]
        features.extend(import_names)
        
        # Suspicious strings
        strings = dna_data.get('strings', {})
        suspicious = strings.get('suspicious', [])[:5]
        for s in suspicious:
            features.append(s.get('value', '')[:20])
        
        # Combine and hash
        feature_string = '|'.join(str(f) for f in features)
        lsh_hash = hashlib.sha256(feature_string.encode()).hexdigest()
        
        return {
            'method': 'lsh',
            'fingerprint': lsh_hash,
            'feature_count': len(features),
            'similarity_key': feature_string[:100]  # For debugging
        }
    
    def _generate_hash(self, dna_data: Dict) -> Dict:
        """
        Generate simple hash fingerprint.
        
        Args:
            dna_data: DNA feature dictionary
            
        Returns:
            Hash fingerprint
        """
        # Serialize key features
        key_features = {
            'hashes': dna_data.get('hashes', {}),
            'entropy_overall': dna_data.get('entropy', {}).get('overall', 0),
            'imports_count': len(dna_data.get('imports', [])),
            'strings_suspicious_count': dna_data.get('strings', {}).get('suspicious_count', 0)
        }
        
        feature_json = json.dumps(key_features, sort_keys=True)
        fingerprint = hashlib.sha256(feature_json.encode()).hexdigest()
        
        return {
            'method': 'hash',
            'fingerprint': fingerprint,
            'feature_hash': hashlib.md5(feature_json.encode()).hexdigest()
        }
    
    def _generate_embedding(self, dna_data: Dict) -> Dict:
        """
        Generate embedding vector fingerprint.
        
        Args:
            dna_data: DNA feature dictionary
            
        Returns:
            Embedding fingerprint
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available, falling back to hash method")
            return self._generate_hash(dna_data)
        
        # Extract text features for TF-IDF
        text_features = []
        
        # Import names
        imports = dna_data.get('imports', [])
        import_text = ' '.join(i.get('dll', i.get('library', i.get('function', ''))) for i in imports)
        text_features.append(import_text)
        
        # Suspicious strings
        strings = dna_data.get('strings', {})
        suspicious = strings.get('suspicious', [])
        string_text = ' '.join(s.get('value', '') for s in suspicious[:20])
        text_features.append(string_text)
        
        # Combine
        combined_text = ' '.join(text_features)
        
        # Vectorize
        if self.vectorizer is not None:
            try:
                embedding = self.vectorizer.transform([combined_text])
                embedding_array = embedding.toarray()[0]
                
                return {
                    'method': 'embedding',
                    'fingerprint': embedding_array.tolist(),
                    'dimension': len(embedding_array),
                    'norm': float(np.linalg.norm(embedding_array))
                }
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                return self._generate_hash(dna_data)
        else:
            return self._generate_hash(dna_data)
    
    def compare_fingerprints(self, fp1: Dict, fp2: Dict) -> float:
        """
        Compare two fingerprints and return similarity score.
        
        Args:
            fp1: First fingerprint
            fp2: Second fingerprint
            
        Returns:
            Similarity score (0-1)
        """
        method1 = fp1.get('method', 'hash')
        method2 = fp2.get('method', 'hash')
        
        if method1 != method2:
            logger.warning(f"Comparing different fingerprint methods: {method1} vs {method2}")
        
        if method1 == 'hash' or method2 == 'hash':
            # Compare hash fingerprints
            fp1_val = fp1.get('fingerprint', '')
            fp2_val = fp2.get('fingerprint', '')
            
            if fp1_val == fp2_val:
                return 1.0
            else:
                # Hamming distance for hex strings
                return self._hex_hamming_similarity(fp1_val, fp2_val)
        
        elif method1 == 'embedding' and method2 == 'embedding':
            # Cosine similarity for embeddings
            if SKLEARN_AVAILABLE:
                emb1 = np.array(fp1.get('fingerprint', []))
                emb2 = np.array(fp2.get('fingerprint', []))
                
                if len(emb1) == len(emb2) and len(emb1) > 0:
                    similarity = cosine_similarity([emb1], [emb2])[0][0]
                    return float(max(0.0, similarity))  # Ensure non-negative
            
            return 0.0
        
        else:
            # LSH comparison
            fp1_val = fp1.get('fingerprint', '')
            fp2_val = fp2.get('fingerprint', '')
            
            if fp1_val == fp2_val:
                return 1.0
            else:
                return self._hex_hamming_similarity(fp1_val, fp2_val)
    
    def _hex_hamming_similarity(self, hex1: str, hex2: str) -> float:
        """Calculate similarity based on Hamming distance of hex strings."""
        if len(hex1) != len(hex2):
            return 0.0
        
        matches = sum(c1 == c2 for c1, c2 in zip(hex1, hex2))
        return matches / len(hex1) if len(hex1) > 0 else 0.0

