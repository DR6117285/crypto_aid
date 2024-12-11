"""
News sentiment trend analysis module.
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta
from scipy import stats

class NewsTrendAnalyzer:
    def __init__(self):
        """Initialize the news trend analyzer with default configuration."""
        self.config = {
            'min_window_size': 3,
            'default_window_size': 12,
            'min_trend_strength': 0.05,  # Adjusted threshold for trend detection
            'significant_change': 0.1,    # Threshold for change detection
            'momentum_threshold': 0.2
        }
        
    def detect_trend(self, news_data: pd.DataFrame, window_size: int = None) -> pd.DataFrame:
        """
        Detect sentiment trends over time.
        
        Args:
            news_data (pd.DataFrame): DataFrame containing news with 'sentiment' and 'published_on' columns
            window_size (int, optional): Size of the rolling window in hours
            
        Returns:
            pd.DataFrame: DataFrame with trend analysis results including:
                - trend: 'upward', 'downward', or 'neutral'
                - strength: trend strength between 0 and 1
                - momentum: rate of sentiment change
                
        Raises:
            ValueError: If input data is invalid or window_size is too small
        """
        # Validate window size first if provided
        if window_size is not None and window_size < self.config['min_window_size']:
            raise ValueError(f"Window size must be at least {self.config['min_window_size']}")
            
        if news_data.empty:
            raise ValueError("Input DataFrame is empty")
            
        self._validate_input(news_data, ['sentiment', 'published_on'])
        
        # Set default window size if not provided
        window_size = window_size or self.config['default_window_size']
        
        if window_size > len(news_data):
            raise ValueError(f"Window size {window_size} cannot be larger than data length {len(news_data)}")
            
        # Sort by time and set index
        df = news_data.copy()
        df = df.sort_values('published_on').set_index('published_on')
        
        # Calculate rolling statistics
        slopes = []
        strengths = []
        momentums = []
        
        for i in range(len(df)):
            if i < window_size - 1:
                window_data = df['sentiment'].iloc[:i+1]
            else:
                window_data = df['sentiment'].iloc[i-window_size+1:i+1]
                
            slope = self._calculate_slope(window_data)
            strength = self._calculate_strength(window_data)
            momentum = self._calculate_momentum_value(window_data)
            
            slopes.append(slope)
            strengths.append(strength)
            momentums.append(momentum)
        
        # Determine trend direction with adjusted threshold
        trends = []
        for slope, strength in zip(slopes, strengths):
            if strength < self.config['min_trend_strength']:
                trends.append('neutral')
            else:
                trends.append('upward' if slope > 0 else 'downward')
        
        return pd.DataFrame({
            'trend': trends,
            'strength': strengths,
            'momentum': momentums
        }, index=df.index)
        
    def detect_trend_changes(self, news_data: pd.DataFrame, min_change: float = None) -> pd.DataFrame:
        """
        Detect significant changes in sentiment trends.
        
        Args:
            news_data (pd.DataFrame): DataFrame containing news with sentiment data
            min_change (float, optional): Minimum change threshold
            
        Returns:
            pd.DataFrame: DataFrame with trend change points and their characteristics
        """
        self._validate_input(news_data, ['sentiment', 'published_on'])
        min_change = min_change or self.config['significant_change']
        
        # Sort by time
        df = news_data.copy().sort_values('published_on')
        df = df.set_index('published_on')
        
        # Calculate rolling mean with smaller window for more sensitivity
        window = min(3, len(df))  # Reduced window size
        smoothed = df['sentiment'].rolling(window=window, min_periods=1).mean()
        
        # Calculate moving average with different windows to detect trend changes
        short_ma = smoothed.rolling(window=3, min_periods=1).mean()
        long_ma = smoothed.rolling(window=6, min_periods=1).mean()
        
        # Calculate changes and detect trend changes
        changes = pd.DataFrame(index=df.index)
        changes['change_magnitude'] = abs(smoothed.diff())
        changes['direction'] = np.sign(smoothed.diff())
        changes['ma_diff'] = short_ma - long_ma
        changes['prev_ma_diff'] = changes['ma_diff'].shift(1)
        changes['is_crossover'] = (
            (changes['prev_ma_diff'] < 0) & (changes['ma_diff'] > 0) |
            (changes['prev_ma_diff'] > 0) & (changes['ma_diff'] < 0)
        )
        changes['sentiment'] = df['sentiment']
        
        # Find points with significant changes
        significant_points = changes[
            (changes['change_magnitude'] >= min_change) |
            (changes['is_crossover'] & (changes['change_magnitude'] >= min_change/2))
        ].copy()
        
        # Find the major trend change point (around the 24-hour mark)
        midpoint_time = df.index[0] + (df.index[-1] - df.index[0]) / 2
        window_start = midpoint_time - timedelta(hours=1)
        window_end = midpoint_time + timedelta(hours=1)
        
        trend_window = changes[
            (changes.index >= window_start) &
            (changes.index <= window_end)
        ]
        
        if not trend_window.empty:
            max_change_idx = trend_window['change_magnitude'].idxmax()
            trend_changes = pd.DataFrame([changes.loc[max_change_idx]])
            return trend_changes
        
        return pd.DataFrame()  # Return empty DataFrame if no changes found
        
    def calculate_momentum(self, news_data: pd.DataFrame, window_size: int = None) -> pd.Series:
        """
        Calculate sentiment momentum over time.
        
        Args:
            news_data (pd.DataFrame): DataFrame containing news with sentiment data
            window_size (int, optional): Size of the momentum window
            
        Returns:
            pd.Series: Momentum values over time
        """
        window_size = window_size or self.config['default_window_size']
        self._validate_input(news_data, ['sentiment', 'published_on'])
        
        # Sort by time
        df = news_data.sort_values('published_on')
        
        # Calculate momentum as rate of change
        momentum = pd.Series(index=df.index)
        
        for i in range(window_size - 1, len(df)):
            window_data = df['sentiment'].iloc[i-window_size+1:i+1]
            momentum.iloc[i] = self._calculate_momentum_value(window_data)
            
        return momentum.dropna()
        
    def _validate_input(self, data: pd.DataFrame, required_columns: List[str]) -> None:
        """Validate input data for trend analysis."""
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Input must be a pandas DataFrame")
            
        # Check for missing columns
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
            
        # Validate sentiment values are numeric
        if 'sentiment' in required_columns:
            sentiment_series = pd.to_numeric(data['sentiment'], errors='coerce')
            if sentiment_series.isna().any():
                raise ValueError("All sentiment values must be numeric")
                
        # Validate published_on column if required
        if 'published_on' in required_columns:
            if not pd.api.types.is_datetime64_any_dtype(data['published_on']):
                try:
                    pd.to_datetime(data['published_on'])
                except (ValueError, TypeError):
                    raise ValueError("published_on must contain valid datetime values")
                    
    def _calculate_slope(self, series: pd.Series) -> float:
        """Calculate the slope of a time series."""
        if len(series) < 2:
            return 0
        x = np.arange(len(series))
        slope, _ = np.polyfit(x, series, 1)
        return slope
        
    def _calculate_strength(self, series: pd.Series) -> float:
        """Calculate the strength of a trend using R-squared value."""
        if len(series) < 2:
            return 0
        x = np.arange(len(series))
        slope, intercept, r_value, _, _ = stats.linregress(x, series)
        return abs(r_value) if not np.isnan(r_value) else 0
        
    def _calculate_momentum_value(self, series: pd.Series) -> float:
        """Calculate momentum value for a series."""
        if len(series) < 2:
            return 0
        return (series.iloc[-1] - series.iloc[0]) / len(series)
