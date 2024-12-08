# CryptoAid

A Python-based cryptocurrency portfolio management and analysis tool.

## Project Structure

```
crypto_aid/
├── src/
│   ├── market_data/    # Market data fetching and processing
│   ├── portfolio/      # Portfolio management and tracking
│   ├── analysis/       # Technical analysis and signals
│   └── utils/          # Utility functions and helpers
├── data/               # Data storage (created when needed)
├── logs/               # Application logs (created when needed)
├── main.py            # Application entry point
├── requirements.txt   # Project dependencies
└── .env              # Environment variables (create from .env.example)
```

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

## Usage

Run the main application:
```bash
python main.py
```

## Features

- Market data integration with multiple exchanges
- Portfolio tracking and management
- Technical analysis tools
- Customizable trading signals
- Secure API key management
