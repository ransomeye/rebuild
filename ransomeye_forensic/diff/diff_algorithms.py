# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/diff/diff_algorithms.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Rolling hash (Rabin-Karp) and entropy calculation algorithms for memory diffing

import hashlib
import math
from typing import Iterator, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RollingHash:
    """
    Rabin-Karp rolling hash implementation for efficient chunk comparison.
    Uses polynomial rolling hash with base 256 and large prime modulus.
    """
    
    def __init__(self, window_size: int = 4096, base: int = 256, modulus: int = 2**61 - 1):
        """
        Initialize rolling hash.
        
        Args:
            window_size: Size of sliding window in bytes
            base: Base for polynomial hash (256 for byte values)
            modulus: Large prime modulus (2^61-1 is a Mersenne prime)
        """
        self.window_size = window_size
        self.base = base
        self.modulus = modulus
        
        # Precompute base^window_size mod modulus for efficient rolling
        self.base_power = pow(base, window_size, modulus)
    
    def compute_hash(self, data: bytes) -> int:
        """
        Compute hash of data block.
        
        Args:
            data: Data bytes (must be exactly window_size)
            
        Returns:
            Hash value
        """
        if len(data) != self.window_size:
            raise ValueError(f"Data must be exactly {self.window_size} bytes")
        
        hash_value = 0
        for byte in data:
            hash_value = (hash_value * self.base + byte) % self.modulus
        
        return hash_value
    
    def roll_hash(self, old_hash: int, old_byte: int, new_byte: int) -> int:
        """
        Roll hash forward by one byte.
        
        Args:
            old_hash: Previous hash value
            old_byte: Byte being removed (first byte of old window)
            new_byte: Byte being added (last byte of new window)
            
        Returns:
            New hash value
        """
        # Remove old byte: (old_hash - old_byte * base^(window_size-1)) * base + new_byte
        new_hash = (old_hash - old_byte * self.base_power) % self.modulus
        new_hash = (new_hash * self.base + new_byte) % self.modulus
        return new_hash
    
    def hash_stream(self, stream: Iterator[bytes], chunk_size: int = 4096) -> Iterator[Tuple[int, bytes, int]]:
        """
        Generate rolling hashes from a byte stream.
        
        Args:
            stream: Iterator yielding bytes
            chunk_size: Size of chunks to read from stream
            
        Yields:
            Tuple of (position, window_data, hash_value)
        """
        buffer = b''
        position = 0
        
        for chunk in stream:
            buffer += chunk
            
            # Process complete windows
            while len(buffer) >= self.window_size:
                window = buffer[:self.window_size]
                hash_value = self.compute_hash(window)
                yield (position, window, hash_value)
                
                # Slide window by one byte
                buffer = buffer[1:]
                position += 1
        
        # Process remaining buffer if it's at least window_size
        while len(buffer) >= self.window_size:
            window = buffer[:self.window_size]
            hash_value = self.compute_hash(window)
            yield (position, window, hash_value)
            buffer = buffer[1:]
            position += 1


class EntropyCalculator:
    """
    Calculate Shannon entropy for binary data to detect packed/encrypted regions.
    """
    
    @staticmethod
    def calculate_entropy(data: bytes, window_size: int = 256) -> float:
        """
        Calculate Shannon entropy of data.
        
        Args:
            data: Data bytes
            window_size: Optional window size for sliding entropy (if None, calculates for entire data)
            
        Returns:
            Entropy value (0-8 for bytes)
        """
        if len(data) == 0:
            return 0.0
        
        # Count byte frequencies
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1
        
        # Calculate Shannon entropy: H = -sum(p(x) * log2(p(x)))
        entropy = 0.0
        data_len = len(data)
        
        for count in byte_counts:
            if count > 0:
                probability = count / data_len
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    @staticmethod
    def calculate_entropy_map(data: bytes, window_size: int = 4096, step: int = 1024) -> list:
        """
        Calculate sliding window entropy map.
        
        Args:
            data: Data bytes
            window_size: Size of sliding window
            step: Step size between windows
            
        Returns:
            List of (position, entropy) tuples
        """
        entropy_map = []
        
        for i in range(0, len(data) - window_size + 1, step):
            window = data[i:i + window_size]
            entropy = EntropyCalculator.calculate_entropy(window)
            entropy_map.append((i, entropy))
        
        return entropy_map
    
    @staticmethod
    def calculate_entropy_delta(entropy_map_a: list, entropy_map_b: list) -> float:
        """
        Calculate average entropy delta between two entropy maps.
        
        Args:
            entropy_map_a: First entropy map (list of (position, entropy))
            entropy_map_b: Second entropy map (list of (position, entropy))
            
        Returns:
            Average absolute entropy difference
        """
        if len(entropy_map_a) != len(entropy_map_b):
            logger.warning("Entropy maps have different lengths, using minimum")
            min_len = min(len(entropy_map_a), len(entropy_map_b))
            entropy_map_a = entropy_map_a[:min_len]
            entropy_map_b = entropy_map_b[:min_len]
        
        if len(entropy_map_a) == 0:
            return 0.0
        
        total_delta = 0.0
        for (pos_a, ent_a), (pos_b, ent_b) in zip(entropy_map_a, entropy_map_b):
            total_delta += abs(ent_a - ent_b)
        
        return total_delta / len(entropy_map_a)

