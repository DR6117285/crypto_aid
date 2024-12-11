"""
Market data visualization utilities.
"""
import plotly.graph_objects as go
import pandas as pd
from typing import Tuple
import numpy as np

class MarketVisualizer:
    """Utility class for creating market data visualizations."""
    
    @staticmethod
    def plot_candlestick(df: pd.DataFrame, title: str = None) -> go.Figure:
        """
        Create a candlestick chart from OHLCV data.
        
        Args:
            df (pd.DataFrame): DataFrame with OHLCV data
            title (str, optional): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close']
        )])
        
        fig.update_layout(
            title=title,
            yaxis_title='Price',
            xaxis_title='Date',
            template='plotly_dark',
            xaxis_rangeslider_visible=False
        )
        
        return fig
        
    @staticmethod
    def plot_order_book(asks: pd.DataFrame, bids: pd.DataFrame, depth: int = 20, title: str = None) -> go.Figure:
        """
        Create an order book visualization.
        
        Args:
            asks (pd.DataFrame): Ask orders
            bids (pd.DataFrame): Bid orders
            depth (int): Number of orders to show
            title (str, optional): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        # Prepare ask data
        ask_prices = asks.index[:depth]
        ask_volumes = asks['volume'].cumsum()[:depth]
        
        # Prepare bid data
        bid_prices = bids.index[:depth]
        bid_volumes = bids['volume'].cumsum()[:depth]
        
        fig = go.Figure()
        
        # Add asks (sell orders)
        fig.add_trace(go.Scatter(
            x=ask_prices,
            y=ask_volumes,
            name='Asks',
            line=dict(color='red'),
            fill='tonexty'
        ))
        
        # Add bids (buy orders)
        fig.add_trace(go.Scatter(
            x=bid_prices,
            y=bid_volumes,
            name='Bids',
            line=dict(color='green'),
            fill='tonexty'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Price',
            yaxis_title='Cumulative Volume',
            template='plotly_dark',
            showlegend=True
        )
        
        return fig
        
    @staticmethod
    def plot_volume_profile(df: pd.DataFrame, price_levels: int = 50) -> go.Figure:
        """
        Create a volume profile visualization.
        
        Args:
            df (pd.DataFrame): OHLCV data
            price_levels (int): Number of price levels to show
            
        Returns:
            go.Figure: Plotly figure object
        """
        # Calculate price range and create bins
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_bins = np.linspace(price_min, price_max, price_levels)
        
        # Calculate volume for each price level
        volumes = []
        for i in range(len(price_bins)-1):
            mask = (df['low'] >= price_bins[i]) & (df['high'] < price_bins[i+1])
            volume = df.loc[mask, 'volume'].sum()
            volumes.append(volume)
            
        fig = go.Figure(data=[go.Bar(
            x=volumes,
            y=price_bins[:-1],
            orientation='h',
            name='Volume Profile'
        )])
        
        fig.update_layout(
            title='Volume Profile',
            xaxis_title='Volume',
            yaxis_title='Price',
            template='plotly_dark',
            showlegend=False,
            bargap=0
        )
        
        return fig
