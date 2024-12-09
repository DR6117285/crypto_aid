"""
Command-line interface for crypto_aid.
"""
import click
import json
from typing import List, Optional

from ..market_data.kraken_client import KrakenClient
from ..analysis.technical import TechnicalAnalysis
from ..analysis.recommendation import TradeRecommender

@click.group()
def cli():
    """Crypto trading aid CLI"""
    pass

@cli.command()
@click.argument('pairs', nargs=-1, required=True)
@click.option('-o', '--output', type=click.Path(), help='Save output to file')
def fetch_data(pairs: List[str], output: Optional[str]):
    """Fetch market data for specified trading pairs"""
    client = KrakenClient()
    data = client.get_ticker_info(list(pairs))
    
    if output:
        with open(output, 'w') as f:
            json.dump(data, f, indent=2)
        click.echo(f"Data saved to {output}")
    else:
        click.echo(json.dumps(data, indent=2))

@cli.command()
@click.argument('pairs', nargs=-1, required=True)
@click.option('--indicators', default='all', help='Comma-separated list of indicators')
@click.option('--timeframe', default='1d', help='Analysis timeframe')
def analyze(pairs: List[str], indicators: str, timeframe: str):
    """Run technical analysis on specified pairs"""
    client = KrakenClient()
    analyzer = TechnicalAnalysis(client)
    
    indicator_list = indicators.split(',') if indicators != 'all' else None
    results = analyzer.analyze(pairs, timeframe, indicators=indicator_list)
    click.echo(json.dumps(results, indent=2))

@cli.command()
@click.argument('pairs', nargs=-1, required=True)
@click.option('--risk-level', default='medium', type=click.Choice(['low', 'medium', 'high']))
@click.option('--min-confidence', default=70, type=int)
def recommend(pairs: List[str], risk_level: str, min_confidence: int):
    """Get trade recommendations based on analysis"""
    client = KrakenClient()
    analyzer = TechnicalAnalysis(client)
    recommender = TradeRecommender(analyzer)
    
    recommendations = recommender.get_recommendations(
        pairs, 
        risk_level=risk_level,
        min_confidence=min_confidence
    )
    click.echo(json.dumps(recommendations, indent=2))

@cli.command()
def query():
    """Interactive mode for market queries"""
    client = KrakenClient()
    analyzer = TechnicalAnalysis(client)
    
    click.echo("Interactive Query Mode")
    click.echo("Enter your question (or 'exit' to quit):")
    
    while True:
        question = click.prompt('> ')
        if question.lower() == 'exit':
            break
            
        try:
            # Simple question handling - can be expanded
            if 'price' in question.lower():
                pair = next((p for p in ['BTC/USD', 'ETH/USD'] if p.split('/')[0].lower() in question.lower()), 'BTC/USD')
                price = client.get_ticker_info([pair])[pair]['last']
                click.echo(f"{pair}: ${price:,.2f}")
            elif 'rsi' in question.lower():
                pair = next((p for p in ['BTC/USD', 'ETH/USD'] if p.split('/')[0].lower() in question.lower()), 'BTC/USD')
                rsi = analyzer.get_rsi(pair)
                click.echo(f"{pair} RSI: {rsi:.2f}")
            else:
                click.echo("I don't understand that question. Try asking about prices or RSI values.")
        except Exception as e:
            click.echo(f"Error processing request: {str(e)}")

if __name__ == '__main__':
    cli()
