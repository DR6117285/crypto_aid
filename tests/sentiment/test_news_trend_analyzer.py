"""
Tests for news sentiment trend analysis functionality.
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.sentiment.news_trend_analyzer import NewsTrendAnalyzer
from src.sentiment.news_analyzer import NewsAnalyzer

class TestNewsTrendAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.news_analyzer = NewsAnalyzer()
        self.trend_analyzer = NewsTrendAnalyzer()
        
        # Create time series of news data
        dates = pd.date_range(
            end=datetime.now(),
            periods=48,  # 2 days of hourly data
            freq='h'
        )
        
        # Generate test news data with known trends
        self.test_news_data = pd.DataFrame({
            'title': [
                f'Bitcoin News {i}' for i in range(len(dates))
            ],
            'body': [
                f'This is test news article {i}' for i in range(len(dates))
            ],
            'source': ['CoinDesk' if i % 2 == 0 else 'Reuters' for i in range(len(dates))],
            'source_rating': [8.5 if i % 2 == 0 else 9.5 for i in range(len(dates))],
            'published_on': dates,
            'sentiment': np.concatenate([
                np.linspace(0, 0.8, 24),  # Increasing positive trend
                np.linspace(0.7, -0.5, 24)  # Decreasing negative trend
            ])
        })
        
    def test_detect_sentiment_trend(self):
        """Test detection of sentiment trends over time."""
        trend_results = self.trend_analyzer.detect_trend(
            self.test_news_data,
            window_size=6  # Smaller window to detect trends better
        )
        
        # Verify trend detection for positive trend period
        positive_period = trend_results[trend_results.index < self.test_news_data['published_on'].iloc[24]]
        self.assertEqual(positive_period['trend'].iloc[-1], 'upward')
        self.assertTrue(positive_period['strength'].iloc[-1] > 0.5)
        
        # Verify trend detection for negative trend period
        negative_period = trend_results[trend_results.index >= self.test_news_data['published_on'].iloc[24]]
        self.assertEqual(negative_period['trend'].iloc[-1], 'downward')
        self.assertTrue(negative_period['strength'].iloc[-1] > 0.5)
        
    def test_detect_trend_changes(self):
        """Test detection of significant trend changes."""
        trend_changes = self.trend_analyzer.detect_trend_changes(
            self.test_news_data,
            min_change=0.1  # More sensitive to changes
        )
        
        # Should detect the major trend change at the 24-hour mark
        self.assertGreater(len(trend_changes), 0)
        
        # Verify the timing of trend change
        change_time = trend_changes.index[0]
        expected_time = self.test_news_data['published_on'].iloc[24]
        time_difference = abs((change_time - expected_time).total_seconds())
        self.assertLessEqual(time_difference, 3600)  # Within or equal to 1 hour
        
    def test_calculate_momentum(self):
        """Test calculation of sentiment momentum."""
        momentum = self.trend_analyzer.calculate_momentum(
            self.test_news_data,
            window_size=6  # 6-hour window
        )
        
        # Verify momentum values are calculated
        self.assertEqual(len(momentum), len(self.test_news_data) - 5)  # One less than window size
        
        # Verify momentum direction matches known trends
        early_momentum = momentum.iloc[0]
        late_momentum = momentum.iloc[-1]
        self.assertGreater(early_momentum, 0)  # Positive in first period
        self.assertLess(late_momentum, 0)      # Negative in second period
        
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs."""
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError):
            self.trend_analyzer.detect_trend(empty_df)
            
        # Test with missing required columns
        invalid_df = pd.DataFrame({'title': ['Test']})
        with self.assertRaises(ValueError):
            self.trend_analyzer.detect_trend(invalid_df)
            
        # Test with non-numeric sentiment
        invalid_sentiment_df = pd.DataFrame({
            'sentiment': ['high', 'low'],
            'published_on': self.test_news_data['published_on'][:2]
        })
        with self.assertRaises(ValueError):
            self.trend_analyzer.detect_trend(invalid_sentiment_df)
            
        # Test with invalid window size
        with self.assertRaises(ValueError):
            self.trend_analyzer.detect_trend(
                self.test_news_data,
                window_size=0
            )
            
    def test_trend_strength_calculation(self):
        """Test that trend strength is properly calculated."""
        trend_results = self.trend_analyzer.detect_trend(
            self.test_news_data,
            window_size=12
        )
        
        # Verify strength values are between 0 and 1
        self.assertTrue(all(0 <= strength <= 1 for strength in trend_results['strength']))
        
        # Verify stronger trends have higher strength values
        max_strength = trend_results['strength'].max()
        min_strength = trend_results['strength'].min()
        self.assertGreater(max_strength - min_strength, 0.2)  # Should have significant difference

if __name__ == '__main__':
    unittest.main()
