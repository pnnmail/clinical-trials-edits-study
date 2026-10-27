"""Stage 4, data: daily prices (Alpaca — includes delisted ones), XBI/IBB, share counts (XBRL).

Alpaca stitches history itself when a ticker changes (IMUX includes VTL, LENZ — GRPH). A freed symbol
may go to another company — so prices are cut to the listing period [listed_from, listed_to].
Saves data/prices.parquet (date, ticker, cik, adj_close, close, volume) and data/shares.parquet."""
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, RAW, ROOT, get_logger, sec_client  # noqa: E402

log = get_logger("prices")
START = "2016-12-01"  # 250 trading days before the first events of 2018
PX_DIR = RAW / "PRICES"
SH_DIR = RAW / "SEC" / "shares"
for d in (PX_DIR, SH_DIR):
    d.mkdir(parents=True, exist_ok=True)


def alpaca_headers():
    """Alpaca keys from the environment or from a .env file in the project root."""
    env = dict(os.environ)
    f = ROOT / ".env"
    if f.exists():
        env.update(re.findall(r"^([A-Z_]+)\s*=\s*(.*)$", f.read_text(encoding="utf-8"), re.M))
    return {"APCA-API-KEY-ID": env["ALPACA_API_KEY_ID"].strip().strip('"'),
            "APCA-API-SECRET-KEY": env["ALPACA_API_SECRET_KEY"].strip().strip('"')}


def bars(sym, adjustment, H):
    p = PX_DIR / f"{sym}_{adjustment}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    out, tok = [], None
    while True:
        params = {"timeframe": "1Day", "start": START, "limit": 10000, "adjustment": adjustment, "feed": "sip"}
        if tok:
            params["page_token"] = tok
        r = None
        for i in range(6):
            try:
                r = requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/bars", params=params, headers=H,
                                 timeout=(10, 60))
            except requests.RequestException as e:  # network failure — retry
                log.warning("%s: %s", sym, type(e).__name__)
                time.sleep(10 * (i + 1))
                continue
            if r.status_code == 429:
                time.sleep(20 * (i + 1))
                continue
            break
        if r is None:
            log.warning("%s %s: network unavailable", sym, adjustment)
            return []  # not cached — will be retried on the next run
        if r.status_code != 200:
            log.warning("%s %s: HTTP %s %s", sym, adjustment, r.status_code, r.text[:100])
            break
        j = r.json()
        out += j.get("bars") or []
        tok = j.get("next_page_token")
        time.sleep(0.35)  # ≤ 200 requests/min
        if not tok:
            break
    p.write_text(json.dumps(out), encoding="utf-8")
    return out


def shares(c, cik):
    p = SH_DIR / f"{cik}.json"
    if not p.exists():
        try:
            r = c.get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/EntityCommonStockSharesOutstanding.json")
        except RuntimeError:
            return []
        p.write_text(r.text if r is not None else "{}", encoding="utf-8")
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("units", {}).get("shares", [])
    except json.JSONDecodeError:
        return []


def main():
    sp = pd.read_parquet(DATA / "sponsors.parquet")
    use = sp[sp.status.isin(["auto", "confirmed"]) & sp.on_exchange & sp.small & sp.ticker.notna()]
    comp = use.groupby("cik").agg(ticker=("ticker", "first"), listed_from=("listed_from", "min"),
                                  listed_to=("listed_to", "max")).reset_index()
    H = alpaca_headers()
    frames = []
    for k, r in enumerate(comp.itertuples(), 1):
        adj, raw = bars(r.ticker, "all", H), bars(r.ticker, "raw", H)
        if not adj:
            continue
        a = pd.DataFrame(adj)[["t", "c", "v"]].rename(columns={"t": "date", "c": "adj_close", "v": "volume"})
        b = pd.DataFrame(raw)[["t", "c"]].rename(columns={"t": "date", "c": "close"}) if raw else None
        x = a.merge(b, on="date", how="left") if b is not None else a.assign(close=None)
        x["date"] = pd.to_datetime(x.date).dt.tz_localize(None).dt.normalize()
        lo = pd.Timestamp(r.listed_from) if isinstance(r.listed_from, str) else pd.Timestamp(START)
        hi = pd.Timestamp(r.listed_to) + pd.Timedelta(days=5) if isinstance(r.listed_to, str) else pd.Timestamp.max
        x = x[(x.date >= lo - pd.Timedelta(days=400)) & (x.date <= hi)]  # someone else's history of the symbol is cut off
        x["ticker"], x["cik"] = r.ticker, r.cik
        frames.append(x)
        if k % 100 == 0:
            log.info("prices: %d/%d", k, len(comp))
    for etf in ("XBI", "IBB"):
        a, b = pd.DataFrame(bars(etf, "all", H)), pd.DataFrame(bars(etf, "raw", H))
        x = a[["t", "c", "v"]].rename(columns={"t": "date", "c": "adj_close", "v": "volume"}).merge(
            b[["t", "c"]].rename(columns={"t": "date", "c": "close"}), on="date")
        x["date"] = pd.to_datetime(x.date).dt.tz_localize(None).dt.normalize()
        x["ticker"], x["cik"] = etf, 0
        frames.append(x)
    px = pd.concat(frames, ignore_index=True)
    px.to_parquet(DATA / "prices.parquet", index=False)
    log.info("prices: %d rows, tickers %d of %d", len(px), px.ticker.nunique() - 2, len(comp))

    c = sec_client()
    rows = []
    for cik in comp.cik:
        for u in shares(c, int(cik)):
            rows.append(dict(cik=int(cik), end=u["end"], shares=u["val"], filed=u.get("filed")))
    sh = pd.DataFrame(rows)
    sh["end"] = pd.to_datetime(sh.end)
    sh = sh.groupby(["cik", "end"], as_index=False).shares.sum()  # share classes are summed
    sh.to_parquet(DATA / "shares.parquet", index=False)
    log.info("shares: %d companies", sh.cik.nunique())


if __name__ == "__main__":
    main()
