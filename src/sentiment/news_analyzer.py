"""
News sentiment analysis module.
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from textblob import TextBlob

class NewsAnalyzer:
    def __init__(self):
        """Initialize the news analyzer with default configuration."""
        self.config = {
            'min_source_rating': 0.0,
            'max_source_rating': 10.0,
            'title_weight': 0.6,  # Title has more impact than body
            'body_weight': 0.4,
        }
        
    def calculate_news_sentiment(self, news_data: pd.DataFrame) -> pd.Series:
        """
        Calculate sentiment scores for news articles.
        
        Args:
            news_data (pd.DataFrame): DataFrame containing news articles with 'title' and 'body' columns
            
        Returns:
            pd.Series: Series of sentiment scores between -1 and 1
            
        Raises:
            ValueError: If input data is empty or missing required columns
        """
        self._validate_input(news_data, ['title', 'body'])
        
        sentiment_scores = []
        
        for _, article in news_data.iterrows():
            # Calculate sentiment for title and body separately
            title_sentiment = TextBlob(article['title']).sentiment.polarity
            body_sentiment = TextBlob(article['body']).sentiment.polarity
            
            # Combine with weights
            combined_sentiment = (
                title_sentiment * self.config['title_weight'] +
                body_sentiment * self.config['body_weight']
            )
            
            sentiment_scores.append(combined_sentiment)
            
        return pd.Series(sentiment_scores, index=news_data.index)
        
    def calculate_weighted_sentiment(self, news_data: pd.DataFrame) -> pd.Series:
        """
        Calculate sentiment scores weighted by source credibility.
        
        Args:
            news_data (pd.DataFrame): DataFrame containing news with 'title', 'body', and 'source_rating' columns
            
        Returns:
            pd.Series: Series of weighted sentiment scores between -1 and 1
        """
        self._validate_input(news_data, ['title', 'body', 'source_rating'])
        
        # Calculate base sentiment scores
        base_scores = self.calculate_news_sentiment(news_data)
        
        # Normalize source ratings to 0-1 range
        normalized_ratings = self._normalize_ratings(news_data['source_rating'])
        
        # Apply source credibility weights
        weighted_scores = base_scores * normalized_ratings
        
        return weighted_scores
        
    def _validate_input(self, data: pd.DataFrame, required_columns: List[str]) -> None:
        """
        Validate input DataFrame.
        
        Args:
            data (pd.DataFrame): Input data to validate
            required_columns (List[str]): List of required column names
            
        Raises:
            ValueError: If validation fails
        """
        if data.empty:
            raise ValueError("Input DataFrame is empty")
            
        missing_cols = set(required_columns) - set(data.columns)
        if missing_cols:
            raise ValueError(f"Input DataFrame missing required columns: {missing_cols}")
            
    def _normalize_ratings(self, ratings: pd.Series) -> pd.Series:
        """
        Normalize source ratings to 0-1 range.
        
        Args:
            ratings (pd.Series): Series of source ratings
            
        Returns:
            pd.Series: Normalized ratings between 0 and 1
        """
        min_rating = self.config['min_source_rating']
        max_rating = self.config['max_source_rating']
        
        # Clip ratings to valid range
        clipped_ratings = np.clip(ratings, min_rating, max_rating)
        
        # Normalize to 0-1 range
        normalized = (clipped_ratings - min_rating) / (max_rating - min_rating)
        
        return normalized
