"""
Tests for backtesting functionality.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.analysis.technical import TechnicalAnalysis, TradingSignal
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
    def test_backtest_basic_functionality(self, backtester, sample_price_data):
        """Test basic backtesting functionality with a simple strategy"""
        # Convert sample data to pandas DataFrame
        df = pd.DataFrame(
            sample_price_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Configure backtest parameters
        initial_capital = 10000.0
        position_size = 0.1  # 10% of capital per trade
        
        # Run backtest
        result = backtester.run(
            pair="BTC/USD",
            start_date=df['timestamp'].min(),
            end_date=df['timestamp'].max(),
            initial_capital=initial_capital,
            position_size=position_size
        )
        
        # Basic assertions
        assert isinstance(result, BacktestResult)
        assert result.pair == "BTC/USD"
        assert result.initial_capital == initial_capital
        assert result.total_trades > 0
        assert result.winning_trades + result.losing_trades == result.total_trades
        assert 0 <= result.win_rate <= 1.0
        assert result.profit_factor > 0
        assert isinstance(result.trades, list)
        assert all(isinstance(trade, Trade) for trade in result.trades)
        
        # Verify trade properties
        for trade in result.trades:
            assert trade.entry_time < trade.exit_time
            assert trade.position_size > 0
            assert trade.profit_loss == (trade.exit_price - trade.entry_price) * trade.position_size
            assert trade.exit_reason in ['take_profit', 'stop_loss', 'signal']
            assert isinstance(trade.entry_signal, TradingSignal)
            
        # Verify performance metrics
        assert 'max_drawdown' in result.metrics
        assert 'sharpe_ratio' in result.metrics
        assert result.max_drawdown <= 0  # drawdown should be negative or zero
        assert isinstance(result.sharpe_ratio, float)
    
    def test_position_sizing(self, backtester, sample_price_data):
        """Test different position sizing strategies"""
        # Convert sample data to pandas DataFrame
        df = pd.DataFrame(
            sample_price_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        initial_capital = 10000.0
        position_size = 0.1
        
        # Test with fixed position size
        result_fixed = backtester.run(
            pair="BTC/USD",
            start_date=df['timestamp'].min(),
            end_date=df['timestamp'].max(),
            initial_capital=initial_capital,
            position_size=position_size
        )
        
        # Test with dynamic position sizing based on volatility
        result_dynamic = backtester.run(
            pair="BTC/USD",
            start_date=df['timestamp'].min(),
            end_date=df['timestamp'].max(),
            initial_capital=initial_capital,
            position_size=position_size,
            dynamic_sizing=True
        )
        
        # Both strategies should generate trades
        assert len(result_fixed.trades) > 0 and len(result_dynamic.trades) > 0
        
        # Dynamic sizing should adjust position sizes based on volatility
        dynamic_sizes = [t.position_size for t in result_dynamic.trades]
        fixed_sizes = [t.position_size for t in result_fixed.trades]
        
        # Dynamic sizes should vary more than fixed sizes
        assert np.std(dynamic_sizes) > np.std(fixed_sizes)
        
        # Dynamic sizing should be more conservative in volatile periods
        # Compare average position sizes in high volatility periods
        high_vol_periods = []
        for i in range(len(df) - 20):
            window = df['close'].iloc[i:i+20]
            volatility = np.std(window) / np.mean(window)
            if volatility > 0.02:  # 2% threshold for high volatility
                high_vol_periods.append(pd.Timestamp(df.index[i+19]).timestamp())  # Convert to timestamp
        
        dynamic_high_vol_sizes = [
            t.position_size for t in result_dynamic.trades 
            if any(abs(t.entry_time.timestamp() - p) <= 86400 for p in high_vol_periods)  # Within 1 day
        ]
        
        fixed_high_vol_sizes = [
            t.position_size for t in result_fixed.trades
            if any(abs(t.entry_time.timestamp() - p) <= 86400 for p in high_vol_periods)  # Within 1 day
        ]
        
        if dynamic_high_vol_sizes and fixed_high_vol_sizes:
            # Dynamic sizing should use smaller positions in high volatility
            assert np.mean(dynamic_high_vol_sizes) < np.mean(fixed_high_vol_sizes)
    
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
