"""Fade sharp moves on Kalshi 15-minute Bitcoin windows and sell into the snap-back.

Entry (either side): Bitcoin moves at least --drop-sigma times its normal
3-minute move, the contract on the opposite side costs <= --max-entry, and
>= 4 minutes remain in the window.
  - sharp drop  -> buy YES ("Up")
  - sharp spike -> buy NO ("Down")
Each entry buys --contracts with an IOC limit at the ask.

Exit: sell (IOC at the bid) once the bid is >= entry + max(5c, 30% of entry);
with under 1 minute left, sell at any profit; otherwise hold to settlement, so
the most a trade can lose is its cost.

Stops after --max-trades entries or once realized P/L reaches -max-loss.

Usage:
  python3 trading/btc15_dip.py [--max-trades 10] [--contracts 3] [--max-loss 2.50]
                               [--hours 2] [--live]
Without --live it logs what it would do.
"""

import argparse
import math
import os
import sys
import time
import uuid
from collections import deque
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btc15_watch import active_window, log, minute_vol, spot_price  # noqa: E402
from kalshi_client import KalshiClient  # noqa: E402
from odds_scan import taker_fee  # noqa: E402

POLL_SECONDS = 10
MOVE_WINDOW_SECONDS = 180


def seconds_left(market):
    return datetime.fromisoformat(market["close_time"].replace("Z", "+00:00")).timestamp() - time.time()


def quotes(market, side):
    """(ask, bid) in dollars for the given contract side."""
    return float(market.get(f"{side}_ask_dollars") or 0), float(market.get(f"{side}_bid_dollars") or 0)


def send(client, live, ticker, side, action, count, price):
    """IOC order. The V2 book is YES-only: buy YES / sell NO are YES bids,
    buy NO / sell YES are YES asks at (1 - NO price)."""
    yes_bid = (action == "buy") == (side == "yes")
    order = {
        "ticker": ticker,
        "side": "bid" if yes_bid else "ask",
        "count": f"{count}.00",
        "price": f"{price if side == 'yes' else 1 - price:.4f}",
        "time_in_force": "immediate_or_cancel",
        "self_trade_prevention_type": "taker_at_cross",
        "client_order_id": str(uuid.uuid4()),
    }
    if action == "sell":
        order["reduce_only"] = True
    if not live:
        log(f"DRY RUN {action} {count} {side.upper()} {ticker} @ {price:.2f}")
        return count, price
    resp = client.request("POST", "/portfolio/events/orders", body=order)
    filled = int(float(resp.get("fill_count", 0)))
    avg_yes = float(resp.get("average_fill_price") or order["price"])
    avg = avg_yes if side == "yes" else 1 - avg_yes
    log(f"ORDER {action} {count} {side.upper()} {ticker} @ {price:.2f}: filled {filled} avg {avg:.4f} "
        f"fee/contract {resp.get('average_fee_paid')}")
    return filled, avg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-trades", type=int, default=10)
    parser.add_argument("--contracts", type=int, default=3)
    parser.add_argument("--max-entry", type=float, default=0.25)
    parser.add_argument("--drop-sigma", type=float, default=2.0)
    parser.add_argument("--max-loss", type=float, default=2.50)
    parser.add_argument("--hours", type=float, default=2)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    client = KalshiClient()
    deadline = time.time() + args.hours * 3600
    history = deque()  # (timestamp, spot)
    sigma, sigma_at = minute_vol(), time.time()
    trades, traded_windows, position, pending, pnl = 0, set(), None, [], 0.0
    log(f"start: live={args.live} max_trades={args.max_trades} contracts={args.contracts} "
        f"max_entry={args.max_entry} drop_sigma={args.drop_sigma} max_loss={args.max_loss}")

    def can_enter():
        return trades < args.max_trades and pnl > -args.max_loss

    while time.time() < deadline and (position or pending or can_enter()):
        try:
            # settle positions held through expiry once Kalshi posts the result
            for p in list(pending):
                result = client.request("GET", f"/markets/{p['ticker']}")["market"].get("result")
                if result in ("yes", "no"):
                    payout = 1.0 if result == p["side"] else 0.0
                    trade_pnl = (payout - p["entry"] - taker_fee(p["entry"])) * p["count"]
                    pnl += trade_pnl
                    log(f"SETTLED {p['ticker']} result={result} held {p['count']} {p['side'].upper()} "
                        f"@ {p['entry']:.2f}: P/L ${trade_pnl:+.2f} | day ${pnl:+.2f}")
                    pending.remove(p)

            spot, _ = spot_price()
            now = time.time()
            if spot:
                history.append((now, spot))
            while history and now - history[0][0] > MOVE_WINDOW_SECONDS:
                history.popleft()
            if now - sigma_at > 600:
                sigma, sigma_at = minute_vol(), now

            if position:
                m = client.request("GET", f"/markets/{position['ticker']}")["market"]
                left = seconds_left(m)
                _, bid = quotes(m, position["side"])
                entry = position["entry"]
                target = entry + max(0.05, 0.30 * entry)
                if left <= 0:
                    log(f"{position['ticker']} closed holding {position['count']} {position['side'].upper()} "
                        f"@ {entry:.2f}; waiting for settlement")
                    pending.append(position)
                    position = None
                elif bid >= target or (left < 60 and bid - taker_fee(bid) > entry + taker_fee(entry)):
                    filled, avg = send(client, args.live, position["ticker"], position["side"], "sell",
                                       position["count"], bid)
                    if filled:
                        trade_pnl = (avg - entry - taker_fee(avg) - taker_fee(entry)) * filled
                        pnl += trade_pnl
                        log(f"EXIT sold {filled} {position['side'].upper()} @ {avg:.2f} (entry {entry:.2f}) "
                            f"P/L ${trade_pnl:+.2f} | day ${pnl:+.2f}")
                        position["count"] -= filled
                        if position["count"] == 0:
                            position = None
                time.sleep(POLL_SECONDS)
                continue

            m = active_window(client) if can_enter() else None
            if not m or m["ticker"] in traded_windows or len(history) < 2 or not spot:
                time.sleep(POLL_SECONDS)
                continue
            span = now - history[0][0]
            move = spot - history[0][1]
            normal_move = sigma * math.sqrt(max(span, 60) / 60) * spot
            left = seconds_left(m)
            side = "yes" if move < 0 else "no"  # fade the move
            ask, _ = quotes(m, side)
            if abs(move) >= args.drop_sigma * normal_move and 0 < ask <= args.max_entry and left >= 240:
                log(f"{'DIP' if side == 'yes' else 'SPIKE'} {m['ticker']}: BTC {move:+.0f} in {span:.0f}s "
                    f"(normal {normal_move:.0f}), spot {spot:.2f} vs strike {float(m['floor_strike']):.2f}, "
                    f"{side.upper()} ask {ask:.2f}, {left / 60:.1f}m left")
                filled, avg = send(client, args.live, m["ticker"], side, "buy", args.contracts, ask)
                traded_windows.add(m["ticker"])
                if filled:
                    position = {"ticker": m["ticker"], "side": side, "count": filled, "entry": avg}
                    trades += 1
            time.sleep(POLL_SECONDS)
        except SystemExit as e:
            log(f"API error: {e}")
            time.sleep(30)
        except Exception as e:  # keep watching through network hiccups
            log(f"error: {e!r}")
            time.sleep(30)

    log(f"stop: {trades} trade(s), realized P/L ${pnl:+.2f}")


if __name__ == "__main__":
    main()
