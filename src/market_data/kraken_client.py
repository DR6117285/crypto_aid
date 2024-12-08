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
    Focused on ledger entries and data export functionality.
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
        
    @property
    def is_healthy(self) -> bool:
        """Check if the client is in a healthy state."""
        return self._consecutive_failures < 3
        
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
        
        try:
            for attempt in range(MAX_RETRIES):
                try:
                    result = request_func(*args, **kwargs)
                    self._consecutive_failures = 0
                    self._last_request_time = datetime.now()
                    return result
                except Exception as e:
                    if attempt == MAX_RETRIES - 1:
                        raise e
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            self._consecutive_failures += 1
            logger.error(f"Failed after {MAX_RETRIES} attempts: {str(e)}")
            raise KrakenError(f"API request failed: {str(e)}")
        
    def get_ledger_entries(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, 
                          asset: Optional[str] = None, type: Optional[str] = None) -> pd.DataFrame:
        """
        Get ledger entries within the specified time range.
        
        Args:
            start_time (datetime, optional): Start time for ledger entries
            end_time (datetime, optional): End time for ledger entries
            asset (str, optional): Filter by asset (e.g., 'XBT' for Bitcoin)
            type (str, optional): Filter by type (e.g., 'trade', 'deposit', 'withdrawal')
            
        Returns:
            pd.DataFrame: Ledger entries with columns [refid, time, type, asset, amount, fee, balance]
            
        Raises:
            KrakenConfigError: If API keys are not configured
            KrakenError: If the API request fails
        """
        if not self.has_private_access:
            raise KrakenConfigError("API keys required for ledger entries")
            
        params = {}
        if start_time:
            params['start'] = int(start_time.timestamp())
        if end_time:
            params['end'] = int(end_time.timestamp())
        if asset:
            params['asset'] = asset
        if type:
            params['type'] = type
            
        return self._handle_request(self.k.get_ledgers_info, params, is_private=True)
        
    def export_ledger_data(self, report_type: str, description: str, 
                          start_time: datetime, end_time: datetime, 
                          format: str = 'CSV') -> str:
        """
        Request an export of ledger data.
        
        Args:
            report_type (str): Type of report ('ledgers')
            description (str): Description of the export
            start_time (datetime): Start time for the export
            end_time (datetime): End time for the export
            format (str): Export format ('CSV' or 'PDF')
            
        Returns:
            str: Report ID that can be used to check the export status
            
        Raises:
            KrakenConfigError: If API keys are not configured
            KrakenError: If the API request fails
        """
        if not self.has_private_access:
            raise KrakenConfigError("API keys required for data export")
            
        params = {
            'report': report_type,
            'description': description,
            'format': format,
            'starttm': int(start_time.timestamp()),
            'endtm': int(end_time.timestamp())
        }
            
        return self._handle_request(self.k.add_export, params, is_private=True)
        
    def get_export_status(self, report_id: str) -> Dict:
        """
        Check the status of a requested export.
        
        Args:
            report_id (str): ID of the export request
            
        Returns:
            Dict: Status information including completion status and download URL if ready
            
        Raises:
            KrakenConfigError: If API keys are not configured
            KrakenError: If the API request fails
        """
        if not self.has_private_access:
            raise KrakenConfigError("API keys required for export status")
            
        return self._handle_request(self.k.get_export_status, {'report': report_id}, is_private=True)
