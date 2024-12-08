"""
Streamlit web application for cryptocurrency market analysis.
"""
import streamlit as st
from market_data.kraken_client import KrakenClient
from analysis.visualizer import MarketVisualizer
from utils.config import Config
from datetime import datetime, timedelta
import pandas as pd

def main():
    st.set_page_config(
        page_title="Crypto Aid - Market Analysis",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("Crypto Aid - Market Analysis")
    
    # Initialize clients
    config = Config()
    keys = config.get_api_keys()
    client = KrakenClient(
        api_key=keys.get('kraken_api_key'),
        private_key=keys.get('kraken_secret_key')
    )
    
    # Sidebar for controls
    st.sidebar.header("Controls")
    
    # Get available pairs
    pairs_df = client.get_asset_pairs()
    selected_pair = st.sidebar.selectbox(
        "Select Trading Pair",
        options=pairs_df.index,
        index=pairs_df.index.get_loc('XXBTZUSD') if 'XXBTZUSD' in pairs_df.index else 0
    )
    
    # Time period selection
    timeframe = st.sidebar.selectbox(
        "Select Timeframe",
        options=['1 Day', '1 Week', '1 Month', '3 Months'],
        index=1
    )
    
    timeframe_days = {
        '1 Day': 1,
        '1 Week': 7,
        '1 Month': 30,
        '3 Months': 90
    }
    
    # Fetch OHLCV data
    since = datetime.now() - timedelta(days=timeframe_days[timeframe])
    ohlc_data = client.get_ohlc(selected_pair, interval=1440, since=since)
    
    # Create candlestick chart
    st.subheader(f"{selected_pair} Price Chart")
    fig_candlestick = MarketVisualizer.plot_candlestick(
        ohlc_data,
        title=f"{selected_pair} - {timeframe} Chart"
    )
    st.plotly_chart(fig_candlestick, use_container_width=True)
    
    # Order book visualization
    st.subheader("Order Book Depth")
    depth = st.sidebar.slider("Order Book Depth", min_value=10, max_value=100, value=20)
    asks, bids = client.get_order_book(selected_pair, count=depth)
    
    fig_orderbook = MarketVisualizer.plot_order_book(
        asks, bids, depth=depth,
        title=f"{selected_pair} Order Book"
    )
    st.plotly_chart(fig_orderbook, use_container_width=True)
    
    # Price comparison
    st.subheader("Price Comparison")
    comparison_pairs = st.sidebar.multiselect(
        "Compare with",
        options=pairs_df.index,
        default=[p for p in ['XXBTZUSD', 'XETHZUSD'] if p in pairs_df.index]
    )
    
    if comparison_pairs:
        prices = {}
        for pair in comparison_pairs:
            pair_data = client.get_ohlc(pair, interval=1440, since=since)
            prices[pair] = pair_data['close']
        
        fig_comparison = MarketVisualizer.plot_price_comparison(
            prices,
            title="Price Comparison (% Change)"
        )
        st.plotly_chart(fig_comparison, use_container_width=True)

if __name__ == "__main__":
    main()
