"""
Tests for news sentiment analysis functionality.
"""
import unittest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.sentiment.news_analyzer import NewsAnalyzer

class TestNewsAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.news_analyzer = NewsAnalyzer()
        
        # Sample news data
        self.test_news_data = pd.DataFrame({
            'title': [
                'Bitcoin Surges to New Highs',
                'Major Bank Adopts Cryptocurrency',
                'Crypto Market Faces Uncertainty'
            ],
            'body': [
                'Bitcoin price reaches unprecedented levels as institutional adoption grows.',
                'Leading financial institution announces crypto integration services.',
                'Market analysts express concerns over regulatory challenges.'
            ],
            'source': ['CoinDesk', 'Reuters', 'CryptoNews'],
            'source_rating': [8.5, 9.5, 7.0],  # Out of 10
            'published_on': [
                datetime.now() - timedelta(hours=1),
                datetime.now() - timedelta(hours=2),
                datetime.now() - timedelta(hours=3)
            ]
        })
        
    def test_calculate_news_sentiment(self):
        """Test basic sentiment calculation from news content."""
        sentiment_scores = self.news_analyzer.calculate_news_sentiment(self.test_news_data)
        
        # Verify sentiment scores are calculated for each article
        self.assertEqual(len(sentiment_scores), len(self.test_news_data))
        
        # Verify sentiment scores are in the expected range (-1 to 1)
        for score in sentiment_scores:
            self.assertGreaterEqual(score, -1)
            self.assertLessEqual(score, 1)
            
    def test_weighted_sentiment_score(self):
        """Test sentiment calculation with source credibility weighting."""
        weighted_scores = self.news_analyzer.calculate_weighted_sentiment(self.test_news_data)
        
        # Verify weighted scores are calculated
        self.assertEqual(len(weighted_scores), len(self.test_news_data))
        
        # Verify higher rated sources have more impact
        high_rated_source = self.test_news_data[
            self.test_news_data['source_rating'] == self.test_news_data['source_rating'].max()
        ].index[0]
        
        low_rated_source = self.test_news_data[
            self.test_news_data['source_rating'] == self.test_news_data['source_rating'].min()
        ].index[0]
        
        # Higher rated source should have more weight in final sentiment
        self.assertGreater(
            abs(weighted_scores[high_rated_source]),
            abs(weighted_scores[low_rated_source])
        )
        
    def test_invalid_input_handling(self):
        """Test handling of invalid input data."""
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError):
            self.news_analyzer.calculate_news_sentiment(empty_df)
            
        # Test with missing required columns
        invalid_df = pd.DataFrame({'title': ['Test']})
        with self.assertRaises(ValueError):
            self.news_analyzer.calculate_news_sentiment(invalid_df)
            
    def test_source_rating_normalization(self):
        """Test that source ratings are properly normalized."""
        # Create test data with extreme ratings
        test_data = self.test_news_data.copy()
        test_data['source_rating'] = [15.0, 5.0, 0.0]  # Out of range values
        
        weighted_scores = self.news_analyzer.calculate_weighted_sentiment(test_data)
        
        # Verify scores are still in valid range (-1 to 1)
        for score in weighted_scores:
            self.assertGreaterEqual(score, -1)
            self.assertLessEqual(score, 1)

if __name__ == '__main__':
    unittest.main()
