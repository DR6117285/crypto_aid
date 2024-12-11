from src.sentiment.cryptocompare_client import CryptoCompareClient

class SentimentTrader:
    def __init__(self):
        self.client = CryptoCompareClient()
        self.sentiment_thresholds = {
            'strong_positive': 0.7,  # Adjusted from 0.6
            'weak_positive': 0.3,    # Adjusted from 0.2
            'strong_negative': -0.7,  # Adjusted from -0.6
            'weak_negative': -0.3     # Adjusted from -0.2
        }
        self.position_sizes = {
            'strong': 0.2,  # 20% of capital
            'moderate': 0.1,  # 10% of capital
            'weak': 0.05    # 5% of capital
        }

    def generate_trading_signal(self, sentiment_score: float) -> str:
        """
        Generate trading signal based on sentiment score
        
        Args:
            sentiment_score (float): Score between -1 and 1
            
        Returns:
            str: Trading signal (BUY, SELL, or HOLD)
        """
        if sentiment_score >= self.sentiment_thresholds['strong_positive']:
            return "BUY"
        elif sentiment_score <= self.sentiment_thresholds['strong_negative']:
            return "SELL"
        return "HOLD"

    def calculate_position_size(self, available_capital: float, sentiment_score: float) -> float:
        """
        Calculate position size based on sentiment strength and available capital
        
        Args:
            available_capital (float): Available capital for trading
            sentiment_score (float): Sentiment score between -1 and 1
            
        Returns:
            float: Position size in base currency
        """
        abs_sentiment = abs(sentiment_score)
        if abs_sentiment >= self.sentiment_thresholds['strong_positive']:
            return available_capital * self.position_sizes['strong']
        elif abs_sentiment >= self.sentiment_thresholds['weak_positive']:
            return available_capital * self.position_sizes['moderate']
        return available_capital * self.position_sizes['weak']

    def execute_sentiment_based_trade(self, symbol: str, available_capital: float) -> dict:
        """
        Execute a trade based on current sentiment analysis
        
        Args:
            symbol (str): Cryptocurrency symbol (e.g., 'BTC')
            available_capital (float): Available capital for trading
            
        Returns:
            dict: Trade decision including action, position size, and analysis
        """
        sentiment_score = self.client.get_latest_sentiment(symbol)
        current_price = self.client.get_current_price(symbol)
        
        action = self.generate_trading_signal(sentiment_score)
        position_size = self.calculate_position_size(available_capital, sentiment_score)
        
        return {
            "action": action,
            "position_size": position_size,
            "sentiment_score": sentiment_score,
            "current_price": current_price,
            "symbol": symbol
        }
