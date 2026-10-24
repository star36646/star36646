"""Compare Kalshi game-winner prices with de-vigged sportsbook odds.

Fair probability comes from Pinnacle when it quotes the game, otherwise the
median of the de-vigged bookmaker prices. Edge = fair - Kalshi yes ask - fee.

Usage:
  python3 trading/odds_scan.py nfl [--min-edge 0.05] [--cache DIR]
Sports: nfl, ncaaf, nba, nhl, mlb. Each live sport costs 2 Odds API requests
(regions eu,us x h2h); --cache DIR reuses DIR/<sport_key>.json if present.
"""

import argparse
import json
import math
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kalshi_client import KalshiClient  # noqa: E402

SPORTS = {
    "nfl": ("americanfootball_nfl", "KXNFLGAME"),
    "ncaaf": ("americanfootball_ncaaf", "KXNCAAFGAME"),
    "nba": ("basketball_nba", "KXNBAGAME"),
    "nhl": ("icehockey_nhl", "KXNHLGAME"),
    "mlb": ("baseball_mlb", "KXMLBGAME"),
}


def taker_fee(price):
    """Kalshi taker fee per contract in dollars: ceil(7% * P * (1-P)) cents."""
    return math.ceil(round(7 * price * (1 - price), 6)) / 100


def fetch_odds(sport_key, cache):
    path = os.path.join(cache, f"{sport_key}.json") if cache else None
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    response = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/",
        params={"apiKey": os.environ["ODDS_API_KEY"], "regions": "eu,us",
                "markets": "h2h", "oddsFormat": "decimal"},
        timeout=20,
    )
    response.raise_for_status()
    print(f"Odds API requests remaining: {response.headers.get('x-requests-remaining')}")
    data = response.json()
    if path:
        with open(path, "w") as f:
            json.dump(data, f)
    return data


def fair_probs(game):
    """Return ({team: prob}, source) for a two-way game."""
    devigged = {}
    for book in game["bookmakers"]:
        for market in book["markets"]:
            outcomes = market["outcomes"]
            if market["key"] != "h2h" or len(outcomes) != 2:
                continue
            implied = {o["name"]: 1 / o["price"] for o in outcomes}
            total = sum(implied.values())
            devigged[book["key"]] = {k: v / total for k, v in implied.items()}
    if not devigged:
        return None, None
    if "pinnacle" in devigged:
        return devigged["pinnacle"], "pinnacle"
    teams = [game["home_team"], game["away_team"]]
    probs = {t: statistics.median(d[t] for d in devigged.values() if t in d) for t in teams}
    total = sum(probs.values())
    return {t: p / total for t, p in probs.items()}, f"median of {len(devigged)}"


def kalshi_markets(client, series):
    markets, cursor = [], None
    while True:
        params = {"series_ticker": series, "status": "open", "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        data = client.request("GET", "/markets", params=params)
        markets += data.get("markets", [])
        cursor = data.get("cursor")
        if not cursor:
            return markets


def match_team(label, teams):
    """Map a Kalshi label like 'Seattle' or 'Miami (OH)' to one odds team name."""
    label = label.lower().replace(".", "")
    hits = [t for t in teams if t.lower().replace(".", "").startswith(label + " ") or t.lower() == label]
    return hits[0] if len(hits) == 1 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sport", choices=SPORTS)
    parser.add_argument("--min-edge", type=float, default=0.05)
    parser.add_argument("--cache")
    parser.add_argument("--all", action="store_true", help="print every matched market")
    args = parser.parse_args()

    sport_key, series = SPORTS[args.sport]
    games = fetch_odds(sport_key, args.cache)
    by_event = {}
    for m in kalshi_markets(KalshiClient(), series):
        by_event.setdefault(m["event_ticker"], []).append(m)

    # Live games are excluded: in-play bookmaker odds lag the game and a snapshot
    # comparison against Kalshi's live price is noise, not edge.
    now = datetime.now(timezone.utc)
    games = [g for g in games
             if datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00")) > now]
    rows, unmatched = [], 0
    for event, markets in by_event.items():
        when = datetime.fromisoformat(markets[0]["occurrence_datetime"].replace("Z", "+00:00"))
        found = None
        for game in games:
            start = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
            if abs(start - when) > timedelta(hours=36):
                continue
            teams = [game["home_team"], game["away_team"]]
            names = [match_team(m["yes_sub_title"], teams) for m in markets]
            if all(names) and len(set(names)) == len(markets):
                found = (game, names)
                break
        if not found:
            unmatched += 1
            continue
        game, names = found
        probs, source = fair_probs(game)
        if not probs:
            continue
        for m, name in zip(markets, names):
            ask = float(m.get("yes_ask_dollars") or 0)
            if not 0 < ask < 1:
                continue
            fair = probs[name]
            edge = fair - ask - taker_fee(ask)
            rows.append((edge, m["ticker"], name, ask, fair, source, game["commence_time"],
                         float(m.get("yes_ask_size_fp") or 0)))

    rows.sort(reverse=True)
    print(f"{len(rows)} Kalshi sides matched, {unmatched} events unmatched")
    print(f"{'edge':>6} {'ask':>5} {'fair':>5}  {'start (UTC)':16}  ticker / team / source / ask size")
    for edge, ticker, name, ask, fair, source, start, size in rows:
        if args.all or edge >= args.min_edge:
            print(f"{edge:+6.3f} {ask:5.2f} {fair:5.3f}  {start[:16]}  {ticker}  {name}  [{source}]  size {size:.0f}")


if __name__ == "__main__":
    main()
