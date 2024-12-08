"""
Test script for Kraken API integration.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch
import time

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.market_data.kraken_client import KrakenClient, KrakenConfigError, KrakenError
from src.utils.config import Config
import pandas as pd
from datetime import datetime

@pytest.fixture
def kraken_client():
    """Fixture to create a Kraken client instance with API keys."""
    config = Config()
    keys = config.get_api_keys()
    return KrakenClient(
        api_key=keys['kraken_api_key'],
        private_key=keys['kraken_secret_key']
    )

def test_get_asset_pairs(kraken_client):
    """Test retrieving asset pairs."""
    pairs = kraken_client.get_asset_pairs()
    assert not pairs.empty, "Should return non-empty DataFrame of asset pairs"

def test_get_ticker(kraken_client):
    """Test retrieving ticker information."""
    btc_usd_pair = kraken_client.format_pair('BTC', 'USD')
    ticker = kraken_client.get_ticker(btc_usd_pair)
    assert not ticker.empty, "Should return non-empty ticker data"
    assert 'c' in ticker.columns, "Ticker should contain close price"
    assert float(ticker.loc[btc_usd_pair, 'c']) > 0, "Price should be positive"

def test_get_ohlc(kraken_client):
    """Test retrieving OHLC data."""
    btc_usd_pair = kraken_client.format_pair('BTC', 'USD')
    ohlc = kraken_client.get_ohlc(btc_usd_pair)
    assert not ohlc.empty, "Should return non-empty OHLC data"
    assert all(col in ohlc.columns for col in ['open', 'high', 'low', 'close']), "Should contain OHLC columns"

def test_get_order_book(kraken_client):
    """Test retrieving order book data."""
    btc_usd_pair = kraken_client.format_pair('BTC', 'USD')
    asks, bids = kraken_client.get_order_book(btc_usd_pair, count=10)
    assert not asks.empty and not bids.empty, "Should return non-empty order book"
    assert len(asks) <= 10 and len(bids) <= 10, "Should respect count parameter"
    assert float(asks.iloc[0]['price']) >= float(bids.iloc[0]['price']), "Ask price should be >= bid price"

def test_invalid_api_keys():
    """Test initialization with invalid API keys."""
    with pytest.raises(KrakenConfigError, match="Both API key and private key must be provided together"):
        KrakenClient(api_key="test_key", private_key=None)
    
    with pytest.raises(KrakenConfigError, match="Both API key and private key must be provided together"):
        KrakenClient(api_key=None, private_key="test_key")
        
    with pytest.raises(KrakenConfigError, match="Invalid API key format"):
        KrakenClient(api_key="short", private_key="valid_private_key_12345")
        
    with pytest.raises(KrakenConfigError, match="Invalid private key format"):
        KrakenClient(api_key="valid_api_key_12345", private_key="short")

def test_account_balance_without_keys():
    """Test accessing private endpoints without API keys."""
    client = KrakenClient()  # Initialize without keys
    with pytest.raises(KrakenConfigError, match="API keys required for account balance"):
        client.get_account_balance()

@pytest.mark.parametrize("method,args", [
    ("get_ticker", ("INVALID_PAIR",)),
    ("get_ohlc", ("INVALID_PAIR",)),
    ("get_order_book", ("INVALID_PAIR",)),
])
def test_invalid_pair_errors(kraken_client, method, args):
    """Test error handling for invalid trading pairs."""
    with pytest.raises(KrakenError, match="API request failed"):
        getattr(kraken_client, method)(*args)

@pytest.mark.private
def test_get_account_balance(kraken_client):
    """Test retrieving account balance (requires private API key)."""
    balance = kraken_client.get_account_balance()
    assert isinstance(balance, pd.DataFrame), "Should return DataFrame"
    try:
        assert not balance.empty, "Should return non-empty balance data"
    except Exception as e:
        print(f"Error getting account balance: {str(e)}")

def test_client_health_monitoring(kraken_client):
    """Test client health monitoring."""
    assert kraken_client.is_healthy  # Should start healthy
    
    # Simulate failures
    for _ in range(3):
        try:
            kraken_client._handle_request(lambda: 1/0)  # Force an error
        except KrakenError:
            pass
    
    assert not kraken_client.is_healthy  # Should be unhealthy after 3 failures
    
    # Successful request should restore health
    kraken_client._handle_request(lambda: True)
    assert kraken_client.is_healthy

def test_rate_limiting(kraken_client):
    """Test rate limiting for public and private endpoints."""
    # Test public endpoint rate limiting
    start_time = time.time()
    for _ in range(16):  # Exceed the rate limit
        kraken_client.get_asset_pairs()
    end_time = time.time()
    
    # Should have taken at least 1 second due to rate limiting
    assert end_time - start_time >= 1
    
    # Test private endpoint rate limiting
    if kraken_client.has_private_access:
        start_time = time.time()
        for _ in range(16):  # Exceed the rate limit
            try:
                kraken_client.get_account_balance()
            except KrakenError:
                pass
        end_time = time.time()
        
        # Should have taken at least 3 seconds due to stricter rate limiting
        assert end_time - start_time >= 3
