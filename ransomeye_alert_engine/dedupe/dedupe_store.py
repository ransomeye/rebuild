# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/dedupe/dedupe_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: In-memory store with TTL for recent alert hashes, supports optional Redis backend

import os
import time
from collections import deque
from typing import Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory store only")

class DedupeStore:
    """
    Store for recent alert hashes with TTL.
    Supports in-memory deque or Redis backend.
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 10000,
                 redis_url: Optional[str] = None):
        """
        Initialize dedupe store.
        
        Args:
            ttl_seconds: Time to live for entries in seconds
            max_size: Maximum size of in-memory store
            redis_url: Optional Redis URL (e.g., redis://localhost:6379)
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.redis_url = redis_url or os.environ.get('DEDUPE_STORE_URL')
        
        # In-memory store: deque of (hash, timestamp) tuples
        self.memory_store = deque(maxlen=max_size)
        
        # Redis client (if available and configured)
        self.redis_client = None
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
                logger.info(f"Using Redis backend: {self.redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory store")
                self.redis_client = None
        
        if not self.redis_client:
            logger.info("Using in-memory dedupe store")
    
    def add_hash(self, hash_value: str, hash_type: str = 'exact'):
        """
        Add a hash to the store with current timestamp.
        
        Args:
            hash_value: Hash value to store
            hash_type: Type of hash ('exact' or 'simhash')
        """
        timestamp = time.time()
        key = f"{hash_type}:{hash_value}"
        
        if self.redis_client:
            try:
                self.redis_client.setex(key, self.ttl_seconds, str(timestamp))
            except Exception as e:
                logger.warning(f"Redis error: {e}, falling back to memory")
                self.memory_store.append((key, timestamp))
        else:
            self.memory_store.append((key, timestamp))
    
    def has_hash(self, hash_value: str, hash_type: str = 'exact') -> bool:
        """
        Check if a hash exists in the store and is not expired.
        
        Args:
            hash_value: Hash value to check
            hash_type: Type of hash ('exact' or 'simhash')
            
        Returns:
            True if hash exists and is not expired, False otherwise
        """
        key = f"{hash_type}:{hash_value}"
        current_time = time.time()
        
        if self.redis_client:
            try:
                exists = self.redis_client.exists(key)
                return bool(exists)
            except Exception as e:
                logger.warning(f"Redis error: {e}, checking memory store")
                # Fall back to memory store
        
        # Check memory store
        for stored_key, stored_time in self.memory_store:
            if stored_key == key:
                if current_time - stored_time < self.ttl_seconds:
                    return True
                else:
                    # Expired, remove from store
                    self.memory_store.remove((stored_key, stored_time))
                    return False
        
        return False
    
    def cleanup_expired(self):
        """Remove expired entries from memory store."""
        if self.redis_client:
            # Redis handles TTL automatically
            return
        
        current_time = time.time()
        expired = [
            (key, ts) for key, ts in self.memory_store
            if current_time - ts >= self.ttl_seconds
        ]
        
        for item in expired:
            if item in self.memory_store:
                self.memory_store.remove(item)
    
    def get_stats(self) -> dict:
        """
        Get store statistics.
        
        Returns:
            Dictionary with statistics
        """
        self.cleanup_expired()
        
        stats = {
            'backend': 'redis' if self.redis_client else 'memory',
            'size': len(self.memory_store) if not self.redis_client else 'unknown',
            'ttl_seconds': self.ttl_seconds,
            'max_size': self.max_size
        }
        
        if self.redis_client:
            try:
                stats['redis_size'] = self.redis_client.dbsize()
            except:
                pass
        
        return stats

