"""Buy the dip on Kalshi 15-minute Bitcoin windows and sell into a bounce.

Entry: Bitcoin falls sharply (at least --drop-sigma times the normal 3-minute
move), the window's YES ("Up") ask is <= --max-entry, and >= 4 minutes remain.
Buys --contracts YES with an IOC limit at the ask.

Exit: sell (IOC at the bid) once the bid is >= entry + max(5c, 30% of entry);
with under 1 minute left, sell at any profit; otherwise hold to settlement, so
the most a trade can lose is its cost.

Usage:
  python3 trading/btc15_dip.py [--max-trades 2] [--contracts 3] [--hours 2] [--live]
Without --live it logs what it would do.
"""

import argparse
import math
import os
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btc15_watch import active_window, log, minute_vol, spot_price  # noqa: E402
from kalshi_client import KalshiClient  # noqa: E402
from odds_scan import taker_fee  # noqa: E402

POLL_SECONDS = 10
DROP_WINDOW_SECONDS = 180


def seconds_left(market):
    return datetime.fromisoformat(market["close_time"].replace("Z", "+00:00")).timestamp() - time.time()


def send(client, live, ticker, side, count, price):
    """IOC order on the YES book; side 'bid' buys YES, 'ask' sells YES."""
    order = {
        "ticker": ticker,
        "side": side,
        "count": f"{count}.00",
        "price": f"{price:.4f}",
        "time_in_force": "immediate_or_cancel",
        "self_trade_prevention_type": "taker_at_cross",
        "client_order_id": str(uuid.uuid4()),
    }
    if side == "ask":
        order["reduce_only"] = True
    if not live:
        log(f"DRY RUN {side} {count} {ticker} @ {price:.2f}")
        return count, price
    resp = client.request("POST", "/portfolio/events/orders", body=order)
    filled = int(float(resp.get("fill_count", 0)))
    avg = float(resp.get("average_fill_price") or price)
    log(f"ORDER {side} {count} {ticker} @ {price:.2f}: filled {filled} avg {avg:.4f} "
        f"fee/contract {resp.get('average_fee_paid')}")
    return filled, avg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-trades", type=int, default=2)
    parser.add_argument("--contracts", type=int, default=3)
    parser.add_argument("--max-entry", type=float, default=0.25)
    parser.add_argument("--drop-sigma", type=float, default=2.0)
    parser.add_argument("--hours", type=float, default=2)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    client = KalshiClient()
    deadline = time.time() + args.hours * 3600
    history = deque()  # (timestamp, spot)
    sigma, sigma_at = minute_vol(), time.time()
    trades, traded_windows, position = [], set(), None
    log(f"start: live={args.live} max_trades={args.max_trades} contracts={args.contracts} "
        f"max_entry={args.max_entry} drop_sigma={args.drop_sigma}")

    while time.time() < deadline and (position or len(trades) < args.max_trades):
        try:
            spot, _ = spot_price()
            now = time.time()
            if spot:
                history.append((now, spot))
            while history and now - history[0][0] > DROP_WINDOW_SECONDS:
                history.popleft()
            if now - sigma_at > 600:
                sigma, sigma_at = minute_vol(), now

            if position:
                m = client.request("GET", f"/markets/{position['ticker']}")["market"]
                left = seconds_left(m)
                bid = float(m.get("yes_bid_dollars") or 0)
                entry = position["entry"]
                target = entry + max(0.05, 0.30 * entry)
                if left <= 0:
                    log(f"{position['ticker']} closed holding {position['count']} @ {entry:.2f}; settles at expiry")
                    trades[-1]["exit"] = "settlement"
                    position = None
                elif bid >= target or (left < 60 and bid - taker_fee(bid) > entry + taker_fee(entry)):
                    filled, avg = send(client, args.live, position["ticker"], "ask", position["count"], bid)
                    if filled:
                        pnl = (avg - entry) * filled - (taker_fee(avg) + taker_fee(entry)) * filled
                        log(f"EXIT sold {filled} @ {avg:.2f} (entry {entry:.2f}) est P/L ${pnl:+.2f}")
                        position["count"] -= filled
                        trades[-1]["exit"] = f"sold @ {avg:.2f}"
                        if position["count"] == 0:
                            position = None
                time.sleep(POLL_SECONDS)
                continue

            m = active_window(client)
            if not m or m["ticker"] in traded_windows or len(history) < 2 or not spot:
                time.sleep(POLL_SECONDS)
                continue
            span = now - history[0][0]
            drop = history[0][1] - spot
            normal_move = sigma * math.sqrt(max(span, 60) / 60) * spot
            yes_ask = float(m.get("yes_ask_dollars") or 0)
            left = seconds_left(m)
            if drop >= args.drop_sigma * normal_move and 0 < yes_ask <= args.max_entry and left >= 240:
                log(f"DIP {m['ticker']}: BTC -{drop:.0f} in {span:.0f}s (normal {normal_move:.0f}), "
                    f"spot {spot:.2f} vs strike {float(m['floor_strike']):.2f}, yes_ask {yes_ask:.2f}, {left / 60:.1f}m left")
                filled, avg = send(client, args.live, m["ticker"], "bid", args.contracts, yes_ask)
                traded_windows.add(m["ticker"])
                if filled:
                    position = {"ticker": m["ticker"], "count": filled, "entry": avg}
                    trades.append({"ticker": m["ticker"], "entry": avg, "count": filled})
            time.sleep(POLL_SECONDS)
        except SystemExit as e:
            log(f"API error: {e}")
            time.sleep(30)
        except Exception as e:  # keep watching through network hiccups
            log(f"error: {e!r}")
            time.sleep(30)

    log(f"stop: trades={trades}")


if __name__ == "__main__":
    main()
