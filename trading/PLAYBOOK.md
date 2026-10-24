# $50 → $1,000 Trading Playbook

Rules for the Robinhood agentic account ("MCP", ••••5652). Built from research on 2026-10-24.
The goal is to compound without blowing up. Rules beat feelings, every time.

## 0. Ground truth (read first)

- **Most day traders lose.** Brazil study: 97% of people who day-traded 300+ days lost money; Taiwan study: <1% beat the market consistently. Edge comes from selectivity and risk control, not from trading more.
- **Most small-cap gappers fade.** Across ~3,000 small-cap gap-up events (SmallCapLab, 2022–2026): 64–67% close below their open, ~73% close below VWAP, ~75% open lower the next day. 50% of the day's highs are in by 9:45 ET, ~70% by 10:30, ~86% by 11:30. Monday gappers fade a little less (64%) than Tue–Thu (70–72%).
  - A gapper that barely pushes above its open fades 93% of the time; one that extends 100%+ fades only ~11%. **Only trade strength that is proving itself, and only early.**
- **PDT rule is gone** (FINRA intraday margin replaced it on 2026-06-04). Unlimited day trades are allowed, so the trade count is limited by discipline only.
- **Account mechanics at $50:**
  - Prefer **whole shares of $2–$20 stocks**. Whole shares allow limit orders in pre-market/after-hours and real stop / OCO orders.
  - Fractional shares are market-orders-only, regular hours only, and can't take stops; use them only for swing trades in pricier names.
  - Spread is a hidden fee. Skip anything with a spread > 1% of price.

## 1. Risk rules (non-negotiable)

| Rule | Value |
|---|---|
| Max risk per trade (entry → stop × shares) | **$2.50 (5% of account)**; rescale as the account grows |
| Daily loss limit | **$5 (10%)**, then done for the day |
| Weekly loss limit | **$10 (20%)**, then paper-trade only until next week |
| Max open positions | 1 (2 once account > $150) |
| Margin / options / shorting | **None** |
| Averaging down | **Never** |
| Hold small-cap gappers overnight | **Never** (75% gap down next day) |
| Hold through earnings / FDA / known events | **Never** (check the calendar before every swing entry) |
| Minimum reward : risk | 2 : 1 planned (expect to capture about half of the potential) |

Position size = risk $ ÷ (entry − stop). If the stop is "structurally" too far for $2.50, **skip the trade**. Never move the stop closer just to fit the size.

Scaling (Doug's "3R" rule): raise risk per trade only after **2 consecutive green weeks**, and by ~10% for each +10% of account growth.

Stops go at **structural** levels (below the pullback low, breakout candle low, or opening range low), never at an arbitrary dollar amount.

## 2. Setup A — Opening momentum (day trade, 9:30–10:30 ET)

**Stock selection (Ross Cameron's 5 pillars):** up ≥10% on the day · relative volume ≥5× · fresh news catalyst · price $2–$20 · float <20M.
→ Robinhood saved scan **"Momentum Gappers (5 Pillars)"** `7dba3096-730e-433a-841c-2d77950a19c0`.

**Gate (SMB Capital):** the opening price must be **above yesterday's high AND yesterday's close**. If not, there's no opening-drive trade.

**Trigger:** a 2-minute candle **closes** above the **pre-market high** on expanding volume (RVOL > 3).
- Reject the candle if its upper wick is more than ½ of its body, if it closes red, or if a wick pokes through and the close falls back below.
- It needs room: no obvious resistance within 3–5% overhead.
- Market tailwind: SPY/QQQ above their 10- and 20-day SMAs, and not red on the day.

**Alternative trigger (first pullback):** after the initial squeeze, wait for the first pullback. Buy when the first candle makes a new high over the prior candle (the "crossing candle"). Stop goes below the pullback low.

**Management:**
- Stop goes below the breakout candle low. Exit immediately if a 2-minute candle closes back below the pre-market high.
- Take ½ off at the first target (high of day, round number, or ~1× daily ATR from the open). Trail the rest under the 2-minute 9 EMA.
- Exit on warning signs: a big topping tail or doji at highs, or volume fading as price rises.
- **No new momentum entries after 10:30 ET.** Be flat by close.

## 3. Setup B — Opening range breakout + VWAP (liquid stocks/ETFs)

- Mark the high and low of the first 5 or 15 minutes.
- Go long only on a candle **close** above the range high **with price above VWAP**, and the daily trend up (price > 20-day SMA).
- Stop goes at the range midpoint or the range low. Target 1–1.5× the range height.
- One trade per side per day. No breakouts after 11:30 ET.

## 4. Setup C — Swing pullback (hold 2–10 days)

**Selection:** price > 50-day SMA · 10-day SMA > 20-day SMA, both rising · daily RSI(14) 40–60 · avg volume > 2M · no earnings within the holding window.
→ Robinhood saved scan **"Swing Pullbacks (Uptrend, RSI 40-60)"** `36cadd64-1711-481c-bb13-2969d1ba667a`.

**Entry:**
- (a) The pullback to the rising 9/21 EMA or prior breakout level retraces **40–60%** of the last impulse leg, on **falling volume** with small, mixed-color candles. Buy above the high of a hammer, doji, or narrow-range reversal candle.
- Or (b) a breakout close above a tight base, on a volume spike.

**Stop:** below the pullback low or base low. **Target:** the prior swing high, then 2R. Trail under the 5- or 10-day SMA. Sell into extreme gaps up.

**Relative strength bonus (SMB):** on red market days, note the stocks holding near their 52-week or all-time highs with 10 > 20 SMA. Put them at the top of the watchlist, then buy the breakout when the market turns.

## 5. Daily routine

1. **Pre-market (8:00–9:25 ET):** check the account state. Run the gapper scan. For the top 1–3 names, check the catalyst and look for dilution risk: an S-3/424B5 shelf or a recent offering means pass. Mark pre-market high, yesterday's high/close, and VWAP.
2. **9:30–10:30:** take at most 2 attempts on Setup A or B. Respect the daily loss limit.
3. **Midday:** usually stand aside.
4. **3:00–3:55:** review swing candidates. Enter or exit swing trades. Make sure there are no day-trade leftovers.
5. **After close:** log every trade below, including entry, exit, R multiple, setup, rule followed (y/n), and the lesson.

## 6. Things that blow up accounts (from r/Daytrading postmortems)

Overtrading, revenge trading after a loss, oversizing after a hot streak, widening stops, holding losers "until it comes back", constantly switching strategies, chasing extended candles (FOMO), trading low-volume names, and holding through binary events.

## 7. Trade log

| # | Date | Ticker | Setup | Shares | Entry | Stop | Exit | P/L $ | R | Rules followed? | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|

Starting balance: **$50.00** (2026-10-24)

## Sources

- SMB Capital, *The Only Opening Momentum Strategy I'd Trade*; *Relative Strength Breakout Strategy*; *6 Momentum Trades* (YouTube transcripts)
- Ross Cameron / Warrior Trading, *$2,000 → $105,951 in 46 Days* (5 pillars, first-pullback entry, exit indicators)
- Doug (*If You Only Have $50, the 3R Rule*): 50-day trend bias, structural stops, ATR targets, slow scaling
- Andrew Aziz / Bear Bull Traders, *2-Minute Opening Range Breakout*; *ORB + VWAP* lesson
- Mind Math Money, *Pullback strategy* (impulse + low-volume pullback); 9 EMA strategy (40–60% retracement "golden zone")
- SmallCapLab gapper statistics; Barber/Lee/Liu/Odean (Taiwan); Chague/De-Losso/Giovannetti (Brazil)
- Robinhood Help Center: Day trading / intraday margin (PDT replaced 2026-06-04)
