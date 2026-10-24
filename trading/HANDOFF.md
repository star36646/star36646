# Handoff: $50 → $1,000 trading experiment

Context carried over from the "Challenge discussion" session (2026-10-24). Read this, then `trading/PLAYBOOK.md`.

## The challenge

Steven (the user) gave Claude a small Robinhood account and asked it to grow $50 toward $1,000 as fast as it can, by learning day trading and swing trading. There's no deadline. Steven framed it as a role-play ("you have a family to feed") and an experiment. He granted autonomy: **Claude may trade the agentic accounts within the risk rules without asking first, and must report every trade with its reasoning.** Steven later added Kalshi (prediction markets).

Ground rules Claude committed to and Steven accepted:
- No promise of "profit every day". Flat days happen, and skipping a bad setup is correct.
- No pump-and-dump plays, no margin, no options, no shorting, no averaging down.
- Report losses honestly. Never fabricate results.

## Accounts

### Robinhood (via the Robinhood Trading MCP connector)
- Agentic account: `893185652`, nickname "MCP", type limited_margin. This is the ONLY account Claude may trade. The default account `594724437` is not accessible to the agent.
- As of 2026-10-24: $50 cash, no positions. The $50 showed as a pending deposit, so confirm buying power before the first trade.
- **Trade approvals are OFF** (`human_must_approve_trades: false`), so orders execute immediately.
- Option level: none. PDT rule no longer applies (FINRA intraday margin replaced it on 2026-06-04).
- Saved scans:
  - `7dba3096-730e-433a-841c-2d77950a19c0`: "Momentum Gappers (5 Pillars)" (stock, ≥10% up, RVOL ≥5, $2–20, float <20M)
  - `36cadd64-1711-481c-bb13-2969d1ba667a`: "Swing Pullbacks (Uptrend, RSI 40-60)"

### Kalshi (via `trading/kalshi_client.py`, no connector)
- Credentials: env vars `KALSHI_API_KEY_ID` and `KALSHI_PRIVATE_KEY` (Ed25519) in the Bloom Trader environment. They load only at session start. Never print them.
- Verified 2026-10-24: authenticated, **balance $23.29, no positions**.
- Kalshi API location verification **expires 2026-10-31 1:12 PM EDT**. After that, API trading is restricted until Steven re-verifies at kalshi.com/account/profile.
- Steven's screenshot also showed a "US Tech 100 Up" position (~$5.13, "10.9x buying power"). It was not in the API positions, so it's probably Kalshi Perps or another app. Leave it alone unless Steven says otherwise.
- Script usage: `check`, `balance`, `positions`, `orders`, `markets --series X`, `market T`, `orderbook T`, `buy/sell T yes|no COUNT PRICE_CENTS --confirm`, `cancel ID --confirm`. Buys are capped at 250¢ max cost.

## Risk rules (both venues)

- Max risk $2.50 per trade (a Kalshi buy can lose its full cost, so cost ≤ $2.50).
- Daily loss limit $5, then stop for the day. Weekly loss limit $10.
- One open position at a time on Robinhood.
- Kalshi: at most 2 bets per day; only bet when Claude's probability clearly beats the price after fees.
- First Kalshi picks: show Steven the reasoning before placing (he was told this).

## Research takeaways (details in PLAYBOOK.md)

- 97% of persistent day traders lose (Brazil study). The edge comes from selectivity.
- Small-cap gappers: about 65% close below the open, about 75% open lower the next day, 50% of highs set by 9:45. So trade only confirmed strength, early, and never hold a gapper overnight.
- Setups: (A) premarket-high breakout on a 2-minute close, with an open above yesterday's high and close; (B) ORB + VWAP; (C) swing pullback in an uptrend, with no earnings in the holding window.

## Schedule

- **Monday 2026-10-26, 9:10am ET:** Robinhood pre-market check-in (scheduled task). Run the gapper scan, check catalysts and dilution, and only trade Setup A/B per the playbook until 10:30 ET. Run the swing scan in the afternoon. Log trades in PLAYBOOK.md.

## Branch

Everything is on `claude/inspiring-goodall-ds655q` in `star36646/star36646`. Commit and push playbook or trade-log changes there. Don't open a PR unless asked.
