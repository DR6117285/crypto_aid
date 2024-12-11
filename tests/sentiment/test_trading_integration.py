import unittest
from unittest.mock import patch, MagicMock
from src.sentiment.trading_integration import SentimentTrader

class TestSentimentTrader(unittest.TestCase):
    def setUp(self):
        self.trader = SentimentTrader()

    def test_generate_trading_signal(self):
        # Test case for neutral sentiment
        self.assertEqual(
            self.trader.generate_trading_signal(0.0),
            "HOLD"
        )
        
        # Test case for strong positive sentiment
        self.assertEqual(
            self.trader.generate_trading_signal(0.8),
            "BUY"
        )
        
        # Test case for strong negative sentiment
        self.assertEqual(
            self.trader.generate_trading_signal(-0.7),
            "SELL"
        )

    def test_calculate_position_size(self):
        # Test position sizing based on sentiment strength
        self.assertEqual(
            self.trader.calculate_position_size(1000.0, 0.8),
            200.0  # 20% of available capital for strong sentiment
        )
        
        self.assertEqual(
            self.trader.calculate_position_size(1000.0, 0.3),
            100.0  # 10% of available capital for moderate sentiment
        )

    def test_execute_sentiment_based_trade(self):
        # Create a mock CryptoCompareClient
        mock_client = MagicMock()
        mock_client.get_latest_sentiment.return_value = 0.8
        mock_client.get_current_price.return_value = 40000.0
        
        # Replace the trader's client with our mock
        self.trader.client = mock_client
        
        trade_decision = self.trader.execute_sentiment_based_trade(
            "BTC",
            available_capital=10000.0
        )
        
        self.assertEqual(trade_decision["action"], "BUY")
        self.assertTrue("position_size" in trade_decision)
        self.assertTrue("sentiment_score" in trade_decision)
        self.assertTrue("current_price" in trade_decision)

if __name__ == '__main__':
    unittest.main()
