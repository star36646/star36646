"""Minimal Kalshi Trade API client for the trading experiment.

Credentials come from the environment:
  KALSHI_API_KEY_ID   - the key ID shown on kalshi.com/account/profile
  KALSHI_PRIVATE_KEY  - the PEM private key (RSA or Ed25519). Real newlines,
                        literal "\\n" sequences, or spaces between the PEM
                        markers and the body are all accepted.
  KALSHI_BASE_URL     - optional, defaults to production.

Usage:
  python3 trading/kalshi_client.py check
  python3 trading/kalshi_client.py balance
  python3 trading/kalshi_client.py positions
  python3 trading/kalshi_client.py orders
  python3 trading/kalshi_client.py markets [--series KXNBAGAME] [--status open] [--limit 20]
  python3 trading/kalshi_client.py market TICKER
  python3 trading/kalshi_client.py orderbook TICKER
  python3 trading/kalshi_client.py buy TICKER yes|no COUNT PRICE_CENTS [--confirm]
  python3 trading/kalshi_client.py sell TICKER yes|no COUNT PRICE_CENTS [--confirm]
  python3 trading/kalshi_client.py cancel ORDER_ID [--confirm]

Orders are limit orders only and are a dry run unless --confirm is passed.
A buy whose maximum cost exceeds MAX_ORDER_COST_CENTS is refused unless
--max-cost-cents raises the cap for that one call.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import uuid
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DEFAULT_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
# Matches the playbook's per-trade risk budget; a buy can lose its full cost.
MAX_ORDER_COST_CENTS = 250

_PEM_RE = re.compile(r"-----BEGIN ([A-Z ]+)-----(.*?)-----END \1-----", re.S)


def normalize_pem(raw):
    """Rebuild a valid PEM from however the key was pasted into the env var."""
    text = raw.strip().strip('"').strip("'").replace("\\n", "\n")
    match = _PEM_RE.search(text)
    if not match:
        raise ValueError("KALSHI_PRIVATE_KEY has no -----BEGIN/END ... KEY----- markers")
    label, body = match.group(1), re.sub(r"\s+", "", match.group(2))
    lines = [body[i:i + 64] for i in range(0, len(body), 64)]
    return f"-----BEGIN {label}-----\n" + "\n".join(lines) + f"\n-----END {label}-----\n"


def load_credentials():
    key_id = os.environ.get("KALSHI_API_KEY_ID", "").strip()
    raw_key = os.environ.get("KALSHI_PRIVATE_KEY", "")
    if not key_id or not raw_key:
        sys.exit("KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY must both be set.")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", key_id):
        sys.exit(f"KALSHI_API_KEY_ID is not a 36-character key ID (got {len(key_id)} characters). "
                 "Copy the full Key ID from kalshi.com/account/profile.")
    private_key = serialization.load_pem_private_key(normalize_pem(raw_key).encode(), password=None)
    return key_id, private_key


def sign(private_key, message):
    if isinstance(private_key, Ed25519PrivateKey):
        signature = private_key.sign(message)
    else:
        signature = private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
    return base64.b64encode(signature).decode()


class KalshiClient:
    def __init__(self):
        self.base_url = os.environ.get("KALSHI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.key_id, self.private_key = load_credentials()

    def request(self, method, path, params=None, body=None):
        url = self.base_url + path
        timestamp = str(int(time.time() * 1000))
        # Kalshi signs timestamp + method + full URL path, without the query string.
        message = (timestamp + method + urlparse(url).path).encode()
        headers = {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": sign(self.private_key, message),
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }
        response = requests.request(method, url, headers=headers, params=params, json=body, timeout=20)
        if response.status_code >= 400:
            sys.exit(f"HTTP {response.status_code} on {method} {path}: {response.text}")
        return response.json() if response.text else {}


def show(data):
    print(json.dumps(data, indent=2, sort_keys=True))


def place_order(client, args, action):
    if not 1 <= args.price_cents <= 99:
        sys.exit("PRICE_CENTS must be between 1 and 99.")
    # The V2 endpoint quotes only the YES book: buying YES or selling NO is a
    # YES bid, buying NO or selling YES is a YES ask at (100 - NO price).
    yes_bid = (action == "buy") == (args.side == "yes")
    yes_price = args.price_cents if args.side == "yes" else 100 - args.price_cents
    order = {
        "ticker": args.ticker,
        "side": "bid" if yes_bid else "ask",
        "count": f"{args.count}.00",
        "price": f"{yes_price / 100:.4f}",
        "time_in_force": "good_till_canceled",
        "self_trade_prevention_type": "taker_at_cross",
        "client_order_id": str(uuid.uuid4()),
    }
    max_cost = args.count * args.price_cents
    cap = args.max_cost_cents if args.max_cost_cents is not None else MAX_ORDER_COST_CENTS
    if action == "buy" and max_cost > cap:
        sys.exit(f"Refused: max cost {max_cost}c exceeds cap {cap}c.")
    print(f"{action.upper()} {args.count} x {args.ticker} {args.side.upper()} @ {args.price_cents}c "
          f"(max cost ${max_cost / 100:.2f})")
    if not args.confirm:
        print("Dry run. Re-run with --confirm to send it.")
        return
    show(client.request("POST", "/portfolio/events/orders", body=order))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("balance")
    sub.add_parser("positions")
    sub.add_parser("orders")
    markets = sub.add_parser("markets")
    markets.add_argument("--series")
    markets.add_argument("--event")
    markets.add_argument("--status", default="open")
    markets.add_argument("--limit", type=int, default=20)
    for name in ("market", "orderbook"):
        sub.add_parser(name).add_argument("ticker")
    for name in ("buy", "sell"):
        order = sub.add_parser(name)
        order.add_argument("ticker")
        order.add_argument("side", choices=["yes", "no"])
        order.add_argument("count", type=int)
        order.add_argument("price_cents", type=int)
        order.add_argument("--max-cost-cents", type=int)
        order.add_argument("--confirm", action="store_true")
    cancel = sub.add_parser("cancel")
    cancel.add_argument("order_id")
    cancel.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    client = KalshiClient()
    if args.command == "check":
        balance = client.request("GET", "/portfolio/balance")
        print(f"Authenticated. Balance: ${balance.get('balance', 0) / 100:.2f}")
    elif args.command == "balance":
        show(client.request("GET", "/portfolio/balance"))
    elif args.command == "positions":
        show(client.request("GET", "/portfolio/positions", params={"count_filter": "position"}))
    elif args.command == "orders":
        show(client.request("GET", "/portfolio/orders", params={"status": "resting"}))
    elif args.command == "markets":
        params = {"status": args.status, "limit": args.limit}
        if args.series:
            params["series_ticker"] = args.series
        if args.event:
            params["event_ticker"] = args.event
        show(client.request("GET", "/markets", params=params))
    elif args.command == "market":
        show(client.request("GET", f"/markets/{args.ticker}"))
    elif args.command == "orderbook":
        show(client.request("GET", f"/markets/{args.ticker}/orderbook"))
    elif args.command in ("buy", "sell"):
        place_order(client, args, args.command)
    elif args.command == "cancel":
        if not args.confirm:
            print(f"Would cancel {args.order_id}. Re-run with --confirm to send it.")
            return
        show(client.request("DELETE", f"/portfolio/orders/{args.order_id}"))


if __name__ == "__main__":
    main()
