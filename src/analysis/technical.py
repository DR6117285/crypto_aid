"""
Technical analysis module for cryptocurrency trading signals.
"""
from typing import Dict, List
import pandas as pd
import pandas_ta as ta

class TechnicalAnalyzer:
    """
    Performs technical analysis on cryptocurrency price data.
    """
    def __init__(self):
        """Initialize the technical analyzer."""
        pass
        
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            data (pd.DataFrame): Price data with 'close' column
            period (int): RSI period (default: 14)
            
        Returns:
            pd.Series: RSI values
        """
        return ta.rsi(data['close'], length=period)
    
    def calculate_macd(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            data (pd.DataFrame): Price data with 'close' column
            
        Returns:
            Dict[str, pd.Series]: MACD line, signal line, and histogram
        """
        macd = ta.macd(data['close'])
        return {
            'macd': macd['MACD_12_26_9'],
            'signal': macd['MACDs_12_26_9'],
            'hist': macd['MACDh_12_26_9']
        }
    
    def calculate_bollinger_bands(self, data: pd.DataFrame, 
                                period: int = 20) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Args:
            data (pd.DataFrame): Price data with 'close' column
            period (int): Period for calculation (default: 20)
            
        Returns:
            Dict[str, pd.Series]: Upper band, middle band, and lower band
        """
        bbands = ta.bbands(data['close'], length=period)
        return {
            'upper': bbands['BBU_20_2.0'],
            'middle': bbands['BBM_20_2.0'],
            'lower': bbands['BBL_20_2.0']
        }
