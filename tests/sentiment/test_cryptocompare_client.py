"""
Tests for the CryptoCompare client.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.sentiment.cryptocompare_client import CryptoCompareClient

@pytest.fixture
def client():
    """Create a CryptoCompare client for testing."""
    return CryptoCompareClient()

def test_init():
    """Test client initialization."""
    with patch('os.getenv', return_value='test_key'):
        with patch('cryptocompare.cryptocompare._set_api_key_parameter') as mock_set_key:
            client = CryptoCompareClient()
            mock_set_key.assert_called_once_with('test_key')

def test_get_price(client):
    """Test getting current price."""
    mock_price_data = {'BTC': {'USD': 50000.0}}
    with patch('cryptocompare.get_price', return_value=mock_price_data):
        price = client.get_price('BTC', 'USD')
        assert price == 50000.0

def test_get_price_error(client):
    """Test error handling when getting price."""
    with patch('cryptocompare.get_price', side_effect=Exception('API Error')):
        price = client.get_price('BTC', 'USD')
        assert price is None

def test_get_social_stats(client):
    """Test getting social stats."""
    mock_stats = {'Data': {'Reddit': {'posts_per_day': 100}}}
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_stats
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        stats = client.get_social_stats('BTC')
        assert stats == mock_stats
        mock_get.assert_called_once()

def test_get_social_stats_error(client):
    """Test error handling when getting social stats."""
    with patch('requests.get', side_effect=Exception('API Error')):
        stats = client.get_social_stats('BTC')
        assert stats == {}

def test_get_historical_price(client):
    """Test getting historical price data."""
    mock_history = [{'time': 1234567890, 'close': 50000.0}]
    with patch('cryptocompare.get_historical_price_day', return_value=mock_history):
        history = client.get_historical_price('BTC', 'USD', limit=1)
        assert history == mock_history

def test_get_historical_price_error(client):
    """Test error handling when getting historical price data."""
    with patch('cryptocompare.get_historical_price_day', 
              side_effect=Exception('API Error')):
        history = client.get_historical_price('BTC', 'USD', limit=1)
        assert history == []

def test_calculate_sentiment_score(client):
    """Test sentiment score calculation."""
    mock_stats = {
        'Data': {
            'Reddit': {
                'posts_per_day': 100,
                'comments_per_day': 1000,
                'active_users': 5000
            },
            'Twitter': {
                'statuses': 2000,
                'followers': 1000000
            }
        }
    }
    
    with patch.object(client, 'get_social_stats', return_value=mock_stats):
        score = client.calculate_sentiment_score('BTC')
        assert -1.0 <= score <= 1.0

def test_calculate_sentiment_score_no_data(client):
    """Test sentiment score calculation with no data."""
    with patch.object(client, 'get_social_stats', return_value={}):
        score = client.calculate_sentiment_score('BTC')
        assert score == 0.0

def test_calculate_sentiment_score_error(client):
    """Test error handling in sentiment score calculation."""
    with patch.object(client, 'get_social_stats', 
                     side_effect=Exception('API Error')):
        score = client.calculate_sentiment_score('BTC')
        assert score == 0.0
