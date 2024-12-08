"""
Tests for the rate limiter implementation.
"""
import pytest
import time
from src.utils.rate_limiter import TokenBucket, RateLimiter

def test_token_bucket_initialization():
    """Test token bucket initialization."""
    bucket = TokenBucket(capacity=10, fill_rate=1)
    assert bucket.capacity == 10
    assert bucket.fill_rate == 1
    assert bucket.tokens == 10

def test_token_bucket_acquire():
    """Test token acquisition."""
    bucket = TokenBucket(capacity=5, fill_rate=1)
    
    # Should be able to acquire immediately
    wait_time = bucket.try_acquire(tokens=1, block=False)
    assert wait_time == 0
    assert bucket.tokens == 4
    
    # Acquire all remaining tokens
    for _ in range(4):
        wait_time = bucket.try_acquire(tokens=1, block=False)
        assert wait_time == 0
    
    # Should need to wait when bucket is empty
    wait_time = bucket.try_acquire(tokens=1, block=False)
    assert wait_time > 0

def test_token_bucket_refill():
    """Test token refill over time."""
    bucket = TokenBucket(capacity=2, fill_rate=1)  # 1 token per second
    
    # Use all tokens
    bucket.try_acquire(tokens=2, block=True)
    assert bucket.tokens < 1
    
    # Wait for refill
    time.sleep(1.1)  # Wait slightly more than 1 second
    bucket._add_tokens()  # Manually trigger token addition
    
    assert bucket.tokens >= 1

def test_rate_limiter():
    """Test the rate limiter for both public and private endpoints."""
    limiter = RateLimiter()
    
    # Test public endpoint rate limiting
    wait_time = limiter.acquire(private=False, block=False)
    assert wait_time == 0  # First request should be immediate
    
    # Exhaust public rate limit
    for _ in range(14):  # We already used one above
        limiter.acquire(private=False, block=True)
    
    # Next request should need to wait
    wait_time = limiter.acquire(private=False, block=False)
    assert wait_time > 0
    
    # Test private endpoint rate limiting
    wait_time = limiter.acquire(private=True, block=False)
    assert wait_time == 0  # First request should be immediate
    
    # Exhaust private rate limit
    for _ in range(14):  # We already used one above
        limiter.acquire(private=True, block=True)
    
    # Next request should need to wait
    wait_time = limiter.acquire(private=True, block=False)
    assert wait_time > 0
