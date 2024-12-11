"""
Portfolio management module for tracking cryptocurrency holdings and performance.
"""
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
from src.market_data.kraken_client import KrakenClient
import logging
import time

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    Manages cryptocurrency portfolio data and calculations.
    """
    def __init__(self, kraken_client: KrakenClient):
        """
        Initialize the portfolio manager.
        
        Args:
            kraken_client (KrakenClient): Initialized Kraken client
        """
        self.kraken_client = kraken_client
        
    def _handle_request(self, request_func, *args, **kwargs):
        """
        Handle API requests with rate limiting and error handling.
        
        Args:
            request_func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the request function
        """
        MAX_RETRIES = 3
        RETRY_DELAY = 5  # seconds
        
        for attempt in range(MAX_RETRIES):
            try:
                return request_func(*args, **kwargs)
            except Exception as e:
                if "public call frequency exceeded" in str(e).lower():
                    logger.warning(f"Rate limit hit, waiting {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                    continue
                elif attempt == MAX_RETRIES - 1:
                    raise e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                time.sleep(RETRY_DELAY)
        
        raise Exception(f"Failed after {MAX_RETRIES} attempts")
        
    def _get_trading_pair(self, asset: str) -> str:
        """
        Get the base name for a trading pair from an asset.
        
        Args:
            asset (str): Asset symbol (e.g., XXBT, XETH)
            
        Returns:
            str: Base name for trading pair (e.g., BTC, ETH)
        """
        # Common mappings for Kraken assets
        asset_map = {
            'XXBT': 'XBT',  # Bitcoin
            'XBT': 'XBT',
            'XETH': 'ETH',  # Ethereum
            'ETH': 'ETH',
            'XXDG': 'XDG',  # Dogecoin
            'XXRP': 'XRP',  # Ripple
            'XXMR': 'XMR',  # Monero
            'XLTC': 'LTC',  # Litecoin
            'XXLM': 'XLM',  # Stellar
            'XZEC': 'ZEC',  # Zcash
            'DASH': 'DASH',
            'EOS': 'EOS',
            'GNO': 'GNO',
            'QTUM': 'QTUM',
            'USDT': 'USDT',
            'ZUSD': 'USD',
            'USD': 'USD',
            'USDC': 'USDC',
            'DAI': 'DAI',
            'MATIC': 'MATIC',
            'SOL': 'SOL',
            'LINK': 'LINK',
            'ZGBP': 'GBP'
        }
        
        # First try direct mapping
        if asset in asset_map:
            logger.info(f"Found direct mapping for {asset}: {asset_map[asset]}")
            return asset_map[asset]
            
        # Handle prefixed assets (X or Z)
        if asset.startswith('X') or asset.startswith('Z'):
            base = asset[1:]  # Remove prefix
            if base in asset_map:
                logger.info(f"Found mapping for prefixed asset {asset}: {asset_map[base]}")
                return asset_map[base]
            logger.info(f"Using base name for prefixed asset {asset}: {base}")
            return base
            
        # If no mapping found, return the original asset name
        logger.info(f"No mapping found for {asset}, using as is")
        return asset
        
    def _get_pair_format(self, base: str, quote: str = 'USD') -> List[str]:
        """
        Get possible pair formats for Kraken API.
        
        Args:
            base (str): Base currency (e.g., XBT, ETH)
            quote (str): Quote currency (default: USD)
            
        Returns:
            List[str]: List of possible pair formats
        """
        formats = [
            f"{base}{quote}",       # e.g., BTCUSD
            f"{base}/{quote}",      # e.g., BTC/USD
            f"X{base}Z{quote}",     # e.g., XBTZUSD
            f"{base.upper()}{quote.upper()}",  # e.g., BTCUSD (uppercase)
        ]
        
        # Add special cases for USD pairs
        if quote == 'USD':
            formats.extend([
                f"X{base}ZUSD",     # e.g., XBTZUSD
                f"{base}ZUSD",      # e.g., ETHZUSD
            ])
            
        return formats
        
    def get_portfolio(self) -> pd.DataFrame:
        """
        Get current portfolio holdings from Kraken.
        
        Returns:
            pd.DataFrame: Portfolio holdings with current values
        """
        try:
            # Get account balance with proper error handling
            try:
                balance = self._handle_request(self.kraken_client.get_account_balance)
                logger.info(f"Raw balance data: {balance}")
                
                if balance is None or balance.empty:
                    logger.warning("No balance data received from Kraken")
                    return pd.DataFrame(columns=['Asset', 'Amount', 'Trading Pair', 'Price (USD)', 'Value (USD)', 'Portfolio %'])
                
            except Exception as e:
                logger.error(f"Error getting account balance: {str(e)}")
                return pd.DataFrame(columns=['Asset', 'Amount', 'Trading Pair', 'Price (USD)', 'Value (USD)', 'Portfolio %'])
                
            # Get ticker information for all assets
            non_zero_assets = balance['asset'].tolist()
            logger.info(f"Non-zero assets found: {non_zero_assets}")
            
            if not non_zero_assets:
                logger.info("No non-zero balances found")
                return pd.DataFrame(columns=['Asset', 'Amount', 'Trading Pair', 'Price (USD)', 'Value (USD)', 'Portfolio %'])
                
            # First, try to get all available trading pairs from Kraken
            try:
                asset_pairs = self._handle_request(self.kraken_client.k.get_tradable_asset_pairs)
                available_pairs = set(asset_pairs.index) if asset_pairs is not None else set()
                logger.info(f"Available trading pairs: {available_pairs}")
                
                # Log asset details for debugging
                logger.info(f"Non-zero assets: {non_zero_assets}")
                if asset_pairs is not None:
                    for pair in asset_pairs.index:
                        wsname = asset_pairs.loc[pair, 'wsname']
                        altname = asset_pairs.loc[pair, 'altname']
                        logger.info(f"Pair: {pair}, WebSocket Name: {wsname}, Alt Name: {altname}")
            except Exception as e:
                logger.warning(f"Error fetching tradable pairs: {str(e)}")
                available_pairs = set()
                
            # Create pairs for price lookup
            pairs = []
            asset_to_pair = {}  # Map to keep track of which pair to use for each asset
            
            # Try both USD and USDT pairs for each asset
            for asset in non_zero_assets:
                if asset in ['ZUSD', 'USD', 'USDT']:  # Skip USD/USDT as they're quote currencies
                    continue
                    
                # Get base asset name
                base_asset = self._get_trading_pair(asset)
                logger.info(f"Processing asset {asset} with base name {base_asset}")
                
                # Try different pair combinations
                pair_found = False
                for quote in ['USD', 'USDT']:
                    # Try different formats of the pair
                    pair_formats = self._get_pair_format(base_asset, quote)
                    
                    # Try each format
                    for pair in pair_formats:
                        logger.info(f"Trying pair format for {asset}: {pair}")
                        if pair in available_pairs:
                            pairs.append(pair)
                            asset_to_pair[asset] = pair
                            pair_found = True
                            logger.info(f"Found trading pair for {asset}: {pair}")
                            break
                    
                    if pair_found:
                        break
                        
                if not pair_found:
                    # Try to find any pair containing this asset
                    asset_str = base_asset.upper()
                    for pair in available_pairs:
                        if asset_str in pair:
                            pairs.append(pair)
                            asset_to_pair[asset] = pair
                            pair_found = True
                            logger.info(f"Found alternative trading pair for {asset}: {pair}")
                            break
                            
                if not pair_found:
                    logger.warning(f"No valid trading pair found for asset {asset}")
                    
            if not pairs:
                logger.warning("No valid trading pairs found for any assets")
                return pd.DataFrame(columns=['Asset', 'Amount', 'Trading Pair', 'Price (USD)', 'Value (USD)', 'Portfolio %'])
                
            # Get ticker information for all pairs
            try:
                tickers = self._handle_request(self.kraken_client.k.get_ticker_information, pairs)
                if tickers is None:
                    logger.warning("No ticker data received")
                    return pd.DataFrame(columns=['Asset', 'Amount', 'Trading Pair', 'Price (USD)', 'Value (USD)', 'Portfolio %'])
            except Exception as e:
                logger.error(f"Error fetching ticker information: {str(e)}")
                return pd.DataFrame(columns=['Asset', 'Amount', 'Trading Pair', 'Price (USD)', 'Value (USD)', 'Portfolio %'])
                
            # Create portfolio DataFrame
            portfolio_data = []
            for asset, amount in balance[['asset', 'balance']].values:
                try:
                    if asset in ['ZUSD', 'USD', 'USDT']:
                        price = 1.0
                        value = float(str(amount).replace(',', ''))
                        pair = f"{asset}/USD"
                    elif asset in asset_to_pair:
                        pair = asset_to_pair[asset]
                        try:
                            # Handle potential string or series price data
                            price_data = tickers.loc[pair, 'c']
                            if isinstance(price_data, pd.Series):
                                price = float(price_data.iloc[0])
                            else:
                                price = float(price_data[0])
                            
                            # Clean amount string and convert to float
                            amount_clean = str(amount).replace(',', '')
                            value = float(amount_clean) * price
                            logger.info(f"Calculated value for {asset}: amount={amount_clean}, price={price}, value={value}")
                        except (KeyError, ValueError, IndexError) as e:
                            logger.warning(f"Error calculating value for {asset}: {str(e)}")
                            # Try alternative pair format if available
                            alt_pair = None
                            for p in pairs:
                                if self._get_trading_pair(asset) in p:
                                    alt_pair = p
                                    break
                            
                            if alt_pair and alt_pair in tickers.index:
                                try:
                                    price_data = tickers.loc[alt_pair, 'c']
                                    price = float(price_data[0] if isinstance(price_data, (list, tuple)) else price_data)
                                    amount_clean = str(amount).replace(',', '')
                                    value = float(amount_clean) * price
                                    pair = alt_pair
                                    logger.info(f"Used alternative pair {alt_pair} for {asset}")
                                except (ValueError, IndexError) as e:
                                    logger.warning(f"Error with alternative pair for {asset}: {str(e)}")
                                    price = 0.0
                                    value = 0.0
                            else:
                                price = 0.0
                                value = 0.0
                    else:
                        logger.warning(f"No price information available for {asset}")
                        price = 0.0
                        value = 0.0
                        pair = "N/A"
                        
                    # Clean amount for display
                    try:
                        display_amount = float(str(amount).replace(',', ''))
                    except (ValueError, TypeError):
                        display_amount = 0.0
                            
                    portfolio_data.append({
                        'Asset': self._get_trading_pair(asset),
                        'Amount': display_amount,
                        'Trading Pair': pair,
                        'Price (USD)': price,
                        'Value (USD)': value
                    })
                except Exception as e:
                    logger.error(f"Error processing asset {asset}: {str(e)}")
                    continue
                
            # Create DataFrame with explicit dtypes
            df = pd.DataFrame(portfolio_data)
            if df.empty:
                logger.warning("No portfolio data to display")
                return pd.DataFrame(columns=['Asset', 'Amount', 'Trading Pair', 'Price (USD)', 'Value (USD)', 'Portfolio %'])
            
            # Ensure numeric types and handle NaN values
            numeric_columns = ['Amount', 'Price (USD)', 'Value (USD)']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            # Calculate total portfolio value (excluding zero values)
            total_value = df['Value (USD)'].sum()
            if total_value > 0:
                df['Portfolio %'] = (df['Value (USD)'] / total_value * 100).round(2)
            else:
                df['Portfolio %'] = 0.0
            
            # Sort by value and clean up display
            df = df.sort_values('Value (USD)', ascending=False)
            
            # Format numeric columns
            df['Amount'] = df['Amount'].round(8)
            df['Price (USD)'] = df['Price (USD)'].round(2)
            df['Value (USD)'] = df['Value (USD)'].round(2)
            
            return df
            
        except Exception as e:
            logger.error(f"Error in get_portfolio: {str(e)}")
            return pd.DataFrame(columns=['Asset', 'Amount', 'Trading Pair', 'Price (USD)', 'Value (USD)', 'Portfolio %'])
