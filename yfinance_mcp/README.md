# Yahoo Finance MCP Server (FastMCP)

FastMCP server exposing Yahoo Finance data as MCP tools via the [yfinance](https://github.com/ranaroussi/yfinance) library. No API key required.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r yfinance_mcp/requirements.txt
python yfinance_mcp/server.py
```

## Tools

### Quote
- **get_info** — Comprehensive info (price, fundamentals, profile, etc.)
- **get_fast_info** — Fast-loading price/volume/market cap snapshot
- **get_market_summary** — Major market indices overview
- **get_market_status** — Current market open/close status

### Chart / History
- **get_history** — Historical OHLCV data with configurable periods and intervals (includes dividends and splits)

### Search
- **search** — Search for symbols, companies, ETFs, indices, crypto, etc.

### Fundamentals
- **get_profile** — Company profile (sector, industry, description, officers)
- **get_financials** — Income statement (yearly/quarterly)
- **get_balance_sheet** — Balance sheet (yearly/quarterly)
- **get_earnings** — Earnings data (yearly/quarterly)

### Analyst
- **get_analyst_price_targets** — Low, current, mean, median, high targets
- **get_recommendations** — Buy, hold, sell recommendation trends

### Options
- **get_options_expirations** — Available options expiration dates
- **get_options_chain** — Calls and puts for an expiration date

### News
- **get_news** — Recent news articles

## Code Structure

- `yfinance_client/base.py`: Shared helpers (Ticker creation, DataFrame conversion)
- `yfinance_client/__init__.py`: Unified client aggregating all APIs
- `yfinance_client/[quote|chart|search|summary|options|news].py`: Individual API implementations
- `server.py`: FastMCP server with tool registrations

## Notes

- No API key needed — yfinance handles Yahoo Finance authentication automatically.
- All DataFrames are converted to JSON-serializable dicts/lists for MCP transport.
- See `yfinance_client/` for the modular API implementations.
- See `server.py` for FastMCP tool registrations.
