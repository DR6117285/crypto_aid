"""
Tests for the market data visualization components.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.analysis.visualizer import MarketVisualizer

@pytest.fixture
def sample_ohlc_data():
    """Create sample OHLC data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='D')
    data = {
        'open': np.random.uniform(30000, 35000, len(dates)),
        'high': np.random.uniform(35000, 40000, len(dates)),
        'low': np.random.uniform(25000, 30000, len(dates)),
        'close': np.random.uniform(30000, 35000, len(dates)),
        'volume': np.random.uniform(100, 1000, len(dates))
    }
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def sample_order_book():
    """Create sample order book data for testing."""
    asks = pd.DataFrame({
        'price': np.linspace(35000, 36000, 20),
        'volume': np.random.uniform(0.1, 1.0, 20)
    })
    bids = pd.DataFrame({
        'price': np.linspace(34900, 34000, 20),
        'volume': np.random.uniform(0.1, 1.0, 20)
    })
    return asks, bids

def test_plot_candlestick(sample_ohlc_data):
    """Test candlestick chart creation."""
    fig = MarketVisualizer.plot_candlestick(sample_ohlc_data)
    assert fig is not None
    assert len(fig.data) > 0  # Should have at least one trace
    
    # Test with volume
    fig = MarketVisualizer.plot_candlestick(sample_ohlc_data, volume=True)
    assert len(fig.data) > 1  # Should have candlestick and volume traces

def test_plot_order_book(sample_order_book):
    """Test order book visualization."""
    asks, bids = sample_order_book
    fig = MarketVisualizer.plot_order_book(asks, bids)
    assert fig is not None
    assert len(fig.data) == 2  # Should have asks and bids traces
    
    # Test with different depth
    fig = MarketVisualizer.plot_order_book(asks, bids, depth=10)
    for trace in fig.data:
        assert len(trace.x) <= 10  # Should respect depth parameter

def test_plot_price_comparison():
    """Test price comparison chart."""
    dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='D')
    prices = {
        'BTC/USD': pd.Series(np.random.uniform(30000, 35000, len(dates)), index=dates),
        'ETH/USD': pd.Series(np.random.uniform(1800, 2200, len(dates)), index=dates)
    }
    
    fig = MarketVisualizer.plot_price_comparison(prices)
    assert fig is not None
    assert len(fig.data) == 2  # Should have two traces
    
    # Check normalization
    for trace in fig.data:
        assert abs(trace.y[0]) < 1e-10  # First point should be close to 0%
