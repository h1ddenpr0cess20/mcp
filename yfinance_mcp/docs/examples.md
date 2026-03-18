# Usage Examples

Practical workflows showing how to combine tools for common tasks. Each scenario includes the sequence of tool calls and sample questions you can ask an AI assistant connected to this server.

---

## Table of Contents

- [Quick Stock Check](#quick-stock-check)
- [Research a Stock Before Buying](#research-a-stock-before-buying)
- [Compare Two Stocks](#compare-two-stocks)
- [Check Options Activity](#check-options-activity)
- [Market Overview](#market-overview)
- [Find a Symbol You Do Not Know](#find-a-symbol-you-do-not-know)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Quick Stock Check

**Goal:** Get a fast read on a stock's current price and recent news in two calls.

**Tool sequence:**

1. `get_fast_info` — current price, volume, and market cap
2. `get_news` — recent headlines

**Why this order:** `get_fast_info` is lightweight and confirms the stock is actively trading. News gives you immediate context for any unusual price movement.

**Sample prompt to an AI assistant:**

> Give me a quick snapshot of NVDA — current price and any news from the past few days.

**What to look for:**
- Is the price near its 52-week high or low? (You will need `get_info` for the full range, but `get_fast_info` gives you `previousClose` to gauge same-day movement.)
- Are headlines explaining today's move, or is the price moving without an obvious catalyst?

---

## Research a Stock Before Buying

**Goal:** Build a complete picture of a company before committing capital.

**Tool sequence:**

1. `get_fast_info` — confirm the current price and market cap
2. `get_profile` — understand the business: what it does, what sector, how many employees
3. `get_financials` with `freq="yearly"` — revenue and profit growth over the last four years
4. `get_balance_sheet` with `freq="yearly"` — debt load and cash position
5. `get_earnings` with `freq="quarterly"` — recent quarterly earnings trend
6. `get_analyst_price_targets` — where analysts collectively think it is headed
7. `get_recommendations` — whether analyst sentiment is improving or deteriorating
8. `get_news` — any recent developments that could affect the thesis

**Why this order:** Start with price context, then understand the business before looking at numbers. Financial statements come next because they tell you whether the fundamentals support the valuation. Analyst data is last because it is a market opinion, not a primary source — use it to sense-check your own view.

**Sample prompts to an AI assistant:**

> Walk me through the investment case for AMD. Cover the business, recent financials, and what analysts think.

> Is TSLA's balance sheet improving or deteriorating? Check the last four years and tell me how debt has changed relative to cash.

> What do analysts say about META's price target, and has sentiment shifted over the last six months?

**What to look for:**
- Revenue growing faster than expenses (improving margins)?
- Debt increasing while cash shrinks (potential stress)?
- Analyst consensus moving up (upgrades) or down (downgrades) over recent months?
- News that contradicts or reinforces the financial picture?

---

## Compare Two Stocks

**Goal:** Side-by-side comparison of two stocks in the same sector.

**Tool sequence (run for each symbol):**

1. `get_fast_info` — price, market cap
2. `get_info` — P/E, forward P/E, dividend yield, beta
3. `get_financials` with `freq="yearly"` — revenue and margin comparison
4. `get_analyst_price_targets` — consensus upside/downside for each

**Sample prompts to an AI assistant:**

> Compare JPM and BAC. Which is cheaper on a P/E basis and which has more analyst upside?

> I'm choosing between AMZN and MSFT for a tech allocation. Compare their revenue growth, profit margins, and where analysts have each priced.

> Which has a better balance sheet: KO or PEP? Check cash, debt, and the current ratio for both.

**What to look for:**
- Lower forward P/E suggests cheaper valuation, all else equal.
- Higher revenue growth often justifies a premium valuation.
- Compare beta values: higher beta means more volatile relative to the overall market.
- Analyst mean target versus current price shows implied upside for each.

---

## Check Options Activity

**Goal:** Understand where traders are positioned in the options market for a stock.

**Tool sequence:**

1. `get_fast_info` — current stock price (needed to identify at-the-money strikes)
2. `get_options_expirations` — see which dates are available
3. `get_options_chain` with a chosen expiration — full calls and puts with open interest and volume

**Sample prompts to an AI assistant:**

> What options expirations are available for SPY?

> Pull the options chain for AAPL for the nearest expiration. Which strike has the highest open interest on the call side?

> Is there unusual put activity in TSLA this week? Look at the options chain and tell me if any strikes have high volume relative to open interest.

**What to look for:**
- High open interest at a specific strike suggests traders consider that level significant (potential support or resistance).
- Volume much higher than open interest on a given day indicates fresh positioning — traders are opening new contracts, not rolling existing ones.
- Implied volatility levels: higher IV means the market expects larger price swings.
- A skew where put IV is much higher than call IV suggests the market is pricing in downside risk.

> **New to open interest vs. volume?** Volume counts contracts traded today. Open interest counts all contracts that have been opened and not yet closed or expired. A spike in volume without a corresponding open interest increase means traders are closing existing positions, not opening new ones.

---

## Market Overview

**Goal:** Orient yourself to the overall market before trading the open or reviewing your portfolio.

**Tool sequence:**

1. `get_market_status` — confirm the market is open (or check international markets)
2. `get_market_summary` — see how major indices are trading
3. `get_fast_info` on key ETFs or indices you track — `SPY`, `QQQ`, `IWM`, `DIA`
4. `get_news` on broad tickers like `SPY` or sector ETFs — macro headlines

**Sample prompts to an AI assistant:**

> Is the US market open right now?

> Give me a morning overview — how are the major indices trading and is there any macro news I should know about?

> How is the UK market doing today compared to the US? Check both gb_market and us_market.

> Pull the news for SPY and QQQ. Is there anything macro-driven happening today?

**What to look for:**
- Are indices moving in the same direction (broad trend) or diverging (sector rotation)?
- Is volume on the index ETFs above or below average (conviction behind a move)?
- Are there macro events in the news — Fed statements, economic data releases, geopolitical developments — that explain market direction?

---

## Find a Symbol You Do Not Know

**Goal:** Locate the correct ticker for a company or ETF you want to research.

**Tool sequence:**

1. `search` — find matching symbols by name or keyword
2. `get_profile` on the result — confirm you have the right company before pulling financials

**Sample prompts to an AI assistant:**

> What is the ticker symbol for Palantir Technologies?

> Search for ETFs that track the semiconductor sector.

> I want to look at the S&P 500 index. What symbol should I use?

> Find the ticker for Volkswagen's US-listed shares.

**Tips:**
- For US-listed stocks, `search` usually returns the correct result as the first quote entry.
- For foreign stocks, there may be multiple listings — check the `exchDisp` field to confirm you have the exchange you want.
- ETF names often include words like "iShares", "Vanguard", "SPDR", or "Invesco" — including these in your search narrows results.

---

## Sample Questions for an AI Assistant

The following questions illustrate what you can ask an AI assistant that has this MCP server connected. Each question maps to one or more tool calls the assistant will make on your behalf.

**Price and snapshot**
- What is Apple's stock price right now?
- How much has Microsoft moved today, and is volume above average?
- What is Netflix's market cap?

**Company research**
- What does Moderna do and what sector is it in?
- How has Amazon's revenue grown over the last four years?
- What is Alphabet's debt situation? Is cash growing or shrinking?
- Show me Nike's quarterly earnings for the past year.

**Analyst opinions**
- What is the analyst consensus price target for Salesforce? Is the stock trading above or below it?
- Have analysts been upgrading or downgrading Disney recently?
- Which has more analyst upside: Uber or Lyft?

**Options**
- What expiration dates are available for Tesla options?
- What are the most actively traded call strikes for NVDA this week?
- Is there any unusual put volume in the SPY options chain?

**News**
- What is the latest news on Nvidia?
- Are there any headlines explaining today's move in Boeing?
- What is in the news for the semiconductor sector? Search "semiconductor" and show me recent articles.

**Market overview**
- Is the stock market open right now?
- How are the major US indices trading today?
- What is the S&P 500 doing this morning, and is there any macro news?

**Historical data**
- Show me Apple's daily price history for the last three months.
- What did Tesla's stock do in the week after its last earnings report?
- Pull weekly data for the S&P 500 over the past two years.
- Did Amazon pay any dividends in the last year?
