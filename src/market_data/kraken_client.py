"""
Kraken-specific market data client implementation.
"""
import krakenex
from pykrakenapi import KrakenAPI
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime
import logging
from time import sleep
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class KrakenError(Exception):
    """Base exception for Kraken client errors."""
    pass

class KrakenConfigError(KrakenError):
    """Exception for configuration-related errors."""
    pass

class KrakenClient:
    """
    A client for interacting with the Kraken cryptocurrency exchange.
    Uses REST API for market data and trading operations.
    """
    def __init__(self, api_key: str = None, private_key: str = None):
        """
        Initialize the Kraken client.
        
        Args:
            api_key (str, optional): Kraken API key
            private_key (str, optional): Kraken private key
            
        Raises:
            KrakenConfigError: If API keys are invalid or missing when required
        """
        self._validate_api_keys(api_key, private_key)
        self.api = krakenex.API(key=api_key, secret=private_key)
        self.k = KrakenAPI(self.api)
        self.has_private_access = bool(api_key and private_key)
        self.rate_limiter = RateLimiter()
        self._last_request_time = datetime.now()
        self._consecutive_failures = 0
        self._health_status = True
        
    @property
    def is_healthy(self) -> bool:
        """Check if the client is in a healthy state."""
        return self._health_status and self._consecutive_failures < 3
        
    def _validate_api_keys(self, api_key: Optional[str], private_key: Optional[str]) -> None:
        """
        Validate API keys format and presence.
        
        Args:
            api_key (str, optional): Kraken API key
            private_key (str, optional): Kraken private key
            
        Raises:
            KrakenConfigError: If keys are invalid or missing when both are required
        """
        # Both keys must be provided together
        if bool(api_key) != bool(private_key):
            raise KrakenConfigError("Both API key and private key must be provided together")
            
        if api_key:
            if not isinstance(api_key, str) or len(api_key) < 10:
                raise KrakenConfigError("Invalid API key format")
        if private_key:
            if not isinstance(private_key, str) or len(private_key) < 10:
                raise KrakenConfigError("Invalid private key format")
                
    def _handle_request(self, request_func, *args, is_private: bool = False, **kwargs):
        """
        Handle API requests with rate limiting and error handling.
        
        Args:
            request_func: Function to execute
            *args: Positional arguments for the function
            is_private: Whether this is a private API endpoint
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the request function
            
        Raises:
            KrakenError: If the API request fails
        """
        if not self.is_healthy:
            logger.error("Client is in an unhealthy state. Waiting for recovery...")
            sleep(60)  # Wait for 1 minute before retrying
            
        MAX_RETRIES = 3
        RETRY_DELAY = 1  # seconds
        
        # Apply rate limiting
        wait_time = self.rate_limiter.acquire(private=is_private)
        if wait_time > 0:
            logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
            sleep(wait_time)
        
        for attempt in range(MAX_RETRIES):
            try:
                result = request_func(*args, **kwargs)
                self._consecutive_failures = 0
                self._health_status = True
                self._last_request_time = datetime.now()
                return result
            except Exception as e:
                self._consecutive_failures += 1
                if self._consecutive_failures >= 3:
                    self._health_status = False
                    
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"Failed after {MAX_RETRIES} attempts: {str(e)}")
                    raise KrakenError(f"API request failed: {str(e)}")
                    
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                sleep(RETRY_DELAY * (attempt + 1))
    
    def get_asset_pairs(self) -> pd.DataFrame:
        """
        Get information about asset pairs.
        
        Returns:
            pd.DataFrame: Asset pair information
            
        Raises:
            KrakenError: If the API request fails
        """
        return self._handle_request(self.k.get_tradable_asset_pairs)
    
    def get_ticker(self, pair: str) -> pd.DataFrame:
        """
        Get ticker information for a trading pair.
        
        Args:
            pair (str): Trading pair (e.g., 'XXBTZUSD' for BTC/USD)
            
        Returns:
            pd.DataFrame: Ticker information including current price
            
        Raises:
            KrakenError: If the API request fails
        """
        return self._handle_request(self.k.get_ticker_information, pair)
    
    def get_ohlc(self, pair: str, interval: int = 1440,
                 since: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get OHLC (Open, High, Low, Close) data.
        
        Args:
            pair (str): Trading pair
            interval (int): Time frame interval in minutes (default: 1440 for 1 day)
            since (datetime, optional): Start time for historical data
            
        Returns:
            pd.DataFrame: OHLC data with proper datetime index
            
        Raises:
            KrakenError: If the API request fails
        """
        return self._handle_request(self.k.get_ohlc_data, pair, interval=interval, since=since)
    
    def get_order_book(self, pair: str, count: int = 100) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Get order book data.
        
        Args:
            pair (str): Trading pair
            count (int): Number of orders to retrieve
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: Tuple containing (asks, bids) DataFrames with columns [price, volume, timestamp]
            
        Raises:
            KrakenError: If the API request fails
        """
        return self._handle_request(self.k.get_order_book, pair, count=count)
    
    def get_account_balance(self) -> pd.DataFrame:
        """
        Get account balance information.
        Requires API key with appropriate permissions.
        
        Returns:
            pd.DataFrame: Account balance information
            
        Raises:
            KrakenConfigError: If API keys are not configured
            KrakenError: If the API request fails
        """
        if not self.has_private_access:
            raise KrakenConfigError("API keys required for account balance")
        return self._handle_request(self.k.get_account_balance, is_private=True)
    
    @staticmethod
    def format_pair(base: str, quote: str) -> str:
        """
        Format trading pair string according to Kraken's convention.
        
        Args:
            base (str): Base currency (e.g., 'BTC')
            quote (str): Quote currency (e.g., 'USD')
            
        Returns:
            str: Formatted pair string (e.g., 'XXBTZUSD')
        """
        # Common mappings for Kraken's asset codes
        asset_map = {
            'BTC': 'XBT',
            'DOGE': 'XDG'
        }
        
        base = asset_map.get(base, base)
        if base in ['BTC', 'XBT', 'ETH', 'LTC', 'XRP']:
            base = f'X{base}'
        if quote in ['USD', 'EUR', 'GBP', 'JPY']:
            quote = f'Z{quote}'
            
        return f'{base}{quote}'
