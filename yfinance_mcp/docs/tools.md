# Tool Reference

Complete reference for all 15 tools exposed by the yfinance MCP server. Tools are grouped by category matching the server's module structure.

---

## Table of Contents

- [Quote](#quote)
- [Chart](#chart)
- [Search](#search)
- [Fundamentals](#fundamentals)
- [Analyst](#analyst)
- [Options](#options)
- [News](#news)

---

## Quote

These tools return current or near-real-time price and market data. Yahoo Finance data is typically delayed 15 minutes for US equities unless you have a premium account.

---

### get_info

Returns the full data object Yahoo Finance exposes for a ticker. This is the most comprehensive single-call tool — it includes price data, valuation ratios, company profile fields, dividend info, and more in one response.

**Parameters**

| Parameter | Type   | Required | Description                       |
|-----------|--------|----------|-----------------------------------|
| symbol    | string | yes      | Ticker symbol, e.g. `AAPL`        |

**Returns**

A flat dictionary with dozens of fields. Common fields include:

| Field              | Description                                      |
|--------------------|--------------------------------------------------|
| currentPrice       | Last traded price                                |
| previousClose      | Prior session closing price                      |
| open               | Current session open price                       |
| dayLow / dayHigh   | Intraday range                                   |
| fiftyTwoWeekLow / fiftyTwoWeekHigh | 52-week range               |
| volume             | Current session volume                           |
| averageVolume      | 30-day average daily volume                      |
| marketCap          | Total market capitalization                      |
| trailingPE         | Trailing 12-month price-to-earnings ratio        |
| forwardPE          | Forward price-to-earnings ratio                  |
| dividendYield      | Annual dividend yield as a decimal (e.g. 0.005)  |
| beta               | Price volatility relative to the market          |
| sector / industry  | GICS sector and industry classification          |
| longName           | Full company name                                |

**Use cases**

- Pull all available data for a stock in one call when you are not sure exactly which fields you need.
- Get valuation multiples (P/E, P/B, EV/EBITDA) alongside current price.

> **New to ticker symbols?** A ticker symbol is the short code a stock trades under on an exchange. Apple is `AAPL`, Microsoft is `MSFT`, Tesla is `TSLA`. ETFs and indices have their own symbols too — the S&P 500 index is `^GSPC`.

---

### get_fast_info

Returns a small, fast-loading subset of quote data. Use this when you only need current price, volume, and market cap and do not want to wait for the full `get_info` response.

**Parameters**

| Parameter | Type   | Required | Description                |
|-----------|--------|----------|----------------------------|
| symbol    | string | yes      | Ticker symbol, e.g. `MSFT` |

**Returns**

A dictionary with fields including:

| Field              | Description                        |
|--------------------|------------------------------------|
| last_price         | Most recent trade price            |
| open               | Current session open               |
| day_high / day_low | Intraday range                     |
| previous_close     | Prior session close                |
| last_volume        | Most recent bar volume             |
| market_cap         | Total market capitalization        |
| shares             | Total shares outstanding           |
| currency           | Trading currency, e.g. `USD`       |
| exchange           | Exchange code, e.g. `NMS`          |

**Use cases**

- Quick price check before digging deeper.
- Polling multiple symbols efficiently without fetching full info for each.

---

### get_market_summary

Returns a snapshot of major market indices for a given market region.

**Parameters**

| Parameter | Type   | Required | Default     | Description                                           |
|-----------|--------|----------|-------------|-------------------------------------------------------|
| market    | string | no       | `us_market` | Market identifier. See valid values below.            |

**Valid market values**

| Value        | Description               |
|--------------|---------------------------|
| `us_market`  | US equities (default)     |
| `gb_market`  | UK equities               |
| `eu_market`  | European equities         |
| `jp_market`  | Japanese equities         |
| `au_market`  | Australian equities       |

Other regional identifiers may work. The value is passed directly to the yfinance `Market` class.

**Returns**

A dictionary keyed by exchange code. Each entry contains the index name, current value, change, and percentage change.

**Use cases**

- Morning market check: are the major indices up or down before you look at individual stocks?
- Get a feel for broad market direction before placing trades.

---

### get_market_status

Returns whether the specified market is currently open or closed, along with session timing information.

**Parameters**

| Parameter | Type   | Required | Default     | Description              |
|-----------|--------|----------|-------------|--------------------------|
| market    | string | no       | `us_market` | Market identifier        |

**Returns**

A dictionary with all values converted to strings. The exact field names depend on what Yahoo Finance returns for the given market. Fields typically describe whether the market is open or closed, session times, and timezone information.

**Use cases**

- Confirm whether the market is open before acting on a price quote.
- Check international market hours.

---

## Chart

---

### get_history

Returns historical price data (OHLCV) for a symbol over a configurable time range and interval. This is the primary tool for trend analysis and reviewing past price action.

OHLCV stands for Open, High, Low, Close, and Volume — the standard fields in a price bar or candlestick.

**Parameters**

| Parameter | Type    | Required | Default | Description                                                          |
|-----------|---------|----------|---------|----------------------------------------------------------------------|
| symbol    | string  | yes      |         | Ticker symbol                                                        |
| period    | string  | no       | `1mo`   | Lookback window. Ignored if `start` is set. See valid values below.  |
| interval  | string  | no       | `1d`    | Bar size. See valid values below.                                    |
| start     | string  | no       | `null`  | Start date in `YYYY-MM-DD` format. Overrides `period`.               |
| end       | string  | no       | `null`  | End date in `YYYY-MM-DD` format. Only used with `start`.             |
| prepost   | boolean | no       | `false` | Include pre-market and after-hours data.                             |
| actions   | boolean | no       | `true`  | Include dividend and stock split events in the response.             |

**Valid period values**

`1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`

**Valid interval values**

`1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, `3mo`

**Interval constraints (Yahoo Finance limits)**

| Interval | Maximum lookback window |
|----------|------------------------|
| 1m       | 7 days                 |
| 2m–90m   | 60 days                |
| 1h       | 730 days               |
| 1d and above | No hard limit    |

**Returns**

A list of records, one per bar, each containing:

| Field     | Description                                        |
|-----------|----------------------------------------------------|
| Date      | Bar timestamp (string)                             |
| Open      | Opening price                                      |
| High      | Session high                                       |
| Low       | Session low                                        |
| Close     | Closing price                                      |
| Volume    | Shares traded during the bar                       |
| Dividends | Dividend amount if `actions=true` (0 if none)      |
| Stock Splits | Split ratio if `actions=true` (0 if none)       |

**Use cases**

- Review the last month of daily closes to identify a trend.
- Pull hourly data for the past week to study short-term price action.
- Check a specific date range around an earnings announcement.
- Retrieve dividend history for an income stock.

---

## Search

---

### search

Searches Yahoo Finance for symbols, companies, ETFs, indices, crypto, mutual funds, and futures matching a query string. Useful when you know a company name but not its exact ticker, or when exploring what instruments are available.

**Parameters**

| Parameter   | Type    | Required | Default | Description                                              |
|-------------|---------|----------|---------|----------------------------------------------------------|
| query       | string  | yes      |         | Search term — company name, partial symbol, or keyword   |
| max_results | integer | no       | `8`     | Maximum number of matching quotes to return              |
| news_count  | integer | no       | `8`     | Maximum number of news results to return alongside       |

**Returns**

A dictionary with two keys:

- `quotes` — list of matching instruments. Each entry includes fields like `symbol`, `shortname`, `longname`, `exchDisp` (exchange), `typeDisp` (equity, ETF, index, etc.).
- `news` — list of news articles related to the search query. Each entry includes `title`, `link`, `publisher`, and `providerPublishTime`.

**Use cases**

- Find the ticker symbol for a company you know by name.
- Discover ETFs that track a specific theme or index.
- Verify whether a symbol is listed on a particular exchange.

---

## Fundamentals

These tools return financial statement data and company profile information. All financial statement data is sourced from Yahoo Finance, which derives it from SEC filings for US-listed companies.

---

### get_profile

Returns a focused subset of company profile information extracted from the full info object.

**Parameters**

| Parameter | Type   | Required | Description    |
|-----------|--------|----------|----------------|
| symbol    | string | yes      | Ticker symbol  |

**Returns**

A dictionary with fields including:

| Field                | Description                                     |
|----------------------|-------------------------------------------------|
| longName             | Full legal company name                         |
| sector               | GICS sector (e.g. Technology, Healthcare)       |
| industry             | GICS industry (e.g. Consumer Electronics)       |
| longBusinessSummary  | Multi-paragraph description of the business     |
| fullTimeEmployees    | Headcount                                       |
| website              | Company website URL                             |
| country / state / city | Headquarters location                         |
| address1 / zip / phone | Street address, postal code, phone number     |
| shortName            | Short company name                              |
| symbol               | Ticker symbol                                   |
| companyOfficers      | List of key executives with titles and pay data |
| exchange             | Exchange code                                   |

**Use cases**

- Understand what a company actually does before reviewing its financials.
- Check which sector and industry a stock belongs to for portfolio positioning.
- Find the company website for further independent research.

---

### get_financials

Returns the income statement. Covers revenue, gross profit, operating income, net income, and related line items.

**Parameters**

| Parameter | Type   | Required | Default    | Description                      |
|-----------|--------|----------|------------|----------------------------------|
| symbol    | string | yes      |            | Ticker symbol                    |
| freq      | string | no       | `yearly`   | `yearly` or `quarterly`          |

**Returns**

A list of records. Each record corresponds to one period and contains all available income statement line items as key-value pairs. Common fields include `TotalRevenue`, `GrossProfit`, `OperatingIncome`, `NetIncome`, `EBITDA`, `EPS`.

**Use cases**

- Track revenue and profit growth over the past four annual periods.
- Use quarterly data to look for sequential improvement or deterioration.
- Compare gross margin trends across several years.

> **New to income statements?** The income statement shows how much revenue a company brought in and how much of it became profit after subtracting costs. `TotalRevenue` is at the top; `NetIncome` is what remains after all expenses and taxes.

---

### get_balance_sheet

Returns the balance sheet. Covers assets, liabilities, and shareholder equity.

**Parameters**

| Parameter | Type   | Required | Default    | Description             |
|-----------|--------|----------|------------|-------------------------|
| symbol    | string | yes      |            | Ticker symbol           |
| freq      | string | no       | `yearly`   | `yearly` or `quarterly` |

**Returns**

A list of records per reporting period. Common fields include `TotalAssets`, `TotalLiabilitiesNetMinorityInterest`, `StockholdersEquity`, `CashAndCashEquivalents`, `TotalDebt`, `CurrentAssets`, `CurrentLiabilities`.

**Use cases**

- Assess how much debt a company carries relative to its equity.
- Check cash on hand versus near-term liabilities (current ratio).
- Track book value over time.

> **New to balance sheets?** The balance sheet is a snapshot of what a company owns (assets), what it owes (liabilities), and what is left for shareholders (equity). Assets always equal liabilities plus equity.

---

### get_earnings

Returns earnings data including revenue and earnings figures.

**Parameters**

| Parameter | Type   | Required | Default    | Description             |
|-----------|--------|----------|------------|-------------------------|
| symbol    | string | yes      |            | Ticker symbol           |
| freq      | string | no       | `yearly`   | `yearly` or `quarterly` |

**Returns**

A list of records per period with fields such as `Revenue`, `Earnings`, and associated date or period identifiers.

**Use cases**

- See how earnings have grown or declined over recent quarters.
- Check whether a company has been consistently profitable.
- Use in combination with `get_analyst_price_targets` to see if earnings justify the target price.

---

## Analyst

---

### get_analyst_price_targets

Returns the aggregate of analyst price targets for a symbol.

**Parameters**

| Parameter | Type   | Required | Description   |
|-----------|--------|----------|---------------|
| symbol    | string | yes      | Ticker symbol |

**Returns**

A dictionary with fields:

| Field    | Description                                                   |
|----------|---------------------------------------------------------------|
| low      | Lowest price target among covering analysts                   |
| current  | Most recently published consensus or current target           |
| mean     | Mean (average) of all analyst price targets                   |
| median   | Median of all analyst price targets                           |
| high     | Highest price target among covering analysts                  |

**Use cases**

- Quickly gauge where analysts collectively think a stock is headed.
- Compare the current stock price against the mean target to estimate implied upside or downside.
- Use the range (low to high) to understand analyst disagreement.

> **Note:** Analyst price targets are opinions, not guarantees. A wide spread between low and high targets indicates high uncertainty. Always compare targets against your own analysis.

---

### get_recommendations

Returns the historical trend of analyst buy, hold, and sell ratings for a symbol.

**Parameters**

| Parameter | Type   | Required | Description   |
|-----------|--------|----------|---------------|
| symbol    | string | yes      | Ticker symbol |

**Returns**

A list of records, each representing a month. Fields include:

| Field        | Description                                      |
|--------------|--------------------------------------------------|
| period       | Month/year of the snapshot                       |
| strongBuy    | Number of strong buy ratings                     |
| buy          | Number of buy ratings                            |
| hold         | Number of hold ratings                           |
| sell         | Number of sell ratings                           |
| strongSell   | Number of strong sell ratings                    |

**Use cases**

- See whether analyst sentiment has shifted over the past several months.
- Identify when a wave of upgrades or downgrades occurred.
- Combine with `get_analyst_price_targets` for a fuller picture of analyst conviction.

---

## Options

Options are contracts that give the buyer the right (but not the obligation) to buy or sell a stock at a set price before a specific date. The tools below expose options chain data for any optionable symbol.

> **New to options?** A *call* option profits when the stock goes up. A *put* option profits when the stock goes down. The *strike price* is the price at which you can buy or sell. The *expiration date* is when the contract expires. *Open interest* is the number of contracts currently outstanding.

---

### get_options_expirations

Returns the list of available expiration dates for a symbol's options.

**Parameters**

| Parameter | Type   | Required | Description   |
|-----------|--------|----------|---------------|
| symbol    | string | yes      | Ticker symbol |

**Returns**

A list of date strings in `YYYY-MM-DD` format, ordered chronologically. These are the dates you can pass to `get_options_chain`.

**Use cases**

- Check what expiration dates are available before requesting a chain.
- Identify whether weekly or only monthly expirations exist for a symbol.

---

### get_options_chain

Returns the full options chain (all calls and all puts) for a given expiration date.

**Parameters**

| Parameter | Type   | Required | Description                                                              |
|-----------|--------|----------|--------------------------------------------------------------------------|
| symbol    | string | yes      | Ticker symbol                                                            |
| date      | string | no       | Expiration date in `YYYY-MM-DD` format. Omit to use the nearest expiry. |

**Returns**

A dictionary with two keys: `calls` and `puts`. Each is a list of contract records with fields including:

| Field            | Description                                                          |
|------------------|----------------------------------------------------------------------|
| contractSymbol   | Full OCC contract symbol                                             |
| strike           | Strike price                                                         |
| lastPrice        | Last traded price for the contract                                   |
| bid / ask        | Current bid and ask prices                                           |
| change           | Price change since prior close                                       |
| percentChange    | Percentage price change                                              |
| volume           | Number of contracts traded today                                     |
| openInterest     | Total open contracts outstanding                                     |
| impliedVolatility | Market's implied volatility for this contract                       |
| inTheMoney       | `true` if the contract has intrinsic value at the current stock price |
| expiration       | Expiration date                                                      |

**Use cases**

- Scan all strikes at a given expiry to find options with high open interest (a sign of where traders are positioned).
- Compare implied volatility across strikes to identify skew.
- Find the at-the-money option for a specific expiration before placing a trade.

---

## News

---

### get_news

Returns recent news articles related to a ticker symbol.

**Parameters**

| Parameter | Type    | Required | Default | Description                             |
|-----------|---------|----------|---------|-----------------------------------------|
| symbol    | string  | yes      |         | Ticker symbol                           |
| count     | integer | no       | `10`    | Number of articles to return            |

**Returns**

A list of article dictionaries. Common fields include:

| Field                | Description                                    |
|----------------------|------------------------------------------------|
| title                | Article headline                               |
| link                 | URL to the full article                        |
| publisher            | Name of the publishing outlet                  |
| providerPublishTime  | Unix timestamp of publication                  |
| type                 | Content type (e.g. `STORY`, `VIDEO`)           |
| thumbnail            | Thumbnail image data (if available)            |
| relatedTickers       | Other tickers mentioned in the article         |

**Use cases**

- Scan recent headlines before making a trading decision.
- Check whether there is news explaining unusual price or volume movement.
- Monitor ongoing developments for a position you hold.
