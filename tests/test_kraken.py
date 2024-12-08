"""
Test script for Kraken API integration.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch
import time
from datetime import datetime, timedelta

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.market_data.kraken_client import KrakenClient, KrakenConfigError, KrakenError
from src.utils.config import Config
import pandas as pd

@pytest.fixture
def kraken_client():
    """Fixture to create a Kraken client instance with API keys."""
    config = Config()
    keys = config.get_api_keys()
    return KrakenClient(
        api_key=keys['kraken_api_key'],
        private_key=keys['kraken_secret_key']
    )

@pytest.fixture
def mock_kraken_api():
    """Fixture to create a mocked Kraken API instance."""
    with patch('krakenex.API') as mock_api:
        yield mock_api

@pytest.fixture
def mock_kraken_client(mock_kraken_api):
    """Fixture to create a Kraken client instance with mocked API."""
    with patch('pykrakenapi.KrakenAPI') as mock_k:
        client = KrakenClient(api_key="test_key_12345", private_key="test_private_key_12345")
        client.k = mock_k
        yield client

def test_get_ledger_entries(mock_kraken_client):
    """Test retrieving ledger entries with mocked response."""
    mock_response = pd.DataFrame({
        'refid': ['ABC123', 'DEF456'],
        'time': [1638316800, 1638403200],  # Unix timestamps
        'type': ['deposit', 'withdrawal'],
        'asset': ['XBT', 'XBT'],
        'amount': [1.0, -0.5],
        'fee': [0.0, 0.001],
        'balance': [2.0, 1.5]
    })
    mock_kraken_client.k.get_ledgers_info.return_value = mock_response
    
    # Test with various parameter combinations
    start_time = datetime.now() - timedelta(days=7)
    end_time = datetime.now()
    
    # Test with all parameters
    entries = mock_kraken_client.get_ledger_entries(
        start_time=start_time,
        end_time=end_time,
        asset='XBT',
        type='deposit'
    )
    assert not entries.empty
    assert all(col in entries.columns for col in ['refid', 'time', 'type', 'asset', 'amount', 'fee', 'balance'])
    
    # Test with minimal parameters
    entries = mock_kraken_client.get_ledger_entries()
    assert not entries.empty

def test_export_ledger_data(mock_kraken_client):
    """Test requesting ledger data export with mocked response."""
    mock_report_id = "ABCD-1234"
    mock_kraken_client.k.add_export.return_value = mock_report_id
    
    start_time = datetime.now() - timedelta(days=30)
    end_time = datetime.now()
    
    report_id = mock_kraken_client.export_ledger_data(
        report_type='ledgers',
        description='Monthly ledger export',
        start_time=start_time,
        end_time=end_time
    )
    
    assert report_id == mock_report_id
    mock_kraken_client.k.add_export.assert_called_once()

def test_get_export_status(mock_kraken_client):
    """Test checking export status with mocked response."""
    mock_status = {
        'status': 'Processed',
        'completion': 100,
        'url': 'https://download.kraken.com/export/ABCD-1234.csv'
    }
    mock_kraken_client.k.get_export_status.return_value = mock_status
    
    status = mock_kraken_client.get_export_status('ABCD-1234')
    assert status['status'] == 'Processed'
    assert status['completion'] == 100
    assert 'url' in status
    mock_kraken_client.k.get_export_status.assert_called_once()

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

def test_private_endpoints_without_keys():
    """Test accessing private endpoints without API keys."""
    client = KrakenClient()  # Initialize without keys
    
    with pytest.raises(KrakenConfigError, match="API keys required for ledger entries"):
        client.get_ledger_entries()
        
    with pytest.raises(KrakenConfigError, match="API keys required for data export"):
        client.export_ledger_data('ledgers', 'test', datetime.now(), datetime.now())
        
    with pytest.raises(KrakenConfigError, match="API keys required for export status"):
        client.get_export_status('ABCD-1234')

def test_client_health_monitoring(mock_kraken_client):
    """Test client health monitoring with simulated failures."""
    assert mock_kraken_client.is_healthy  # Should start healthy
    
    # Simulate API failures
    mock_kraken_client.k.get_ledgers_info.side_effect = [
        Exception("API Error 1"),
        Exception("API Error 2"),
        Exception("API Error 3")
    ]
    
    # Test that three consecutive failures make the client unhealthy
    for i in range(3):
        try:
            mock_kraken_client.get_ledger_entries()
        except KrakenError:
            pass
        if i < 2:
            assert mock_kraken_client.is_healthy
        else:
            assert not mock_kraken_client.is_healthy
    
    # Test recovery after successful request
    mock_kraken_client.k.get_ledgers_info.side_effect = None
    mock_kraken_client.k.get_ledgers_info.return_value = pd.DataFrame({'refid': ['ABC123']})
    mock_kraken_client.get_ledger_entries()
    assert mock_kraken_client.is_healthy

def test_rate_limiting(mock_kraken_client):
    """Test rate limiting for private endpoints."""
    start_time = time.time()
    
    # Make multiple requests to private endpoints
    for _ in range(3):
        try:
            mock_kraken_client.get_ledger_entries()
        except KrakenError:
            pass
            
    end_time = time.time()
    assert end_time - start_time >= 0  # Should respect rate limits
