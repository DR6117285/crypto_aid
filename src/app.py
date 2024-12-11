"""
Streamlit web application for cryptocurrency market analysis.
"""
import streamlit as st
import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import time
from src.market_data.kraken_client import KrakenClient
from src.portfolio.manager import PortfolioManager
from src.visualization.market_visualizer import MarketVisualizer
from dotenv import load_dotenv

# Initialize session state
if 'initialized' not in st.session_state:
    # Initialize clients
    load_dotenv()
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_SECRET_KEY')
    
    try:
        st.session_state.client = KrakenClient(api_key=api_key, private_key=api_secret)
        st.session_state.balance = None
        st.session_state.portfolio_data = None
        st.session_state.trades_data = None
        st.session_state.trading_pairs = None
        st.session_state.last_portfolio_update = None
        st.session_state.last_trades_update = None
        st.session_state.last_pairs_update = None
        st.session_state.pairs_info = None
        st.session_state.initialized = True
    except Exception as e:
        st.error(f"Error initializing Kraken client: {str(e)}")
        st.session_state.client = None
        st.session_state.initialized = False

def get_tradable_pairs():
    """Get tradable pairs with caching."""
    current_time = time.time()
    if (st.session_state.pairs_info is None or 
        st.session_state.last_pairs_update is None or
        current_time - st.session_state.last_pairs_update > 300):  # Cache for 5 minutes
        try:
            st.session_state.pairs_info = st.session_state.client.k.get_tradable_asset_pairs()
            st.session_state.last_pairs_update = current_time
        except Exception as e:
            st.error(f"Error fetching trading pairs: {str(e)}")
            if st.session_state.pairs_info is None:
                return []
    
    return st.session_state.pairs_info

def display_portfolio_section():
    """Display portfolio information section."""
    st.header("Portfolio Overview")
    
    client = st.session_state.client
    if not client or not client.has_private_access:
        st.warning("Please configure your Kraken API keys with trading permissions to view portfolio data")
        return

    try:
        with st.spinner("Fetching your portfolio data..."):
            # Get account balance using the proper query method
            balance_data = client.query_private('Balance')
            if not balance_data or not balance_data.get('result'):
                st.info("No assets found in your portfolio")
                return
                
            # Convert balance strings to floats
            balance = {k: float(v) for k, v in balance_data['result'].items() if float(v) > 0}
            if not balance:
                st.info("No non-zero balances found in your portfolio")
                return

            # Create a DataFrame for better display
            df = pd.DataFrame(list(balance.items()), columns=['Asset', 'Balance'])
            df = df.sort_values('Balance', ascending=False)
            
            # Display the portfolio data in a nice table
            st.dataframe(
                df,
                column_config={
                    "Asset": st.column_config.TextColumn("Asset", help="Cryptocurrency asset symbol"),
                    "Balance": st.column_config.NumberColumn(
                        "Balance",
                        help="Current balance",
                        format="%.8f"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
    except Exception as e:
        if "query_private" in str(e):
            st.error("Error accessing private data. Please check your API permissions.")
        else:
            st.error(f"Error fetching portfolio data: {str(e)}")

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Crypto Portfolio Manager",
        page_icon="📈",
        layout="wide"
    )

    # Custom CSS for better styling
    st.markdown("""
        <style>
        .stApp {
            background-color: #0e1117;
            color: #ffffff;
        }
        .stButton>button {
            background-color: #1f2937;
            color: white;
            border-radius: 4px;
            border: 1px solid #374151;
        }
        .stSelectbox {
            background-color: #1f2937;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("Crypto Portfolio Manager")

    # Create columns for layout
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("Refresh Data", key="refresh_button"):
            st.session_state.last_portfolio_update = None
            st.session_state.last_trades_update = None
            st.session_state.last_pairs_update = None
            st.experimental_rerun()

    with col1:
        # Trading pair selection with error handling
        try:
            pairs = get_tradable_pairs()
            if isinstance(pairs, pd.DataFrame):
                pair_options = sorted(pairs.index.tolist())
                selected_pair = st.selectbox("Select Trading Pair", pair_options, index=0 if pair_options else None)
            else:
                st.error("Unable to fetch trading pairs. Please try again later.")
                return
        except Exception as e:
            st.error(f"Error loading trading pairs: {str(e)}")
            return

    try:
        # Portfolio Overview Section
        with st.container():
            display_portfolio_section()

        # Market Analysis Section
        with st.container():
            st.header("Market Analysis")
            if selected_pair:
                try:
                    ohlc_data = st.session_state.client.get_ohlc_data(selected_pair)
                    if not ohlc_data.empty:
                        # Create candlestick chart
                        fig = go.Figure(data=[go.Candlestick(
                            x=ohlc_data.index,
                            open=ohlc_data['open'],
                            high=ohlc_data['high'],
                            low=ohlc_data['low'],
                            close=ohlc_data['close']
                        )])
                        
                        fig.update_layout(
                            title=f'{selected_pair} Price Chart',
                            yaxis_title='Price',
                            template='plotly_dark',
                            height=600
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No OHLC data available for {selected_pair}")
                except Exception as e:
                    st.error(f"Error fetching OHLC data: {str(e)}")
            else:
                st.info("Please select a trading pair to view market analysis")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        if st.session_state.client is None:
            st.warning("Please check your API credentials and try again.")

if __name__ == "__main__":
    main()
