"""
Main entry point for the CryptoAid application.
"""
import os
from src.market_data.client import MarketDataClient
from src.portfolio.manager import PortfolioManager
from src.analysis.technical import TechnicalAnalyzer
from src.utils.config import Config
from src.utils.logger import setup_logger

def main():
    # Set up logging
    logger = setup_logger('crypto_aid', 'logs/crypto_aid.log')
    logger.info('Starting CryptoAid application')
    
    try:
        # Initialize configuration
        config = Config()
        
        # Initialize market data client
        market_client = MarketDataClient()
        
        # Initialize portfolio manager
        portfolio_manager = PortfolioManager()
        
        # Initialize technical analyzer
        technical_analyzer = TechnicalAnalyzer()
        
        # Your application logic here
        logger.info('CryptoAid initialized successfully')
        
    except Exception as e:
        logger.error(f'Error initializing CryptoAid: {str(e)}')
        raise

if __name__ == '__main__':
    main()
