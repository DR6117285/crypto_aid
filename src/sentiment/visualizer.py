"""
Visualization utilities for sentiment analysis.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime, timedelta

class SentimentVisualizer:
    @staticmethod
    def plot_sentiment_trend(
        sentiment_data: pd.DataFrame,
        price_data: Optional[pd.DataFrame] = None,
        title: str = "Sentiment Analysis"
    ) -> go.Figure:
        """
        Create an interactive plot showing sentiment trends over time.
        Optionally overlay price data for correlation analysis.
        
        Args:
            sentiment_data (pd.DataFrame): DataFrame with sentiment scores and timestamps
            price_data (pd.DataFrame, optional): DataFrame with price data for comparison
            title (str): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add sentiment line
        fig.add_trace(
            go.Scatter(
                x=sentiment_data.index,
                y=sentiment_data['sentiment'],
                name="Sentiment",
                line=dict(color='blue'),
                hovertemplate="<b>Sentiment:</b> %{y:.2f}<br>" +
                            "<b>Time:</b> %{x}<br><extra></extra>"
            ),
            secondary_y=False
        )
        
        # Add moving average
        ma_period = min(len(sentiment_data), 24)  # 24-hour moving average
        if ma_period >= 2:
            sentiment_ma = sentiment_data['sentiment'].rolling(window=ma_period).mean()
            fig.add_trace(
                go.Scatter(
                    x=sentiment_data.index,
                    y=sentiment_ma,
                    name=f"{ma_period}h MA",
                    line=dict(color='red', dash='dash'),
                    hovertemplate=f"<b>{ma_period}h MA:</b> %{{y:.2f}}<br>" +
                                "<b>Time:</b> %{x}<br><extra></extra>"
                ),
                secondary_y=False
            )
        
        # Add price data if provided
        if price_data is not None:
            fig.add_trace(
                go.Scatter(
                    x=price_data.index,
                    y=price_data['close'],
                    name="Price",
                    line=dict(color='green'),
                    hovertemplate="<b>Price:</b> %{y:,.2f}<br>" +
                                "<b>Time:</b> %{x}<br><extra></extra>"
                ),
                secondary_y=True
            )
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="Sentiment Score",
            yaxis2_title="Price" if price_data is not None else None,
            hovermode='x unified',
            template="plotly_dark",
            height=600,
            showlegend=True
        )
        
        return fig
        
    @staticmethod
    def plot_sentiment_distribution(
        sentiment_data: pd.DataFrame,
        title: str = "Sentiment Distribution"
    ) -> go.Figure:
        """
        Create a histogram showing the distribution of sentiment scores.
        
        Args:
            sentiment_data (pd.DataFrame): DataFrame with sentiment scores
            title (str): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        fig = go.Figure()
        
        # Add histogram
        fig.add_trace(go.Histogram(
            x=sentiment_data['sentiment'],
            nbinsx=20,
            name="Sentiment",
            marker_color='blue',
            hovertemplate="<b>Sentiment Range:</b> %{x}<br>" +
                         "<b>Count:</b> %{y}<br><extra></extra>"
        ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title="Sentiment Score",
            yaxis_title="Frequency",
            template="plotly_dark",
            height=400,
            showlegend=False,
            bargap=0.1
        )
        
        return fig
        
    @staticmethod
    def plot_sentiment_heatmap(sentiment_data: pd.DataFrame, time_window: str = 'h') -> go.Figure:
        """
        Create a heatmap visualization of sentiment data.
        
        Args:
            sentiment_data: DataFrame with sentiment values and datetime index
            time_window: Time window for aggregation ('h' for hourly, 'd' for daily)
            
        Returns:
            Plotly figure object containing the heatmap
        """
        # Convert time_window to lowercase
        time_window = time_window.lower()
        
        # Create hour and date columns
        df = sentiment_data.copy()
        df['hour'] = df.index.hour
        df['date'] = df.index.date
        
        # Create pivot table for heatmap
        pivot_table = df.pivot_table(
            values='sentiment',
            index='hour',
            columns='date',
            aggfunc='mean'
        )
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=pivot_table.columns,
            y=pivot_table.index,
            colorscale='RdBu',
            zmid=0
        ))
        
        # Update layout
        fig.update_layout(
            title='Sentiment Heatmap',
            xaxis_title='Date',
            yaxis_title='Hour of Day',
            height=600
        )
        
        return fig
