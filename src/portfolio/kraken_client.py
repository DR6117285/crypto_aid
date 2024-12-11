"""
Kraken API client for fetching portfolio and trading data.
"""
import hmac
import base64
import hashlib
import urllib.parse
import time
import requests
from typing import Dict, Optional

class KrakenClient:
    """Client for interacting with the Kraken cryptocurrency exchange API."""
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the Kraken client.
        
        Args:
            api_key (str): Your Kraken API key
            api_secret (str): Your Kraken API secret
        """
        self.api_url = "https://api.kraken.com"
        self.api_key = api_key
        self.api_secret = api_secret

    def _get_kraken_signature(self, urlpath: str, data: Dict) -> str:
        """Generate Kraken API signature."""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(self.api_secret),
                      message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def _make_request(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make an authenticated request to Kraken API."""
        if data is None:
            data = {}
            
        data['nonce'] = str(int(time.time() * 1000))
        
        headers = {
            'API-Key': self.api_key,
            'API-Sign': self._get_kraken_signature(f'/0/private/{endpoint}', data)
        }
        
        response = requests.post(
            f'{self.api_url}/0/private/{endpoint}',
            headers=headers,
            data=data
        )
        
        if response.status_code != 200:
            raise Exception(f'Kraken API request failed: {response.text}')
            
        result = response.json()
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})

    def get_account_balance(self) -> Dict:
        """
        Get account balances for all assets.
        
        Returns:
            Dict: Asset balances in the format {asset: amount}
        """
        return self._make_request('Balance')

    def get_trade_history(self) -> Dict:
        """
        Get trading history.
        
        Returns:
            Dict: Trading history data
        """
        return self._make_request('TradesHistory')

    def get_open_positions(self) -> Dict:
        """
        Get open positions.
        
        Returns:
            Dict: Currently open positions
        """
        return self._make_request('OpenPositions')
