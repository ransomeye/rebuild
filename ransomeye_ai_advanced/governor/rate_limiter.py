# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/governor/rate_limiter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Token bucket implementation for rate limiting LLM calls per user/system

import os
import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int  # Maximum tokens
    tokens: float = 0.0  # Current tokens
    refill_rate: float = 0.0  # Tokens per second
    last_refill: float = field(default_factory=time.time)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    async def consume(self, tokens: int) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient
        """
        async with self._lock:
            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    async def get_available_tokens(self) -> float:
        """Get current available tokens."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
            self.last_refill = now
            return self.tokens
    
    async def wait_for_tokens(self, tokens: int, timeout: Optional[float] = None) -> bool:
        """
        Wait until enough tokens are available.
        
        Args:
            tokens: Number of tokens needed
            timeout: Optional timeout in seconds
            
        Returns:
            True if tokens became available, False if timeout
        """
        start_time = time.time()
        while True:
            if await self.consume(tokens):
                return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            # Wait a bit before retrying
            await asyncio.sleep(0.1)


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    Supports per-user and per-system rate limiting.
    """
    
    def __init__(
        self,
        qps_limit: Optional[float] = None,
        burst_size: Optional[int] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            qps_limit: Queries per second limit (from AI_QPS_LIMIT env var)
            burst_size: Burst size (defaults to qps_limit * 2)
        """
        # Get from environment or use defaults
        self.qps_limit = qps_limit or float(os.environ.get('AI_QPS_LIMIT', '10.0'))
        self.burst_size = burst_size or int(self.qps_limit * 2)
        
        # System-wide bucket
        self.system_bucket = TokenBucket(
            capacity=self.burst_size,
            refill_rate=self.qps_limit
        )
        
        # Per-user buckets
        self.user_buckets: Dict[str, TokenBucket] = {}
        self.user_bucket_lock = asyncio.Lock()
        
        # Per-user QPS limits (can be customized)
        self.user_qps_limits: Dict[str, float] = {}
        
        logger.info(f"Rate limiter initialized: QPS={self.qps_limit}, burst={self.burst_size}")
    
    async def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        tokens: int = 1
    ) -> tuple[bool, Optional[float]]:
        """
        Check if request is within rate limit.
        
        Args:
            user_id: Optional user ID for per-user limiting
            tokens: Number of tokens to consume (default 1)
            
        Returns:
            Tuple of (allowed, wait_time_seconds)
            wait_time_seconds is None if allowed, otherwise estimated wait time
        """
        # Check system-wide limit
        system_allowed = await self.system_bucket.consume(tokens)
        if not system_allowed:
            available = await self.system_bucket.get_available_tokens()
            wait_time = max(0, (tokens - available) / self.qps_limit)
            logger.warning(f"System rate limit exceeded, wait {wait_time:.2f}s")
            return False, wait_time
        
        # Check per-user limit if user_id provided
        if user_id:
            user_allowed, user_wait = await self._check_user_limit(user_id, tokens)
            if not user_allowed:
                return False, user_wait
        
        return True, None
    
    async def _check_user_limit(
        self,
        user_id: str,
        tokens: int
    ) -> tuple[bool, Optional[float]]:
        """Check per-user rate limit."""
        async with self.user_bucket_lock:
            # Get or create user bucket
            if user_id not in self.user_buckets:
                user_qps = self.user_qps_limits.get(user_id, self.qps_limit)
                self.user_buckets[user_id] = TokenBucket(
                    capacity=int(user_qps * 2),
                    refill_rate=user_qps
                )
            
            bucket = self.user_buckets[user_id]
        
        # Check user bucket
        user_allowed = await bucket.consume(tokens)
        if not user_allowed:
            available = await bucket.get_available_tokens()
            user_qps = self.user_qps_limits.get(user_id, self.qps_limit)
            wait_time = max(0, (tokens - available) / user_qps)
            logger.warning(f"User {user_id} rate limit exceeded, wait {wait_time:.2f}s")
            return False, wait_time
        
        return True, None
    
    def set_user_limit(self, user_id: str, qps: float):
        """
        Set custom QPS limit for a user.
        
        Args:
            user_id: User ID
            qps: Queries per second limit
        """
        self.user_qps_limits[user_id] = qps
        # Update existing bucket if it exists
        if user_id in self.user_buckets:
            bucket = self.user_buckets[user_id]
            bucket.refill_rate = qps
            bucket.capacity = int(qps * 2)
        logger.info(f"Set user {user_id} QPS limit to {qps}")
    
    async def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        stats = {
            'system_qps_limit': self.qps_limit,
            'system_burst_size': self.burst_size,
            'system_available_tokens': await self.system_bucket.get_available_tokens(),
            'active_users': len(self.user_buckets)
        }
        
        # Add per-user stats
        user_stats = {}
        for user_id, bucket in self.user_buckets.items():
            user_stats[user_id] = {
                'available_tokens': await bucket.get_available_tokens(),
                'qps_limit': self.user_qps_limits.get(user_id, self.qps_limit)
            }
        stats['user_stats'] = user_stats
        
        return stats

