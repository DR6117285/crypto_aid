"""
CryptoCompare API client for fetching market and social sentiment data.
"""
import os
from typing import Dict, List, Optional, Union
import requests
import cryptocompare
from pathlib import Path

class CryptoCompareClient:
    """Client for interacting with the CryptoCompare API."""
    
    BASE_URL = "https://min-api.cryptocompare.com/data"
    
    def __init__(self):
        """Initialize the CryptoCompare client with API key from keys.txt."""
        self.api_key = self._get_api_key()
        if self.api_key:
            cryptocompare.cryptocompare._set_api_key_parameter(self.api_key)
            
    def _get_api_key(self) -> Optional[str]:
        """Get API key from keys.txt file."""
        try:
            keys_path = Path(__file__).parent.parent.parent / 'keys.txt'
            with open(keys_path, 'r') as f:
                for line in f:
                    if line.startswith('API Key='):
                        return line.split('=')[1].strip()
            return None
        except Exception as e:
            print(f"Error reading API key: {str(e)}")
            return None
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a request to the CryptoCompare API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response data as dictionary
        """
        headers = {'authorization': f'Apikey {self.api_key}'} if self.api_key else {}
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API request error: {str(e)}")
            return {}
    
    def get_price(self, symbol: str, currency: str = 'USD') -> Optional[float]:
        """Get current price for a cryptocurrency.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            currency: Currency to get price in (default: 'USD')
            
        Returns:
            Current price or None if not found
        """
        try:
            price_data = cryptocompare.get_price(symbol, currency=currency)
            return price_data.get(symbol, {}).get(currency)
        except Exception as e:
            print(f"Error fetching price for {symbol}: {str(e)}")
            return None

    def get_social_stats(self, symbol: str) -> Dict:
        """Get social media statistics for a cryptocurrency.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            
        Returns:
            Dictionary containing social media statistics
        """
        return self._make_request('social/stats/latest', {'api_key': self.api_key, 'coinId': symbol})

    def get_historical_price(
        self, 
        symbol: str, 
        currency: str = 'USD',
        limit: int = 30,
        exchange: str = 'CCCAGG'
    ) -> List[Dict]:
        """Get historical daily price data.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            currency: Currency to get prices in (default: 'USD')
            limit: Number of days of data to retrieve (default: 30)
            exchange: Exchange to get data from (default: 'CCCAGG')
            
        Returns:
            List of dictionaries containing historical price data
        """
        try:
            return cryptocompare.get_historical_price_day(
                symbol,
                currency=currency,
                limit=limit,
                exchange=exchange
            )
        except Exception as e:
            print(f"Error fetching historical prices for {symbol}: {str(e)}")
            return []

    def calculate_sentiment_score(self, symbol: str) -> float:
        """Calculate a sentiment score based on social media statistics.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            
        Returns:
            Sentiment score between -1 and 1
        """
        try:
            stats = self.get_social_stats(symbol)
            if not stats or 'Data' not in stats:
                return 0.0
                
            data = stats['Data']
            
            # Extract relevant metrics
            reddit = data.get('Reddit', {})
            twitter = data.get('Twitter', {})
            
            # Calculate Reddit sentiment
            reddit_posts = float(reddit.get('posts_per_day', 0))
            reddit_comments = float(reddit.get('comments_per_day', 0))
            reddit_active_users = float(reddit.get('active_users', 0))
            
            # Calculate Twitter sentiment
            twitter_statuses = float(twitter.get('statuses', 0))
            twitter_followers = float(twitter.get('followers', 0))
            
            # Combine metrics into a single score
            total_engagement = (reddit_posts + reddit_comments + 
                              reddit_active_users + twitter_statuses)
            
            if total_engagement == 0:
                return 0.0
                
            # Normalize to [-1, 1] range
            sentiment = (reddit_posts * 0.3 + 
                        reddit_comments * 0.2 + 
                        reddit_active_users * 0.2 + 
                        twitter_statuses * 0.3)
            
            max_expected = total_engagement  # This can be tuned
            normalized = (sentiment / max_expected) * 2 - 1
            
            return max(min(normalized, 1.0), -1.0)
            
        except Exception as e:
            print(f"Error calculating sentiment score for {symbol}: {str(e)}")
            return 0.0

    def get_latest_sentiment(self, symbol: str) -> float:
        """Get the latest sentiment score for a cryptocurrency.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            
        Returns:
            float: Sentiment score between -1 and 1
        """
        endpoint = "social/stats/day"
        params = {'symbol': symbol}
        data = self._make_request(endpoint, params)
        
        if not data or 'Data' not in data:
            return 0.0
            
        # Calculate sentiment score from comments and posts
        comments = data['Data'].get('comments', 0)
        posts = data['Data'].get('posts', 0)
        
        # Get sentiment from comments
        positive_comments = data['Data'].get('commentsTotalPositive', 0)
        negative_comments = data['Data'].get('commentsTotalNegative', 0)
        
        total_interactions = comments + posts
        if total_interactions == 0:
            return 0.0
            
        # Calculate weighted sentiment score
        sentiment_score = (positive_comments - negative_comments) / (positive_comments + negative_comments) if (positive_comments + negative_comments) > 0 else 0
        
        # Normalize to [-1, 1]
        return max(min(sentiment_score, 1.0), -1.0)

    def get_current_price(self, symbol: str) -> float:
        """Get current price for a cryptocurrency in USD.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC')
            
        Returns:
            float: Current price in USD
        """
        try:
            price_data = cryptocompare.get_price(symbol, currency='USD')
            return float(price_data[symbol]['USD'])
        except Exception as e:
            print(f"Error getting price for {symbol}: {str(e)}")
            return 0.0
