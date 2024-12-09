"""
Tests for backtesting functionality.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.analysis.technical import TechnicalAnalysis
from src.analysis.backtesting import Backtester, BacktestResult, Trade
from src.market_data.kraken_client import KrakenClient

@pytest.fixture
def sample_price_data():
    """Generate sample OHLCV data for backtesting with clear trading signals"""
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=x) for x in range(100)]
    base_price = 50000.0
    data = []
    
    # Generate price data with clear trends and trading opportunities
    for i, date in enumerate(dates):
        # Create a strong trend every 20 days
        if i % 20 < 10:
            trend = 500  # Uptrend
        else:
            trend = -400  # Downtrend
        
        # Add some volatility
        volatility = np.random.normal(0, 200)
        
        # Calculate day's prices
        close = base_price + trend + volatility
        high = close * 1.02  # 2% higher
        low = close * 0.98   # 2% lower
        open_price = (high + low) / 2
        volume = 10 + abs(trend/100)  # Higher volume during trend moves
        
        data.append([
            int(date.timestamp()),
            float(open_price),
            float(high),
            float(low),
            float(close),
            float(volume)
        ])
        
        base_price = close
    
    return data

@pytest.fixture
def mock_kraken_client(sample_price_data):
    """Create a mock KrakenClient with sample data"""
    class MockKraken:
        def __init__(self, data):
            self.data = data
            
        def get_ohlcv(self, pair, interval='1d', since=None, until=None):
            return self.data
    
    return MockKraken(sample_price_data)

@pytest.fixture
def backtester(mock_kraken_client):
    """Create a Backtester instance with mock client"""
    technical_analyzer = TechnicalAnalysis(mock_kraken_client)
    return Backtester(technical_analyzer)

class TestBacktesting:
    def test_backtest_basic_functionality(self, backtester):
        """Test basic backtesting functionality"""
        result = backtester.run(
            pair="BTC/USD",
            start_date="2024-01-01",
            end_date="2024-04-09",
            initial_capital=10000,
            position_size=0.1  # Use 10% of capital per trade
        )
        
        assert isinstance(result, BacktestResult)
        assert result.pair == "BTC/USD"
        assert result.initial_capital == 10000
        assert isinstance(result.final_capital, float)
        assert isinstance(result.total_trades, int)
        assert isinstance(result.win_rate, float)
        assert 0 <= result.win_rate <= 1
        
        # Verify trades list
        assert isinstance(result.trades, list)
        if result.trades:
            trade = result.trades[0]
            assert isinstance(trade, Trade)
            assert trade.entry_price > 0
            assert trade.exit_price > 0
            assert trade.profit_loss != 0
    
    def test_position_sizing(self, backtester):
        """Test different position sizing strategies"""
        # Test with fixed position size
        result_fixed = backtester.run(
            pair="BTC/USD",
            start_date="2024-01-01",
            end_date="2024-04-09",
            initial_capital=10000,
            position_size=0.1
        )
        
        # Test with dynamic position sizing based on volatility
        result_dynamic = backtester.run(
            pair="BTC/USD",
            start_date="2024-01-01",
            end_date="2024-04-09",
            initial_capital=10000,
            position_size=0.1,
            dynamic_sizing=True
        )
        
        # Dynamic sizing should adjust position size based on volatility
        assert len(result_fixed.trades) > 0 and len(result_dynamic.trades) > 0
        
        # Calculate average position sizes
        fixed_sizes = [t.position_size for t in result_fixed.trades]
        dynamic_sizes = [t.position_size for t in result_dynamic.trades]
        
        # Dynamic sizing should show more variation
        assert np.std(dynamic_sizes) > np.std(fixed_sizes)
    
    def test_risk_management(self, backtester):
        """Test risk management rules"""
        result = backtester.run(
            pair="BTC/USD",
            start_date="2024-01-01",
            end_date="2024-04-09",
            initial_capital=10000,
            position_size=0.1,
            stop_loss=0.02,  # 2% stop loss
            take_profit=0.04  # 4% take profit
        )
        
        # Verify that stop loss and take profit were respected
        for trade in result.trades:
            if trade.exit_reason == 'stop_loss':
                assert trade.profit_loss <= -0.02  # Allow for some slippage
            elif trade.exit_reason == 'take_profit':
                assert trade.profit_loss >= 0.04  # Allow for some slippage
    
    def test_performance_metrics(self, backtester):
        """Test calculation of performance metrics"""
        result = backtester.run(
            pair="BTC/USD",
            start_date="2024-01-01",
            end_date="2024-04-09",
            initial_capital=10000,
            position_size=0.1
        )
        
        # Verify all required metrics are present and valid
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.max_drawdown, float)
        assert isinstance(result.win_rate, float)
        assert isinstance(result.profit_factor, float)
        
        # Verify metric ranges
        assert 0 <= result.win_rate <= 1
        assert 0 <= result.max_drawdown <= 1
        assert result.profit_factor >= 0
    
    def test_market_conditions(self, backtester):
        """Test performance in different market conditions"""
        # Test in trending market
        trend_result = backtester.run(
            pair="BTC/USD",
            start_date="2024-01-01",
            end_date="2024-02-01",  # Period with trend
            initial_capital=10000,
            position_size=0.1
        )
        
        # Test in sideways market
        sideways_result = backtester.run(
            pair="BTC/USD",
            start_date="2024-02-01",
            end_date="2024-03-01",  # Period with sideways movement
            initial_capital=10000,
            position_size=0.1
        )
        
        # Store market condition in results
        assert hasattr(trend_result, 'market_condition')
        assert hasattr(sideways_result, 'market_condition')
        
        # Verify that strategy adapts to different conditions
        assert trend_result.market_condition in ['uptrend', 'downtrend', 'sideways']
        assert sideways_result.market_condition in ['uptrend', 'downtrend', 'sideways']
