"""
Kraken-specific market data client implementation.
"""
import krakenex
from pykrakenapi import KrakenAPI
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta
import logging
from time import sleep
from src.utils.rate_limiter import RateLimiter
import websockets
import json
import asyncio
import numpy as np
from websockets.exceptions import ConnectionClosed
import time

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
    Focused on ledger entries, data export functionality, and real-time data via WebSocket.
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
        self.k = KrakenAPI(self.api, tier="Intermediate")  # Adjusted tier for better rate limits
        self.has_private_access = bool(api_key and private_key)
        self.rate_limiter = RateLimiter()
        self._last_request_time = datetime.now()
        self._consecutive_failures = 0
        self._nonce = int(time.time() * 1000)
        
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean a DataFrame by handling infinite values and type conversions.
        
        Args:
            df (pd.DataFrame): DataFrame to clean
        
        Returns:
            pd.DataFrame: Cleaned DataFrame
        """
        if df is None or df.empty:
            return pd.DataFrame()
        
        try:
            # Create a copy to avoid modifying the original
            cleaned_df = df.copy()
            
            # Replace infinite values with NaN and explicitly infer objects
            cleaned_df = cleaned_df.replace([np.inf, -np.inf], np.nan).infer_objects(copy=False)
            
            # Convert numeric columns
            for col in cleaned_df.select_dtypes(include=['float64', 'int64']).columns:
                cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
            
            return cleaned_df
            
        except Exception as e:
            logger.error(f"Error cleaning DataFrame: {str(e)}")
            return df
        
    def _get_nonce(self):
        """Get a unique nonce value."""
        self._nonce = max(int(time.time() * 1000), self._nonce + 1)
        return self._nonce
        
    def _handle_request(self, request_func, *args, **kwargs):
        """
        Handle API requests with proper rate limiting and error handling.
        
        Args:
            request_func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the request function
        """
        MAX_RETRIES = 3
        BASE_DELAY = 5  # Base delay in seconds
        
        for attempt in range(MAX_RETRIES):
            try:
                # Add delay between requests to respect rate limits
                if attempt > 0:
                    time.sleep(BASE_DELAY * (2 ** attempt))  # Exponential backoff
                
                # Execute the request
                result = request_func(*args, **kwargs)
                
                # Add a small delay after successful request to prevent rate limiting
                time.sleep(0.5)
                
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                if "public call frequency exceeded" in error_msg:
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limit hit, waiting {delay} seconds...")
                    time.sleep(delay)
                    continue
                elif attempt == MAX_RETRIES - 1:
                    raise e
                logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
                
        raise Exception(f"Failed after {MAX_RETRIES} attempts")
        
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
                
    async def connect_websocket(self) -> None:
        """
        Establish WebSocket connection to Kraken.
        
        Raises:
            KrakenError: If connection fails
        """
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.is_ws_connected = True
            logger.info("WebSocket connection established")
        except Exception as e:
            self.is_ws_connected = False
            raise KrakenError(f"Failed to establish WebSocket connection: {str(e)}")
            
    async def subscribe_ticker(self, pairs: List[str]) -> None:
        """
        Subscribe to ticker updates for specified pairs.
        
        Args:
            pairs: List of trading pairs (e.g., ["XBT/USD", "ETH/USD"])
            
        Raises:
            KrakenError: If subscription fails
        """
        if not self.is_ws_connected:
            await self.connect_websocket()
            
        # Get tradable pairs info for mapping
        try:
            pairs_info = self._handle_request(self.k.get_tradable_asset_pairs)
            if pairs_info is not None:
                # Create mapping from REST API pair names to WebSocket names
                pair_to_ws = {pair: info['wsname'] for pair, info in pairs_info.iterrows()}
                logger.info(f"WebSocket pair mapping: {pair_to_ws}")
                
                # Map the input pairs to their WebSocket names
                ws_pairs = []
                for pair in pairs:
                    if pair in pair_to_ws:
                        ws_pairs.append(pair_to_ws[pair])
                        logger.info(f"Mapped {pair} to WebSocket name: {pair_to_ws[pair]}")
                    else:
                        logger.warning(f"No WebSocket mapping found for pair: {pair}")
                        ws_pairs.append(pair)  # Use original as fallback
                
                pairs = ws_pairs
                
        except Exception as e:
            logger.warning(f"Error getting WebSocket pair mapping: {str(e)}")
            
        subscription = {
            "event": "subscribe",
            "pair": pairs,
            "subscription": {"name": "ticker"}
        }
        
        try:
            await self.ws.send(json.dumps(subscription))
            logger.info(f"Subscribed to ticker updates for pairs: {pairs}")
        except Exception as e:
            raise KrakenError(f"Failed to subscribe to ticker: {str(e)}")
            
    async def unsubscribe_ticker(self, pairs: List[str]) -> None:
        """
        Unsubscribe from ticker updates for specified pairs.
        
        Args:
            pairs: List of trading pairs to unsubscribe from
            
        Raises:
            KrakenError: If unsubscription fails
        """
        if not self.is_ws_connected:
            return
            
        unsubscribe = {
            "event": "unsubscribe",
            "pair": pairs,
            "subscription": {"name": "ticker"}
        }
        
        try:
            await self.ws.send(json.dumps(unsubscribe))
            logger.info(f"Unsubscribed from ticker updates for pairs: {pairs}")
        except Exception as e:
            raise KrakenError(f"Failed to unsubscribe from ticker: {str(e)}")
            
    async def receive_message(self) -> Dict:
        """
        Receive and process WebSocket messages.
        
        Returns:
            Dict: Processed message data
            
        Raises:
            KrakenError: If message processing fails
            ConnectionClosed: If WebSocket connection is lost
        """
        if not self.is_ws_connected:
            await self.connect_websocket()
            
        try:
            message = await self.ws.recv()
            data = json.loads(message)
            
            # Handle heartbeat messages
            if isinstance(data, dict) and data.get("event") == "heartbeat":
                self.last_heartbeat = datetime.now()
                return data
                
            # Handle error messages
            if isinstance(data, dict) and data.get("event") == "error":
                raise KrakenError(f"WebSocket error: {data.get('errorMessage')}")
                
            return data
            
        except ConnectionClosed as e:
            self.is_ws_connected = False
            raise e
        except Exception as e:
            raise KrakenError(f"Failed to process WebSocket message: {str(e)}")
            
    async def close_websocket(self) -> None:
        """Close the WebSocket connection."""
        if self.ws and self.is_ws_connected:
            await self.ws.close()
            self.is_ws_connected = False
            logger.info("WebSocket connection closed")
            
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

    def get_trades_history(self, start=None, end=None, trade_type="all", offset=0):
        """
        Retrieve trading history from Kraken.
        
        Args:
            start (int, optional): Start timestamp
            end (int, optional): End timestamp
            trade_type (str): Type of trades to retrieve (default: "all")
            offset (int): Result offset for pagination
        
        Returns:
            tuple: (DataFrame of trades, total count)
        """
        try:
            # Prepare request parameters
            params = {
                'type': trade_type,
                'ofs': offset
            }
            if start is not None:
                params['start'] = start
            if end is not None:
                params['end'] = end

            # Query trades history
            trades = self.k.query_private('TradesHistory', data=params)
            
            if trades is None or 'error' in trades and trades['error']:
                logger.warning("No trades found or error occurred")
                return pd.DataFrame(), 0
            
            if 'result' not in trades:
                logger.warning("No result in trades response")
                return pd.DataFrame(), 0
            
            trades_data = trades['result'].get('trades', {})
            count = trades['result'].get('count', 0)
            
            if not trades_data:
                return pd.DataFrame(), count
            
            # Convert trades to DataFrame
            trades_df = pd.DataFrame.from_dict(trades_data, orient='index')
            if not trades_df.empty:
                # Convert timestamp to datetime
                trades_df.index = pd.to_datetime(trades_df.index, unit='s')
                trades_df['time'] = trades_df.index
                
                # Convert numeric columns
                numeric_cols = ['price', 'cost', 'fee', 'vol']
                for col in numeric_cols:
                    if col in trades_df.columns:
                        trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
                        
                # Ensure all required columns exist
                required_cols = ['time', 'pair', 'type', 'price', 'vol', 'cost', 'fee']
                for col in required_cols:
                    if col not in trades_df.columns:
                        trades_df[col] = None
            
            logger.info(f"Retrieved {len(trades_df)} trades")
            return trades_df, count
            
        except Exception as e:
            logger.error(f"Error fetching trade history: {str(e)}")
            return pd.DataFrame(), 0

    def get_ohlc_data(self, pair: str, interval: int = 1, since: Optional[int] = None) -> pd.DataFrame:
        """
        Get OHLC (candlestick) data for a trading pair.
        
        Args:
            pair (str): Trading pair
            interval (int): Time frame interval in minutes
            since (int, optional): Return committed OHLC data since given ID
            
        Returns:
            pd.DataFrame: OHLC data
        """
        try:
            # Get OHLC data using rate-limited request
            with self.rate_limiter:
                ohlc_data, last = self.k.get_ohlc_data(pair, interval=interval, since=since)
                
            # Clean and process the data
            if not ohlc_data.empty:
                ohlc_data = self._clean_dataframe(ohlc_data)
                # Ensure index is properly sorted
                ohlc_data = ohlc_data.sort_index()
                # Set the frequency without using deprecated 'T'
                if len(ohlc_data) > 1:
                    freq = pd.Timedelta(minutes=interval)
                    if ohlc_data.index.is_monotonic_increasing:
                        ohlc_data.index.freq = freq
                
            return ohlc_data
            
        except Exception as e:
            logger.error(f"Error getting OHLC data for {pair}: {str(e)}")
            return pd.DataFrame()

    def query_private(self, method: str, data: Optional[Dict] = None) -> Dict:
        """
        Make a private API query with proper rate limiting.
        
        Args:
            method (str): API method name
            data (Dict, optional): Additional data for the request
            
        Returns:
            Dict: API response
        """
        try:
            with self.rate_limiter:
                response = self.api.query_private(method, data or {})
                if response.get('error'):
                    logger.error(f"Kraken API error: {response['error']}")
                    raise KrakenError(f"API error: {response['error']}")
                return response
        except Exception as e:
            logger.error(f"Error in private query {method}: {str(e)}")
            raise

    def get_account_balance(self) -> pd.DataFrame:
        """
        Get account balance with proper response handling.
        
        Returns:
            pd.DataFrame: Account balance data
        """
        try:
            if not self.has_private_access:
                logger.error("Private API access required for account balance")
                return pd.DataFrame()
                
            # Make the API call
            response = self.api.query_private('Balance')
            
            if not response or 'error' in response and response['error']:
                logger.error(f"Error in balance response: {response.get('error', 'Unknown error')}")
                return pd.DataFrame()
                
            if 'result' not in response:
                logger.error("No result in balance response")
                return pd.DataFrame()
                
            # Convert response to DataFrame
            balance_data = response['result']
            if not balance_data:
                logger.info("No balance data received")
                return pd.DataFrame()
                
            # Create DataFrame with proper columns
            df = pd.DataFrame([(k, float(v)) for k, v in balance_data.items()],
                            columns=['asset', 'balance'])
            
            # Filter out zero balances
            df = df[df['balance'] > 0].reset_index(drop=True)
            
            logger.info(f"Retrieved balance data: {df}")
            return df
            
        except Exception as e:
            logger.error(f"Error retrieving account balance: {str(e)}")
            return pd.DataFrame()

    def _get_kraken_asset_names(self) -> dict:
        """Get the correct Kraken asset names."""
        try:
            response = self.k.get_asset_info()
            asset_names = {}
            for asset, info in response.iterrows():
                asset_names[info.get('altname', '')] = asset
            return asset_names
        except Exception as e:
            logger.error(f"Error getting asset info: {str(e)}")
            return {}

    def get_trading_pair(self, asset):
        """Get the correct trading pair name for an asset."""
        print(f"\n[DEBUG] Getting trading pair for asset: {asset}")
        
        # First, get all available trading pairs
        try:
            # Add retry logic for rate limiting
            max_retries = 3
            retry_delay = 5  # seconds
            
            for attempt in range(max_retries):
                try:
                    pairs = self.k.get_tradable_asset_pairs()
                    break
                except Exception as e:
                    if "public call frequency exceeded" in str(e).lower():
                        if attempt < max_retries - 1:
                            print(f"[DEBUG] Rate limit hit, waiting {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                    raise e
            
            print(f"[DEBUG] Found {len(pairs)} trading pairs")
            matching_pairs = [p for p in pairs.index if asset.upper() in p]
            print(f"[DEBUG] Pairs containing {asset}: {matching_pairs}")
        except Exception as e:
            print(f"[DEBUG] Error getting trading pairs: {e}")
            return None

        # Handle special cases and mappings
        asset_mapping = {
            'MATIC': 'MATIC',
            'SOL': 'SOL',
            'LINK': 'LINK',
            'ETH': 'XETH',
            'BTC': 'XXBT',
            'XBT': 'XXBT',
            'USD': 'ZUSD',
            'GBP': 'ZGBP',
            'EUR': 'ZEUR'
        }

        # Get the normalized asset name
        base_asset = asset_mapping.get(asset, asset)
        print(f"[DEBUG] Normalized asset name: {base_asset}")
        
        # Try different possible pair formats in order of preference
        possible_pairs = [
            f"{base_asset}USD",               # e.g. MATICUSD
            f"X{base_asset}ZUSD",             # e.g. XETHZUSD
            f"{base_asset}USDT",              # e.g. MATICUSDT
            f"{base_asset}EUR",               # e.g. MATICEUR
            f"X{base_asset}ZEUR",             # e.g. XETHZEUR
            f"{base_asset}GBP",               # e.g. MATICGBP
            f"X{base_asset}ZGBP",             # e.g. XETHZGBP
        ]

        print(f"[DEBUG] Trying possible pairs: {possible_pairs}")
        
        # First try exact matches from our possible pairs
        for pair in possible_pairs:
            if pair in pairs.index:
                print(f"[DEBUG] Found exact match: {pair}")
                return pair
                
        # If no exact match, look for any matching pair in the actual available pairs
        usd_pairs = [p for p in matching_pairs if any(quote in p for quote in ['USD', 'USDT', 'ZUSD'])]
        if usd_pairs:
            print(f"[DEBUG] Found USD pair from available pairs: {usd_pairs[0]}")
            return usd_pairs[0]
            
        # Try EUR pairs as fallback
        eur_pairs = [p for p in matching_pairs if any(quote in p for quote in ['EUR', 'ZEUR'])]
        if eur_pairs:
            print(f"[DEBUG] Found EUR pair from available pairs: {eur_pairs[0]}")
            return eur_pairs[0]

        print(f"[DEBUG] No valid trading pair found for {asset}")
        return None
