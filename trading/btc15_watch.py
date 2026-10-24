"""Watch Kalshi 15-minute Bitcoin windows and bet only when the model has an edge.

Model: the window settles YES if the 60-second BRTI average at close is at
least the opening average (the market's floor_strike). Spot is proxied by the
median of BRTI constituent exchanges; P(up) assumes a driftless random walk
with volatility from the last two hours of 1-minute Coinbase candles.

Each window is checked while 3-10 minutes remain. A bet is placed (IOC limit at
the current ask) only if model edge after the taker fee >= --min-edge.

Usage:
  python3 trading/btc15_watch.py [--max-bets 2] [--contracts 2] [--min-edge 0.04]
                                 [--hours 2] [--max-loss 2.50] [--live]
Without --live it only logs what it would do.
"""

import argparse
import math
import os
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from statistics import NormalDist

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kalshi_client import KalshiClient  # noqa: E402
from odds_scan import taker_fee  # noqa: E402

SERIES = "KXBTC15M"


def log(msg):
    print(f"{datetime.now(timezone.utc):%H:%M:%S}Z {msg}", flush=True)


def spot_price():
    """Median of BRTI constituent exchanges that answer quickly."""
    sources = {
        "coinbase": lambda: float(requests.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker", timeout=5).json()["price"]),
        "kraken": lambda: float(next(iter(requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=5).json()["result"].values()))["c"][0]),
        "bitstamp": lambda: float(requests.get("https://www.bitstamp.net/api/v2/ticker/btcusd/", timeout=5).json()["last"]),
        "gemini": lambda: float(requests.get("https://api.gemini.com/v1/pubticker/btcusd", timeout=5).json()["last"]),
    }
    prices = {}
    for name, fetch in sources.items():
        try:
            prices[name] = fetch()
        except Exception:
            pass
    if len(prices) < 2:
        return None, prices
    return statistics.median(prices.values()), prices


def minute_vol():
    candles = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/candles",
                           params={"granularity": 60}, timeout=10).json()[:120]
    closes = [c[4] for c in reversed(candles)]
    return statistics.pstdev(math.log(b / a) for a, b in zip(closes, closes[1:]))


def active_window(client):
    now = int(time.time())
    markets = client.request("GET", "/markets", params={
        "series_ticker": SERIES, "min_close_ts": now, "max_close_ts": now + 1200, "limit": 5})["markets"]
    active = [m for m in markets if m["status"] == "active" and m.get("floor_strike")]
    return min(active, key=lambda m: m["close_time"]) if active else None


def realized_pnl(client, tickers):
    """Sum settled P/L for markets we bet on (revenue - cost - fees), in dollars."""
    total = 0.0
    for ticker in tickers:
        data = client.request("GET", "/portfolio/settlements", params={"ticker": ticker})
        for s in data.get("settlements", []):
            total += (float(s.get("revenue", 0)) - float(s.get("yes_total_cost", 0)) - float(s.get("no_total_cost", 0))) / 100
            total -= float(s.get("fee_cost", 0) or 0)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-bets", type=int, default=2)
    parser.add_argument("--contracts", type=int, default=2)
    parser.add_argument("--min-edge", type=float, default=0.04)
    parser.add_argument("--hours", type=float, default=2)
    parser.add_argument("--max-loss", type=float, default=2.50)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    client = KalshiClient()
    deadline = time.time() + args.hours * 3600
    bets, done_windows = [], set()
    log(f"start: live={args.live} max_bets={args.max_bets} contracts={args.contracts} min_edge={args.min_edge}")

    while time.time() < deadline and len(bets) < args.max_bets:
        try:
            m = active_window(client)
            if not m or m["ticker"] in done_windows:
                time.sleep(20)
                continue
            close = datetime.fromisoformat(m["close_time"].replace("Z", "+00:00")).timestamp()
            mins = (close - time.time()) / 60
            if mins > 10:
                time.sleep(min(30, (mins - 10) * 60))
                continue
            if mins < 3:
                done_windows.add(m["ticker"])
                continue

            # refresh quotes right before deciding
            m = client.request("GET", f"/markets/{m['ticker']}")["market"]
            spot, prices = spot_price()
            if spot is None:
                log("spot unavailable, skipping check")
                time.sleep(20)
                continue
            sigma = minute_vol()
            strike = float(m["floor_strike"])
            t = max(mins - 0.5, 0.1)  # settlement averages the final 60s
            p_up = 1 - NormalDist().cdf(math.log(strike / spot) / (sigma * math.sqrt(t)))
            yes_ask, no_ask = float(m["yes_ask_dollars"]), float(m["no_ask_dollars"])
            edges = {}
            if 0 < yes_ask < 1:
                edges["yes"] = (p_up - yes_ask - taker_fee(yes_ask), yes_ask)
            if 0 < no_ask < 1:
                edges["no"] = ((1 - p_up) - no_ask - taker_fee(no_ask), no_ask)
            side, (edge, ask) = max(edges.items(), key=lambda kv: kv[1][0])
            log(f"{m['ticker']} {mins:4.1f}m left strike {strike:.2f} spot {spot:.2f} ({spot - strike:+.2f}) "
                f"n_src={len(prices)} sigma={sigma * 1e4:.1f}bp P(up)={p_up:.3f} yes_ask={yes_ask:.2f} "
                f"no_ask={no_ask:.2f} best={side} edge={edge:+.3f}")

            if edge >= args.min_edge and ask <= 0.60:  # 2 bets x 2 x 60c stays under $2.50
                order = {
                    "ticker": m["ticker"],
                    "side": "bid" if side == "yes" else "ask",
                    "count": f"{args.contracts}.00",
                    "price": f"{ask if side == 'yes' else 1 - ask:.4f}",
                    "time_in_force": "immediate_or_cancel",
                    "self_trade_prevention_type": "taker_at_cross",
                    "client_order_id": str(uuid.uuid4()),
                }
                if args.live:
                    resp = client.request("POST", "/portfolio/events/orders", body=order)
                    filled = float(resp.get("fill_count", 0))
                    log(f"ORDER {side.upper()} {args.contracts} @ {ask:.2f}: filled {filled} "
                        f"avg {resp.get('average_fill_price')} fee {resp.get('average_fee_paid')}")
                    if filled > 0:
                        bets.append(m["ticker"])
                else:
                    log(f"DRY RUN would buy {side.upper()} {args.contracts} @ {ask:.2f}")
                    bets.append(m["ticker"])
                done_windows.add(m["ticker"])
            else:
                time.sleep(60)  # re-check this window a minute later

            if args.live and bets and realized_pnl(client, bets) <= -args.max_loss:
                log("max loss reached, stopping")
                break
        except SystemExit as e:
            log(f"API error: {e}")
            time.sleep(30)
        except Exception as e:  # network hiccups should not kill the watcher
            log(f"error: {e!r}")
            time.sleep(30)

    log(f"stop: {len(bets)} bet(s): {bets}")
    if args.live and bets:
        # wait for the last window to settle, then report
        time.sleep(max(0, datetime.fromisoformat(
            client.request("GET", f"/markets/{bets[-1]}")["market"]["close_time"].replace("Z", "+00:00")
        ).timestamp() - time.time()) + 120)
        for ticker in bets:
            mk = client.request("GET", f"/markets/{ticker}")["market"]
            log(f"{ticker} result={mk.get('result')!r}")
        log(f"realized P/L on these bets: ${realized_pnl(client, bets):+.2f}")


if __name__ == "__main__":
    main()
