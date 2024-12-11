"""
Tests for sentiment visualization functionality.
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.sentiment.visualizer import SentimentVisualizer

class TestSentimentVisualizer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create sample sentiment data
        dates = pd.date_range(start='2024-01-01', end='2024-01-02', freq='h')
        sentiment_values = np.random.normal(loc=0, scale=0.5, size=len(dates))
        self.sentiment_data = pd.DataFrame({
            'sentiment': sentiment_values
        }, index=dates)
        
        # Create sample price data
        price_values = np.cumsum(np.random.normal(loc=0.001, scale=0.02, size=len(dates)))
        price_values = 1000 * np.exp(price_values)  # Convert to realistic prices
        self.price_data = pd.DataFrame({
            'close': price_values
        }, index=dates)
    
    def test_plot_sentiment_trend(self):
        """Test sentiment trend plotting."""
        # Test with sentiment data only
        fig = SentimentVisualizer.plot_sentiment_trend(self.sentiment_data)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 2)  # Main line and MA
        
        # Test with price data
        fig = SentimentVisualizer.plot_sentiment_trend(
            self.sentiment_data,
            price_data=self.price_data
        )
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 3)  # Main line, MA, and price
        
    def test_plot_sentiment_distribution(self):
        """Test sentiment distribution plotting."""
        fig = SentimentVisualizer.plot_sentiment_distribution(self.sentiment_data)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 1)  # Histogram
        
    def test_plot_sentiment_heatmap(self):
        """Test sentiment heatmap plotting."""
        # Test daily heatmap
        fig = SentimentVisualizer.plot_sentiment_heatmap(
            self.sentiment_data,
            time_window='D'
        )
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 1)  # Heatmap
        
        # Test hourly heatmap
        fig = SentimentVisualizer.plot_sentiment_heatmap(
            self.sentiment_data,
            time_window='h'
        )
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 1)  # Heatmap

if __name__ == '__main__':
    unittest.main()
