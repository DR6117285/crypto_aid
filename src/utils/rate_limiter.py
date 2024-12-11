"""
Rate limiting implementation using token bucket algorithm.
"""
import time
from typing import Dict, Optional
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class TokenBucket:
    """
    Token bucket rate limiter implementation.
    """
    def __init__(self, capacity: int, fill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity (int): Maximum number of tokens the bucket can hold
            fill_rate (float): Rate at which tokens are added (tokens per second)
        """
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = Lock()
        
    def _add_tokens(self) -> None:
        """Add new tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.fill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now
        
    def try_acquire(self, tokens: int = 1, block: bool = True) -> float:
        """
        Try to acquire tokens from the bucket.
        
        Args:
            tokens (int): Number of tokens to acquire
            block (bool): Whether to block until tokens are available
            
        Returns:
            float: Time to wait before proceeding (0 if tokens were acquired)
        """
        with self.lock:
            self._add_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0
            
            if not block:
                required_time = (tokens - self.tokens) / self.fill_rate
                return max(0, required_time)
                
            while self.tokens < tokens:
                required_time = (tokens - self.tokens) / self.fill_rate
                if required_time > 0:
                    time.sleep(required_time)
                self._add_tokens()
            
            self.tokens -= tokens
            return 0

class RateLimiter:
    """
    Rate limiter for API endpoints.
    """
    def __init__(self):
        """Initialize rate limiters for different endpoint types."""
        # Kraken API limits:
        # - Private endpoints: 15 requests per 45 seconds
        # - Public endpoints: More conservative rate - 10 requests per 30 seconds
        self.private_limiter = TokenBucket(capacity=15, fill_rate=1/3)  # 15 per 45 sec
        self.public_limiter = TokenBucket(capacity=10, fill_rate=1/3)   # 10 per 30 sec
        
    def acquire(self, private: bool = False, block: bool = True) -> float:
        """
        Acquire permission to make an API request.
        
        Args:
            private (bool): Whether this is a private API endpoint
            block (bool): Whether to block until permission is granted
            
        Returns:
            float: Time to wait before proceeding (0 if permission granted)
        """
        limiter = self.private_limiter if private else self.public_limiter
        wait_time = limiter.try_acquire(block=block)
        
        if wait_time > 0:
            logger.warning(f"Rate limit reached for {'private' if private else 'public'} endpoint. "
                         f"Need to wait {wait_time:.2f} seconds.")
        
        return wait_time
