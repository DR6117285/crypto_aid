"""
Command-line interface for CryptoCompare sentiment analysis.
"""
import argparse
import json
from typing import List, Optional
from tabulate import tabulate
from .cryptocompare_client import CryptoCompareClient

def format_social_stats(stats: dict) -> List[List]:
    """Format social stats for tabular display."""
    if not stats or 'Data' not in stats:
        return [['No data available']]
        
    data = stats['Data']
    rows = []
    
    # Reddit stats
    reddit = data.get('Reddit', {})
    rows.extend([
        ['Reddit Posts (24h)', reddit.get('posts_per_day', 0)],
        ['Reddit Comments (24h)', reddit.get('comments_per_day', 0)],
        ['Reddit Active Users', reddit.get('active_users', 0)],
    ])
    
    # Twitter stats
    twitter = data.get('Twitter', {})
    rows.extend([
        ['Twitter Statuses', twitter.get('statuses', 0)],
        ['Twitter Followers', twitter.get('followers', 0)],
    ])
    
    return rows

def get_sentiment(symbol: str) -> None:
    """Display sentiment analysis for a cryptocurrency."""
    client = CryptoCompareClient()
    
    # Get current price
    price = client.get_price(symbol)
    if price:
        print(f"\nCurrent {symbol} price: ${price:,.2f}")
    
    # Get and display sentiment score
    score = client.calculate_sentiment_score(symbol)
    print(f"\nSentiment Score: {score:,.3f}")
    
    # Interpret sentiment
    if score > 0.5:
        print("Interpretation: Very Positive (Strong Bullish)")
    elif score > 0.2:
        print("Interpretation: Positive (Bullish)")
    elif score > -0.2:
        print("Interpretation: Neutral")
    elif score > -0.5:
        print("Interpretation: Negative (Bearish)")
    else:
        print("Interpretation: Very Negative (Strong Bearish)")
    
    # Get and display social stats
    stats = client.get_social_stats(symbol)
    if stats:
        print("\nSocial Media Statistics:")
        print(tabulate(
            format_social_stats(stats),
            headers=['Metric', 'Value'],
            tablefmt='grid'
        ))

def compare_coins(symbols: List[str]) -> None:
    """Compare sentiment across multiple cryptocurrencies."""
    client = CryptoCompareClient()
    
    # Collect data for each coin
    rows = []
    for symbol in symbols:
        price = client.get_price(symbol)
        score = client.calculate_sentiment_score(symbol)
        
        # Get social stats
        stats = client.get_social_stats(symbol)
        data = stats.get('Data', {})
        reddit = data.get('Reddit', {})
        twitter = data.get('Twitter', {})
        
        # Get sentiment interpretation
        if score > 0.5:
            sentiment = "Very Positive"
        elif score > 0.2:
            sentiment = "Positive"
        elif score > -0.2:
            sentiment = "Neutral"
        elif score > -0.5:
            sentiment = "Negative"
        else:
            sentiment = "Very Negative"
        
        rows.append([
            symbol,
            f"${price:,.2f}" if price else "N/A",
            f"{score:,.3f}",
            sentiment,
            reddit.get('posts_per_day', 0),
            twitter.get('statuses', 0)
        ])
    
    # Display comparison table
    print("\nCryptocurrency Sentiment Comparison:")
    print(tabulate(
        rows,
        headers=['Symbol', 'Price', 'Score', 'Sentiment', 'Reddit Posts (24h)', 'Twitter Posts'],
        tablefmt='grid'
    ))

def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description='Analyze cryptocurrency sentiment using CryptoCompare data'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Sentiment command
    sentiment_parser = subparsers.add_parser(
        'sentiment',
        help='Get sentiment analysis for a cryptocurrency'
    )
    sentiment_parser.add_argument(
        'symbol',
        help='Cryptocurrency symbol (e.g., BTC)'
    )
    
    # Compare command
    compare_parser = subparsers.add_parser(
        'compare',
        help='Compare sentiment across multiple cryptocurrencies'
    )
    compare_parser.add_argument(
        'symbols',
        nargs='+',
        help='List of cryptocurrency symbols to compare'
    )
    
    args = parser.parse_args()
    
    if args.command == 'sentiment':
        get_sentiment(args.symbol.upper())
    elif args.command == 'compare':
        compare_coins([s.upper() for s in args.symbols])
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
