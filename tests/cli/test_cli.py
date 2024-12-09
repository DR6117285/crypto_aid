"""
Tests for the command-line interface.
"""
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from datetime import datetime
import json
from src.cli.commands import cli

@pytest.fixture
def cli_runner():
    """Fixture for CLI test runner."""
    return CliRunner()

@pytest.fixture
def mock_kraken():
    """Fixture for mocked Kraken client."""
    with patch('src.cli.commands.KrakenClient') as mock:
        instance = mock.return_value
        # Setup default mock responses
        instance.get_ticker.return_value = {
            "XBT/USD": {
                "price": "50000.0",
                "volume": "100.0",
                "timestamp": datetime.now().isoformat()
            }
        }
        yield instance

def test_fetch_data_basic(cli_runner, mock_kraken):
    """Test basic market data fetching."""
    result = cli_runner.invoke(cli, ['fetch-data', 'XBT/USD'])
    assert result.exit_code == 0
    assert "XBT/USD" in result.output
    assert "50000.0" in result.output

def test_fetch_data_multiple_pairs(cli_runner, mock_kraken):
    """Test fetching data for multiple trading pairs."""
    mock_kraken.get_ticker.return_value = {
        "XBT/USD": {"price": "50000.0"},
        "ETH/USD": {"price": "3000.0"}
    }
    
    result = cli_runner.invoke(cli, ['fetch-data', 'XBT/USD', 'ETH/USD'])
    assert result.exit_code == 0
    assert "XBT/USD" in result.output
    assert "ETH/USD" in result.output

def test_analyze_portfolio(cli_runner):
    """Test portfolio analysis command."""
    portfolio_data = "asset,amount,entry_price\nBTC,1.5,45000\nETH,10,2800\n"
    
    with cli_runner.isolated_filesystem():
        with open('portfolio.csv', 'w') as f:
            f.write(portfolio_data)
            
        result = cli_runner.invoke(cli, ['analyze-portfolio', 'portfolio.csv'])
        assert result.exit_code == 0
        assert "Portfolio Analysis" in result.output
        assert "Total Value" in result.output

def test_recommend_trades(cli_runner, mock_kraken):
    """Test trade recommendations."""
    mock_kraken.get_ticker.return_value = {
        "XBT/USD": {
            "price": "50000.0",
            "rsi": "25",
            "volume": "1000.0"
        }
    }
    
    result = cli_runner.invoke(cli, ['recommend-trades', 'XBT/USD'])
    assert result.exit_code == 0
    assert "Trade Recommendations" in result.output
    assert "BUY" in result.output  # Should recommend buy due to low RSI

def test_error_handling(cli_runner, mock_kraken):
    """Test CLI error handling."""
    mock_kraken.get_ticker.side_effect = Exception("API Error")
    
    result = cli_runner.invoke(cli, ['fetch-data', 'XBT/USD'])
    assert result.exit_code == 1
    assert "Error" in result.output

def test_query_basic(cli_runner):
    """Test basic query functionality."""
    portfolio_data = "asset,amount\nBTC,1.5\nETH,10\n"
    
    with cli_runner.isolated_filesystem():
        with open('portfolio.csv', 'w') as f:
            f.write(portfolio_data)
            
        # Simulate user asking about BTC allocation and then exiting
        result = cli_runner.invoke(cli, ['query'], input='what is my btc allocation?\nexit\n')
        assert result.exit_code == 0
        assert "1.5" in result.output
        assert "BTC" in result.output
