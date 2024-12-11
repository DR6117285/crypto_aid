# Crypto Aid - Project Architecture

## Core Components

### 1. Market Data Module (`src/market_data/`)
- **Data Acquisition:**
  - Integration with CryptoCompare API for market data
  - Rate-limiting and API key management
  - Historical and real-time price data fetching

### 2. Sentiment Analysis Module (`src/sentiment/`)
- **Components:**
  - `cryptocompare_client.py`: CryptoCompare API client for market and social data
  - `trading_integration.py`: Sentiment-based trading decisions
  - `cli.py`: Command-line interface for sentiment analysis
- **Features:**
  - Social sentiment analysis from CryptoCompare
  - Trading signal generation
  - Position sizing based on sentiment strength
  - Integration with trading system

### 3. Analysis Module (`src/analysis/`)
- **Technical Analysis:**
  - Market trend analysis
  - Technical indicators calculation
  - Signal generation

### 4. Portfolio Module (`src/portfolio/`)
- **Portfolio Management:**
  - Asset allocation
  - Risk management
  - Performance tracking

### 5. CLI Module (`src/cli/`)
- **User Interface:**
  - Command-line tools for market analysis
  - Interactive query mode
  - Data visualization options

### 6. Utils Module (`src/utils/`)
- **Shared Utilities:**
  - Common functions
  - Configuration management
  - Logging and error handling

## System Architecture

### Data Flow
1. **Data Collection:**
   - Market data from CryptoCompare
   - Social sentiment data
   - Historical price data

2. **Processing Pipeline:**
   - Data normalization
   - Sentiment analysis
   - Technical analysis
   - Signal generation

3. **Decision Making:**
   - Trading signals based on sentiment
   - Position sizing recommendations
   - Risk assessment

### Testing Strategy
- **Unit Tests:**
  - Individual component testing
  - Mock external API calls
  - Test data fixtures

- **Integration Tests:**
  - End-to-end workflow testing
  - API integration validation
  - Trading system integration

### Security
- **API Key Management:**
  - Secure key storage in `keys.txt`
  - Environment variable support
  - Rate limiting implementation

### Dependencies
- **Core Libraries:**
  - `cryptocompare`: Market data access
  - `requests`: HTTP client
  - `tabulate`: Data formatting
  - Additional requirements in `requirements.txt`

## Future Enhancements
1. **Enhanced Analysis:**
   - Machine learning models
   - Advanced technical indicators
   - Real-time alerts

2. **Additional Data Sources:**
   - Multiple exchange integration
   - News sentiment analysis
   - On-chain metrics

3. **Portfolio Features:**
   - Automated rebalancing
   - Risk optimization
   - Performance analytics

4. **User Interface:**
   - Web dashboard
   - Mobile app integration
   - Real-time notifications
