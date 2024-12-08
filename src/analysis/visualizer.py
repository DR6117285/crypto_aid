"""
Data visualization utilities for crypto market analysis.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Optional, Tuple, Dict
import numpy as np
from datetime import datetime, timedelta

class MarketVisualizer:
    """
    A utility class for creating interactive visualizations of cryptocurrency market data.
    """
    
    @staticmethod
    def plot_candlestick(ohlc_data: pd.DataFrame, 
                        title: str = "Cryptocurrency Price Chart",
                        volume: bool = True) -> go.Figure:
        """
        Create an interactive candlestick chart with optional volume bars.
        
        Args:
            ohlc_data (pd.DataFrame): OHLCV data with columns [open, high, low, close, volume]
            title (str): Chart title
            volume (bool): Whether to include volume bars
            
        Returns:
            go.Figure: Plotly figure object
        """
        # Create figure with secondary y-axis for volume
        fig = make_subplots(rows=2 if volume else 1, 
                           cols=1,
                           shared_xaxes=True,
                           vertical_spacing=0.03,
                           subplot_titles=(title, 'Volume' if volume else None),
                           row_heights=[0.7, 0.3] if volume else [1])

        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(x=ohlc_data.index,
                          open=ohlc_data['open'],
                          high=ohlc_data['high'],
                          low=ohlc_data['low'],
                          close=ohlc_data['close'],
                          name="OHLC"),
            row=1, col=1
        )
        
        if volume:
            # Add volume bar chart
            colors = ['red' if row['open'] > row['close'] else 'green' 
                     for _, row in ohlc_data.iterrows()]
            fig.add_trace(
                go.Bar(x=ohlc_data.index,
                      y=ohlc_data['volume'],
                      marker_color=colors,
                      name="Volume"),
                row=2, col=1
            )

        # Update layout
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=800 if volume else 600,
            showlegend=False,
            template="plotly_dark"
        )
        
        return fig
    
    @staticmethod
    def plot_order_book(asks: pd.DataFrame,
                       bids: pd.DataFrame,
                       depth: int = 20,
                       title: str = "Order Book Depth") -> go.Figure:
        """
        Create an interactive order book depth chart.
        
        Args:
            asks (pd.DataFrame): Ask orders with columns [price, volume]
            bids (pd.DataFrame): Bid orders with columns [price, volume]
            depth (int): Number of price levels to show
            title (str): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        # Sort and limit to specified depth
        asks = asks.sort_values('price').head(depth)
        bids = bids.sort_values('price', ascending=False).head(depth)
        
        # Calculate cumulative volumes
        asks['cumulative_volume'] = asks['volume'].cumsum()
        bids['cumulative_volume'] = bids['volume'].cumsum()
        
        fig = go.Figure()
        
        # Add ask orders (red)
        fig.add_trace(go.Scatter(
            x=asks['price'],
            y=asks['cumulative_volume'],
            fill='tozeroy',
            name='Asks',
            line=dict(color='red')
        ))
        
        # Add bid orders (green)
        fig.add_trace(go.Scatter(
            x=bids['price'],
            y=bids['cumulative_volume'],
            fill='tozeroy',
            name='Bids',
            line=dict(color='green')
        ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title="Price",
            yaxis_title="Cumulative Volume",
            template="plotly_dark",
            height=600
        )
        
        return fig
    
    @staticmethod
    def plot_price_comparison(prices: Dict[str, pd.Series],
                            title: str = "Price Comparison") -> go.Figure:
        """
        Create an interactive line chart comparing multiple cryptocurrency prices.
        
        Args:
            prices (Dict[str, pd.Series]): Dictionary mapping crypto names to their price series
            title (str): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        fig = go.Figure()
        
        for crypto_name, price_series in prices.items():
            # Normalize prices to percentage change from start
            normalized = (price_series / price_series.iloc[0] - 1) * 100
            
            fig.add_trace(go.Scatter(
                x=price_series.index,
                y=normalized,
                name=crypto_name,
                mode='lines'
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Price Change (%)",
            template="plotly_dark",
            height=600,
            showlegend=True
        )
        
        return fig
