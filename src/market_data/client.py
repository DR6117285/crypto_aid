"""
Market data client module for fetching cryptocurrency data from various exchanges.
"""
from typing import Dict, List, Optional
import ccxt
from datetime import datetime

class MarketDataClient:
    """
    A client for fetching market data from various cryptocurrency exchanges.
    Supports multiple exchanges through the ccxt library.
    """
    def __init__(self, exchange_id: str = 'binance'):
        """
        Initialize the market data client.
        
        Args:
            exchange_id (str): The ID of the exchange to use (default: 'binance')
        """
        self.exchange = getattr(ccxt, exchange_id)()
        
    def get_ticker(self, symbol: str) -> Dict:
        """
        Get current ticker information for a symbol.
        
        Args:
            symbol (str): The trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dict: Ticker information including price, volume, etc.
        """
        return self.exchange.fetch_ticker(symbol)
    
    def get_ohlcv(self, symbol: str, timeframe: str = '1d', 
                  limit: Optional[int] = None) -> List[List]:
        """
        Get OHLCV (Open, High, Low, Close, Volume) data.
        
        Args:
            symbol (str): The trading pair symbol
            timeframe (str): The timeframe for the data (default: '1d')
            limit (Optional[int]): Number of candles to fetch
            
        Returns:
            List[List]: OHLCV data as a list of [timestamp, open, high, low, close, volume]
        """
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
