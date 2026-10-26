# TMR10 AI INVEST: Value Growth integration contract

Status: GitHub-side handoff only. NOT deployed to the published ChatGPT Site.

## Safe integration into main app

Add a new optional tab labelled `割安成長株`. Do not replace any existing tabs, local storage keys, server tables, histories, orders, scoring rules, watchlist or ETF entries. Feature flag default off until production smoke test. A separate UI component and new namespaced storage (`tmr10.valueGrowth.v1`) prevents collision with existing data.

### Initial eligibility screen (discovery only)
- Japanese equities; market capitalization >= JPY 100,000,000,000
- Equity/total assets >= 40%
- Published **ordinary profit** YoY >= +10% (not pretax, net income or operating profit)
- Last confirmed 52-week high vs confirmed close <= -15%
- Missing or stale financial data => UNVERIFIED, never pass
- Exclude ETFs, REITs, financial institutions requiring distinct leverage metrics unless separate vetted rules are added

### Subsequent gated decision (no automatic trades)
Only call a candidate BUY-ELIGIBLE after an independently sourced TMR10 score >=80, improving/positive trend, strong sector and latest earnings check. Falling price alone is not a buy signal. If score/trend/sector/earnings data unavailable, display WATCH / insufficient confirmation, not GO.

### Data and refresh
- Give source, fiscal period and as-of date per financial value; show stale/unknown explicitly.
- The Python Yahoo/yfinance prototype does not provide complete reliable Japanese ordinary profit data. A verified Japanese fundamentals source is needed before whole-market discovery.
- Return per-ticker partial failures without rewriting saved watchlists or existing holdings.

### Acceptance tests
1. Existing 13 individual equities, 4 ETFs, all scoring and saved data unchanged.
2. Empty/unavailable financial metrics cannot qualify.
3. Identical TMR10 score before/after enabling feature for all existing holdings.
4. Disable feature: existing site functions exactly as before.
5. App reload retains all pre-existing history, limit orders and settings.
6. No buy notification until TMR10 and chart gates both pass.
7. Mobile layout and refresh errors show readable Japanese diagnostics.

Source prototype: https://github.com/theonda/tmr10-swing-signal/tree/main
