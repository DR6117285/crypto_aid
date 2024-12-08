"""
Portfolio management module for tracking cryptocurrency holdings and performance.
"""
from typing import Dict, List
import pandas as pd
from datetime import datetime

class PortfolioManager:
    """
    Manages cryptocurrency portfolio data and calculations.
    """
    def __init__(self, portfolio_file: str = None):
        """
        Initialize the portfolio manager.
        
        Args:
            portfolio_file (str, optional): Path to the CSV file containing portfolio data
        """
        self.portfolio = pd.DataFrame()
        if portfolio_file:
            self.load_portfolio(portfolio_file)
    
    def load_portfolio(self, file_path: str) -> None:
        """
        Load portfolio data from a CSV file.
        
        Args:
            file_path (str): Path to the CSV file
        """
        self.portfolio = pd.read_csv(file_path)
        
    def get_holdings(self) -> pd.DataFrame:
        """
        Get current portfolio holdings.
        
        Returns:
            pd.DataFrame: Portfolio holdings data
        """
        return self.portfolio
    
    def calculate_total_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate total portfolio value using current prices.
        
        Args:
            current_prices (Dict[str, float]): Dictionary of current prices for each asset
            
        Returns:
            float: Total portfolio value
        """
        if self.portfolio.empty:
            return 0.0
            
        total_value = 0.0
        for _, row in self.portfolio.iterrows():
            symbol = row['symbol']
            quantity = row['quantity']
            if symbol in current_prices:
                total_value += quantity * current_prices[symbol]
        
        return total_value
