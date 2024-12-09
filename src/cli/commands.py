"""
Command-line interface for crypto_aid.
"""
import click
import pandas as pd
from typing import List, Optional
import json
from datetime import datetime
from ..market_data.kraken_client import KrakenClient
import logging

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """Crypto trading aid command line interface."""
    pass

@cli.command()
@click.argument('pairs', nargs=-1, required=True)
@click.option('--output', '-o', type=click.Path(), help='Output file for the data')
def fetch_data(pairs: List[str], output: Optional[str] = None):
    """
    Fetch market data for specified trading pairs.
    
    Args:
        pairs: List of trading pairs (e.g., XBT/USD)
        output: Optional output file path
    """
    try:
        client = KrakenClient()
        data = client.get_ticker(list(pairs))
        
        # Format output
        formatted_data = json.dumps(data, indent=2, default=str)
        
        if output:
            with open(output, 'w') as f:
                f.write(formatted_data)
            click.echo(f"Data written to {output}")
        else:
            click.echo(formatted_data)
            
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('portfolio_file', type=click.Path(exists=True))
@click.option('--detailed/--summary', default=False, help='Show detailed analysis')
def analyze_portfolio(portfolio_file: str, detailed: bool):
    """
    Analyze portfolio from CSV file.
    
    Args:
        portfolio_file: Path to portfolio CSV file
        detailed: Whether to show detailed analysis
    """
    try:
        # Read portfolio data
        df = pd.read_csv(portfolio_file)
        
        # Calculate basic metrics
        total_value = (df['amount'] * df['entry_price']).sum()
        allocations = df.assign(
            value=df['amount'] * df['entry_price']
        ).assign(
            allocation=lambda x: x['value'] / total_value * 100
        )
        
        # Display results
        click.echo("\nPortfolio Analysis")
        click.echo("=================")
        click.echo(f"Total Value: ${total_value:,.2f}")
        click.echo("\nAllocations:")
        for _, row in allocations.iterrows():
            click.echo(f"{row['asset']}: {row['allocation']:.2f}%")
            
        if detailed:
            click.echo("\nDetailed Analysis")
            click.echo(allocations.to_string())
            
    except Exception as e:
        logger.error(f"Error analyzing portfolio: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('pairs', nargs=-1, required=True)
@click.option('--risk-level', type=click.Choice(['low', 'medium', 'high']), default='medium')
def recommend_trades(pairs: List[str], risk_level: str):
    """
    Get trade recommendations for specified pairs.
    
    Args:
        pairs: Trading pairs to analyze
        risk_level: Risk tolerance level
    """
    try:
        client = KrakenClient()
        data = client.get_ticker(list(pairs))
        
        click.echo("\nTrade Recommendations")
        click.echo("====================")
        
        for pair, info in data.items():
            # Example simple strategy based on RSI
            rsi = float(info.get('rsi', 50))  # Default to neutral if not available
            
            if rsi < 30:
                signal = "BUY"
                reason = "Oversold condition (RSI < 30)"
            elif rsi > 70:
                signal = "SELL"
                reason = "Overbought condition (RSI > 70)"
            else:
                signal = "HOLD"
                reason = "Neutral conditions"
                
            click.echo(f"\n{pair}:")
            click.echo(f"Signal: {signal}")
            click.echo(f"Reason: {reason}")
            click.echo(f"Current Price: {info.get('price', 'N/A')}")
            
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
def query():
    """Interactive query mode for portfolio information."""
    try:
        click.echo("Interactive Query Mode")
        click.echo("Enter your question (or 'exit' to quit):")
        
        while True:
            question = click.prompt('> ').lower()
            
            if question == 'exit':
                break
                
            # Simple keyword-based response system
            if 'allocation' in question or 'holding' in question:
                asset = None
                for coin in ['btc', 'eth', 'xrp']:  # Add more as needed
                    if coin in question:
                        asset = coin.upper()
                        break
                
                if asset:
                    # Read portfolio data (in real implementation, this would be cached)
                    df = pd.read_csv('portfolio.csv')
                    asset_data = df[df['asset'] == asset]
                    
                    if not asset_data.empty:
                        amount = asset_data.iloc[0]['amount']
                        click.echo(f"You are holding {amount} {asset}")
                    else:
                        click.echo(f"No {asset} holdings found in your portfolio")
                else:
                    click.echo("Please specify which asset you're asking about")
            else:
                click.echo("I'm not sure how to answer that question. Try asking about your allocations or holdings.")
                
    except Exception as e:
        logger.error(f"Error in query mode: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli()
