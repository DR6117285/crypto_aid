"""
Configuration management module.
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

class Config:
    """
    Manages application configuration and environment variables.
    """
    def __init__(self):
        """Initialize configuration."""
        load_dotenv()  # Load environment variables from .env file
        
    @staticmethod
    def get_api_keys() -> Dict[str, str]:
        """
        Get API keys from environment variables.
        
        Returns:
            Dict[str, str]: Dictionary of API keys
        """
        return {
            'binance_api_key': os.getenv('BINANCE_API_KEY'),
            'binance_secret_key': os.getenv('BINANCE_SECRET_KEY'),
            'kraken_api_key': os.getenv('KRAKEN_API_KEY'),
            'kraken_secret_key': os.getenv('KRAKEN_SECRET_KEY'),
            'kucoin_api_key': os.getenv('KUCOIN_API_KEY'),
            'kucoin_secret_key': os.getenv('KUCOIN_SECRET_KEY')
        }
        
    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        """
        Get a configuration setting.
        
        Args:
            key (str): The configuration key
            default (Any): Default value if key is not found
            
        Returns:
            Any: The configuration value
        """
        return os.getenv(key, default)
