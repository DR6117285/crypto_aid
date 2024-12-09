# CLI Commands Documentation

## Overview
The crypto_aid CLI provides several commands to help you manage your cryptocurrency portfolio, fetch market data, and get trading recommendations.

## Available Commands

### 1. fetch-data
Fetch real-time market data for specified trading pairs.

```bash
crypto_aid fetch-data [PAIRS...] [OPTIONS]
```

**Arguments:**
- `PAIRS`: One or more trading pairs (e.g., XBT/USD, ETH/USD)

**Options:**
- `-o, --output FILE`: Save output to a file

**Example:**
```bash
# Fetch data for Bitcoin and Ethereum
crypto_aid fetch-data XBT/USD ETH/USD

# Save data to a file
crypto_aid fetch-data XBT/USD -o market_data.json
```

### 2. analyze-portfolio
Analyze a portfolio from a CSV file.

```bash
crypto_aid analyze-portfolio PORTFOLIO_FILE [OPTIONS]
```

**Arguments:**
- `PORTFOLIO_FILE`: Path to portfolio CSV file

**Options:**
- `--detailed/--summary`: Show detailed analysis or summary (default: summary)

**CSV Format:**
```csv
asset,amount,entry_price
BTC,1.5,45000
ETH,10,2800
```

**Example:**
```bash
# Basic analysis
crypto_aid analyze-portfolio portfolio.csv

# Detailed analysis
crypto_aid analyze-portfolio portfolio.csv --detailed
```

### 3. recommend-trades
Get trade recommendations based on technical analysis.

```bash
crypto_aid recommend-trades [PAIRS...] [OPTIONS]
```

**Arguments:**
- `PAIRS`: One or more trading pairs to analyze

**Options:**
- `--risk-level [low|medium|high]`: Set risk tolerance (default: medium)

**Example:**
```bash
# Get recommendations for Bitcoin
crypto_aid recommend-trades XBT/USD

# Get recommendations with low risk tolerance
crypto_aid recommend-trades XBT/USD --risk-level low
```

### 4. query
Interactive mode for querying portfolio information.

```bash
crypto_aid query
```

This command starts an interactive session where you can ask questions about your portfolio.

**Example Questions:**
- "What is my BTC allocation?"
- "How much ETH am I holding?"
- Type 'exit' to quit

**Example:**
```bash
$ crypto_aid query
Interactive Query Mode
Enter your question (or 'exit' to quit):
> what is my btc allocation?
You are holding 1.5 BTC
> exit
```

## Common Options
These options are available for all commands:

- `--help`: Show help message for any command
- `--version`: Show version information

## Error Handling
- All commands provide descriptive error messages
- Failed commands exit with non-zero status codes
- API errors and rate limits are handled automatically

## Configuration
The CLI uses the following configuration sources:
1. Environment variables
2. Configuration files
3. Command-line arguments (highest priority)

## Examples of Common Workflows

### 1. Daily Portfolio Check
```bash
# Get current market prices
crypto_aid fetch-data XBT/USD ETH/USD

# Analyze portfolio
crypto_aid analyze-portfolio portfolio.csv --detailed

# Check for trade recommendations
crypto_aid recommend-trades XBT/USD ETH/USD
```

### 2. Quick Portfolio Query
```bash
crypto_aid query
> what is my btc allocation?
> exit
```

### 3. Market Analysis
```bash
# Get market data and save to file
crypto_aid fetch-data XBT/USD ETH/USD -o analysis.json

# Get trade recommendations with low risk
crypto_aid recommend-trades XBT/USD ETH/USD --risk-level low
```
