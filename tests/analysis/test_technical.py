"""
Tests for technical analysis module.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, create_autospec
from src.analysis.technical import TechnicalAnalysis, TradingSignal
from src.market_data.kraken_client import KrakenClient

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing"""
    # Generate enough data points for valid indicator calculation
    data = []
    base_price = 10000.0
    volatility = 0.02  # 2% daily volatility
    
    # Generate 60 days of data for Ichimoku calculations
    for i in range(60):
        # Add some trending behavior
        trend = np.sin(i / 10) * 0.01  # Slow sine wave trend
        daily_return = np.random.normal(trend, volatility)
        close = base_price * (1 + daily_return)
        
        # Create more realistic high/low values
        daily_range = close * volatility
        high = close + abs(np.random.normal(0, daily_range))
        low = close - abs(np.random.normal(0, daily_range))
        
        data.append([
            1600000000 + i*86400,  # daily timestamps
            close * 0.99,  # open slightly lower
            high,
            low,
            close,
            np.random.uniform(1, 3)  # random volume between 1-3
        ])
        base_price = close  # use previous close as next base
    return data

@pytest.fixture
def mock_kraken_client(sample_ohlcv_data):
    """Create a mock KrakenClient"""
    client = create_autospec(KrakenClient)
    client.get_ohlcv = Mock(return_value=sample_ohlcv_data)
    return client

@pytest.fixture
def technical_analyzer(mock_kraken_client):
    """Create TechnicalAnalysis instance with mock client"""
    return TechnicalAnalysis(mock_kraken_client)

class TestTechnicalAnalysis:
    def test_rsi_calculation(self, technical_analyzer):
        """Test RSI calculation"""
        rsi = technical_analyzer.get_rsi("BTC/USD")
        assert isinstance(rsi, float)
        assert 0 <= rsi <= 100

    def test_analyze_basic(self, technical_analyzer):
        """Test basic analysis with default parameters"""
        result = technical_analyzer.analyze(["BTC/USD"])
        assert "BTC/USD" in result
        assert "rsi" in result["BTC/USD"]
        assert "macd" in result["BTC/USD"]
        assert "bb_upper" in result["BTC/USD"]

    def test_analyze_with_specific_indicators(self, technical_analyzer):
        """Test analysis with specific indicators"""
        result = technical_analyzer.analyze(["BTC/USD"], indicators=["macd"])
        assert "macd" in result["BTC/USD"]
        assert "bb_upper" not in result["BTC/USD"]

    def test_support_resistance_levels(self, technical_analyzer):
        """Test support and resistance level identification"""
        support, resistance = technical_analyzer.get_support_resistance_levels("BTC/USD")
        assert isinstance(support, list)
        assert isinstance(resistance, list)
        assert all(isinstance(x, float) for x in support)
        assert all(isinstance(x, float) for x in resistance)
        assert len(support) > 0
        assert len(resistance) > 0
        assert min(support) <= max(support)  # Support levels are ordered
        assert min(resistance) <= max(resistance)  # Resistance levels are ordered

    def test_trend_identification(self, technical_analyzer):
        """Test trend identification functionality"""
        trend = technical_analyzer.identify_trend("BTC/USD")
        assert trend in ['uptrend', 'downtrend', 'sideways']

    def test_volume_profile(self, technical_analyzer):
        """Test volume profile analysis"""
        profile = technical_analyzer.analyze_volume_profile("BTC/USD")
        assert isinstance(profile, dict)
        assert 'price_levels' in profile
        assert 'volumes' in profile
        assert len(profile['price_levels']) > 0
        assert len(profile['volumes']) == len(profile['price_levels']) - 1

    def test_signal_generation(self, technical_analyzer):
        """Test trading signal generation based on multiple indicators"""
        analysis = technical_analyzer.analyze(['BTC/USD'])
        signal = technical_analyzer.generate_signal("BTC/USD", analysis['BTC/USD'])
        
        # Verify signal structure
        assert isinstance(signal, TradingSignal)
        assert signal.pair == 'BTC/USD'
        assert signal.signal in ['buy', 'sell', 'neutral']
        assert 0 <= signal.strength <= 1
        assert isinstance(signal.indicators, dict)
        assert isinstance(signal.timestamp, float)

    def test_ichimoku_cloud(self, technical_analyzer):
        """Test Ichimoku Cloud calculation"""
        result = technical_analyzer.analyze(["BTC/USD"], indicators=["ichimoku"])
        cloud = result["BTC/USD"]["ichimoku"]
        
        # Check all components are present
        assert "tenkan_sen" in cloud
        assert "kijun_sen" in cloud
        assert "senkou_span_a" in cloud
        assert "senkou_span_b" in cloud
        assert "chikou_span" in cloud
        assert "metadata" in cloud
        
        # Check values are reasonable
        for key, value in cloud.items():
            if key != "metadata":
                assert isinstance(value, float)
                assert value > 0
        
        # Verify cloud relationship
        span_a = cloud["senkou_span_a"]
        span_b = cloud["senkou_span_b"]
        if span_a > span_b:
            assert cloud["metadata"]["cloud_color"] == "green"
        elif span_b > span_a:
            assert cloud["metadata"]["cloud_color"] == "red"

    def test_atr_volatility(self, technical_analyzer):
        """Test ATR-based volatility metrics"""
        result = technical_analyzer.analyze(["BTC/USD"], indicators=["atr"])
        atr_data = result["BTC/USD"]["atr"]
        
        # Check ATR components
        assert "atr" in atr_data
        assert "atr_percent" in atr_data
        assert "volatility_level" in atr_data
        
        # Validate ATR values
        assert isinstance(atr_data["atr"], float)
        assert atr_data["atr"] > 0
        assert 0 <= atr_data["atr_percent"] <= 100
        assert atr_data["volatility_level"] in ["low", "medium", "high"]
        
        # Test ATR calculation consistency
        high_atr = technical_analyzer.analyze(["BTC/USD"], indicators=["atr"], atr_period=5)["BTC/USD"]["atr"]
        low_atr = technical_analyzer.analyze(["BTC/USD"], indicators=["atr"], atr_period=20)["BTC/USD"]["atr"]
        assert high_atr["atr"] >= low_atr["atr"]  # Shorter period should be more volatile

    def test_stochastic_oscillator(self, technical_analyzer):
        """Test Stochastic Oscillator calculation"""
        result = technical_analyzer.analyze(['BTC/USD'], indicators=['stochastic'])
        stoch_k = result['BTC/USD']['stoch_k']
        stoch_d = result['BTC/USD']['stoch_d']
        
        # Test value ranges
        assert 0 <= stoch_k <= 100, "Stochastic %K should be between 0 and 100"
        assert 0 <= stoch_d <= 100, "Stochastic %D should be between 0 and 100"
        
        # Test for reasonable values (not just zeros or extreme values)
        assert stoch_k != 0 and stoch_k != 100, "Stochastic %K shows unexpected extreme values"
        assert stoch_d != 0 and stoch_d != 100, "Stochastic %D shows unexpected extreme values"

    def test_macd_histogram(self, technical_analyzer):
        """Test MACD Histogram calculation"""
        result = technical_analyzer.analyze(['BTC/USD'], indicators=['macd'])
        macd_hist = result['BTC/USD']['macd_hist']
        
        # Test that histogram values are calculated
        assert isinstance(macd_hist, float), "MACD histogram should be a float"
        
        # Test relationship with MACD and signal line
        macd = result['BTC/USD']['macd']
        signal = result['BTC/USD']['macd_signal']
        assert abs(macd_hist - (macd - signal)) < 1e-10, "MACD histogram should be difference of MACD and signal line"

    def test_multi_indicator_consensus(self, technical_analyzer):
        """Test that signal generation properly considers multiple indicators"""
        result = technical_analyzer.analyze(['BTC/USD'], indicators=['rsi', 'macd', 'stochastic', 'bollinger'])
        signal = technical_analyzer.generate_signal('BTC/USD', result['BTC/USD'])
        
        # Verify signal structure
        assert isinstance(signal, TradingSignal)
        assert signal.pair == 'BTC/USD'
        assert signal.signal in ['buy', 'sell', 'neutral']
        assert 0 <= signal.strength <= 1
        assert isinstance(signal.indicators, dict)
        
        # Verify indicator weights in signal generation
        assert 'weight_factors' in signal.indicators
        weights = signal.indicators['weight_factors']
        assert 'trend' in weights
        assert 'momentum' in weights
        assert 'volatility' in weights
        
        # Verify consensus calculation
        assert 'consensus_score' in signal.indicators
        assert -1 <= signal.indicators['consensus_score'] <= 1

    def test_signal_strength_validation(self, technical_analyzer):
        """Test signal strength calculation and validation"""
        # Test with conflicting indicators
        conflicting_data = {
            'rsi': 65.0,  # Neutral
            'macd': 0.5,  # Bullish
            'macd_hist': 0.1,  # Bullish
            'stoch_k': 85.0,  # Bearish
            'stoch_d': 82.0,  # Bearish
            'bb_width': 0.02,  # Low volatility
        }
        
        signal = technical_analyzer.generate_signal('BTC/USD', conflicting_data)
        # With conflicting signals, strength should be lower
        assert signal.strength < 0.7
        
        # Test with strong consensus
        strong_consensus_data = {
            'rsi': 25.0,  # Oversold - Bullish
            'macd': 0.5,  # Bullish
            'macd_hist': 0.2,  # Bullish
            'stoch_k': 15.0,  # Oversold - Bullish
            'stoch_d': 18.0,  # Oversold - Bullish
            'bb_width': 0.05,  # Normal volatility
        }
        
        signal = technical_analyzer.generate_signal('BTC/USD', strong_consensus_data)
        # With strong consensus, strength should be higher
        assert signal.strength > 0.7
        assert signal.signal == 'buy'

    def test_market_condition_awareness(self, technical_analyzer):
        """Test that signal generation considers market conditions"""
        # Test high volatility condition
        high_volatility_data = {
            'atr': 500.0,  # High ATR
            'bb_width': 0.08,  # Wide Bollinger Bands
            'rsi': 65.0,
            'macd': 0.5
        }
        
        signal = technical_analyzer.generate_signal('BTC/USD', high_volatility_data)
        assert 'volatility_adjustment' in signal.indicators
        assert signal.strength < 0.8  # High volatility should reduce signal strength
        
        # Test trending market condition
        trending_data = {
            'ema_20': 45000,
            'ema_50': 43000,
            'rsi': 65.0,
            'macd': 0.5,
            'trend': 'uptrend'
        }
        
        signal = technical_analyzer.generate_signal('BTC/USD', trending_data)
        assert 'trend_confidence' in signal.indicators
        # Strong trend should increase signal strength for aligned signals
        if signal.signal == 'buy':
            assert signal.strength > 0.6
