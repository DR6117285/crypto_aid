# CLI Commands Documentation

## Overview
The crypto_aid CLI provides several commands to help you analyze cryptocurrency market data and get trading recommendations.

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

### 2. analyze
Run technical analysis on specified trading pairs.

```bash
crypto_aid analyze [PAIRS...] [OPTIONS]
```

**Arguments:**
- `PAIRS`: One or more trading pairs to analyze

**Options:**
- `--indicators [rsi,macd,bb]`: Specify which indicators to use (default: all)
- `--timeframe [1h,4h,1d]`: Analysis timeframe (default: 1d)

**Example:**
```bash
# Analyze Bitcoin with all indicators
crypto_aid analyze XBT/USD

# Analyze Ethereum with specific indicators
crypto_aid analyze ETH/USD --indicators rsi,macd
```

### 3. recommend
Get trade recommendations based on technical analysis.

```bash
crypto_aid recommend [PAIRS...] [OPTIONS]
```

**Arguments:**
- `PAIRS`: One or more trading pairs to analyze

**Options:**
- `--risk-level [low|medium|high]`: Set risk tolerance (default: medium)
- `--min-confidence [0-100]`: Minimum confidence score for recommendations (default: 70)

**Example:**
```bash
# Get recommendations for Bitcoin
crypto_aid recommend XBT/USD

# Get low-risk recommendations
crypto_aid recommend XBT/USD --risk-level low
```

### 4. query
Interactive mode for querying market information.

```bash
crypto_aid query
```

This command starts an interactive session where you can ask questions about market data and analysis.

**Example Questions:**
- "What's the current price of BTC?"
- "Show me the RSI for ETH"
- Type 'exit' to quit

**Example:**
```bash
$ crypto_aid query
Interactive Query Mode
Enter your question (or 'exit' to quit):
> what's the current btc price?
BTC/USD: $45,000
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

## Examples of Common Workflows

### 1. Market Analysis
```bash
# Get current market data
crypto_aid fetch-data XBT/USD ETH/USD

# Run technical analysis
crypto_aid analyze XBT/USD ETH/USD

# Get trade recommendations
crypto_aid recommend XBT/USD ETH/USD --risk-level low
```

### 2. Quick Market Check
```bash
crypto_aid query
> what's the current btc price?
> show me the rsi
> exit
