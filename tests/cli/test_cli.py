"""
Tests for the command-line interface.
"""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from src.cli.commands import cli

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_kraken():
    with patch('src.cli.commands.KrakenClient') as mock:
        instance = mock.return_value
        instance.get_ticker_info.return_value = {
            'XBT/USD': {'last': 45000.0},
            'ETH/USD': {'last': 2800.0},
            'BTC/USD': {'last': 45000.0}  # Added for query test
        }
        yield instance

@pytest.fixture
def mock_analyzer():
    with patch('src.cli.commands.TechnicalAnalysis') as mock:
        instance = mock.return_value
        instance.analyze.return_value = {
            'XBT/USD': {'rsi': 55, 'macd': 100},
            'ETH/USD': {'rsi': 45, 'macd': -50}
        }
        instance.get_rsi.return_value = 55.0
        yield instance

@pytest.fixture
def mock_recommender():
    with patch('src.cli.commands.TradeRecommender') as mock:
        instance = mock.return_value
        instance.get_recommendations.return_value = {
            'XBT/USD': {'signal': 'BUY', 'confidence': 80},
            'ETH/USD': {'signal': 'HOLD', 'confidence': 60}
        }
        yield instance

def test_fetch_data(runner, mock_kraken):
    result = runner.invoke(cli, ['fetch-data', 'XBT/USD'])
    assert result.exit_code == 0
    assert '45000.0' in result.output
    mock_kraken.get_ticker_info.assert_called_once_with(['XBT/USD'])

def test_analyze(runner, mock_analyzer):
    result = runner.invoke(cli, ['analyze', 'XBT/USD', '--indicators', 'rsi,macd'])
    assert result.exit_code == 0
    assert 'rsi' in result.output
    assert 'macd' in result.output
    mock_analyzer.analyze.assert_called_once()

def test_recommend(runner, mock_recommender):
    result = runner.invoke(cli, ['recommend', 'XBT/USD', '--risk-level', 'low'])
    assert result.exit_code == 0
    assert 'signal' in result.output
    mock_recommender.get_recommendations.assert_called_once()

def test_query_price(runner, mock_kraken):
    result = runner.invoke(cli, ['query'], input="what's the btc price?\nexit\n")
    assert result.exit_code == 0
    assert 'BTC/USD: $45,000.00' in result.output

def test_query_rsi(runner, mock_analyzer):
    result = runner.invoke(cli, ['query'], input="show me btc rsi\nexit\n")
    assert result.exit_code == 0
    assert '55.0' in result.output

def test_query_unknown(runner):
    result = runner.invoke(cli, ['query'], input="what's the meaning of life?\nexit\n")
    assert result.exit_code == 0
    assert "I don't understand" in result.output
