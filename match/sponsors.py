"""Stage 2, step 2: trial sponsors -> EDGAR companies (including delisted ones) -> CIK, ticker.

Methods: exact (current or former name, with the period the name was valid), fuzzy (rapidfuzz,
company names only; automatic at ≥ 96 and ≥ 2 words, otherwise manual review).
For each matched company:
  - ticker: current from EDGAR; if empty (delisted) — from the cover of the last 10-K ("Trading Symbol");
  - exchange: current from EDGAR or from the 10-K cover; OTC — outside the pilot;
  - listing period: from the first 10-K of the period (with a one-year margin) to the first form 25/15 (delisting);
  - public float by year (dei:EntityPublicFloat) — for the "up to $10B" cut-off.
Result: data/sponsors.parquet + match/review_sponsors.csv; labels — match/labels.csv."""
import html
import json
import re
import sys
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CFG, DATA, REPORTS, ROOT, RAW, TODAY, get_logger, sec_client  # noqa: E402
from match.normalize import norm, norm_light  # noqa: E402

log = get_logger("sponsors")
MATCH_DIR = ROOT / "match"
LABELS = MATCH_DIR / "labels.csv"
COVER_DIR = RAW / "SEC" / "cover"
FLOAT_DIR = RAW / "SEC" / "float"
for d in (COVER_DIR, FLOAT_DIR):
    d.mkdir(parents=True, exist_ok=True)
FUZZY_AUTO, FUZZY_MIN = 96, 88
EXCH_RX = re.compile(r"(Nasdaq|NASDAQ|New York Stock Exchange|NYSE)", re.I)


def name_table(u):
    """(name_norm, cik, kind, valid_from, valid_to) for current and former names."""
    rows = []
    for r in u.itertuples():
        former = json.loads(r.former_names) if isinstance(r.former_names, str) else []
        tos = [f["to"][:10] for f in former if f.get("to")]
        cur_from = max(tos) if tos else None
        for nm in {r.name, r.name_idx} - {None}:
            rows.append(dict(cik=r.cik, name=nm, kind="current", valid_from=cur_from, valid_to=None))
        for f in former:
            rows.append(dict(cik=r.cik, name=f["name"], kind="former", valid_from=(f.get("from") or "")[:10] or None,
                             valid_to=(f.get("to") or "")[:10] or None))
    t = pd.DataFrame(rows)
    t["name_norm"] = t.name.map(norm)
    t = t[t.name_norm.str.len() >= 3].drop_duplicates(["cik", "name_norm", "kind"])
    return t


EXCH = r"(Nasdaq|NASDAQ|New York Stock Exchange|NYSE)"
NOT_TICKER = {"NYSE", "LLC", "THE", "PER", "INC", "PAR", "USD", "N/A", "NONE", "ADS", "ADR", "CLASS", "COMMON",
              "STOCK", "VALUE", "TITLE", "NAME", "EACH", "ACT", "SEC"}


def doc_text(c, cik, acc, doc):
    p = COVER_DIR / f"{cik}_{acc}.txt"
    if not p.exists():
        r = c.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}")
        t = r.text if r is not None else ""
        t = re.sub(r"(?is)<(script|style|ix:header).*?</\1>", " ", t)  # ix:header is an iXBRL service block
        t = re.sub(r"<[^>]+>", " ", t)
        t = re.sub(r"&nbsp;|&#160;|&#8203;", " ", t)
        t = re.sub(r"\s+", " ", t)[:400000]
        p.write_text(t, encoding="utf-8")
    return p.read_text(encoding="utf-8")


def is_derivative(tick):
    """A warrant/unit/right: 5 letters ending in W, U, R (EFTRW, ABCDU)."""
    return len(tick) == 5 and tick[-1] in "WUR"


def ticker_in_text(t):
    """(ticker, exchange) from a 10-K: the 12(b) table on the cover or the Item 5 phrase "… under the symbol “ABCD”"."""
    t = html.unescape(t)
    m = re.search(r"Section 12\s*\(\s*b\s*\)", t, re.I)
    seg = re.split(r"12\s*\(\s*g\s*\)", t[m.end():m.end() + 700], flags=re.I)[0] if m else ""
    if seg:
        # "CALA The Nasdaq …" — the ticker before the exchange name
        cands = [tm for tm in re.finditer(r"\b([A-Z]{1,5})\b\s+(?:\(\S+\)\s+)?(?:The\s+)?" + EXCH, seg)
                 if tm.group(1) not in NOT_TICKER]
        # a share, not a warrant/unit/right (EFTR, not EFTRW)
        common = [tm for tm in cands if not is_derivative(tm.group(1))]
        if common or cands:
            tm = (common or cands)[0]
            tick = tm.group(1)
            # a table by columns: "EFTR EFTRW Nasdaq …" — the warrant stands next to the exchange, the share before it
            if is_derivative(tick) and re.search(r"\b" + tick[:-1] + r"\b", seg):
                tick = tick[:-1]
            return tick, tm.group(2)
        # «Trading Symbol XENT Name of Exchange … The Nasdaq Global Market»
        tm = re.search(r"Trading\s+Symbol\(?s?\)?\s+([A-Z]{1,5})\b", seg)
        ex = re.search(EXCH, seg)
        if tm and ex and tm.group(1) not in NOT_TICKER:
            return tm.group(1), ex.group(1)
        if re.search(r"Trading\s+Symbol", seg, re.I):
            return None, None  # the table exists but no security is listed (12(b): None) — look at an older 10-K
    # 10-Ks before 2019 have no Trading Symbol field: "… traded on the Nasdaq … under the symbol “LOXO”"
    other = re.compile(r"Toronto|TSX|London|LSE|Euronext|ASX|Australian|Tel Aviv|TASE|SIX|Frankfurt|AIM", re.I)
    for tm in re.finditer(r"(?:" + EXCH + r")([^.]{0,120}?)under the (?:trading )?symbols?\s*[“\"'‘]?([A-Z]{1,5})\b", t):
        if tm.group(3) not in NOT_TICKER and not other.search(tm.group(2)):
            return tm.group(3), tm.group(1)
    for tm in re.finditer(r"under the (?:trading )?symbols?\s*[“\"'‘]?([A-Z]{1,5})\b([^.]{0,80}?)" + EXCH, t):
        if tm.group(1) not in NOT_TICKER and not other.search(tm.group(2)):
            return tm.group(1), tm.group(3)
    return None, None


def cover_ticker(c, cik, max_docs=4):
    """Ticker of a delisted company: 10-Ks from newest to oldest (in the latest ones the stock may no longer trade)."""
    p = RAW / "SEC" / "submissions" / f"{cik}.json"
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))["filings"]["recent"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None, None
    tenk = sorted([(d, a, doc) for f, d, a, doc in zip(rec["form"], rec["filingDate"], rec["accessionNumber"],
                                                        rec["primaryDocument"]) if f in ("10-K", "10-KT")],
                  reverse=True)
    for d, acc, doc in tenk[:max_docs]:
        tick, ex = ticker_in_text(doc_text(c, cik, acc, doc))
        if tick:
            return tick, ex
    return None, None


def public_float(c, cik):
    p = FLOAT_DIR / f"{cik}.json"
    if not p.exists():
        try:
            r = c.get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/EntityPublicFloat.json")
        except RuntimeError:
            return None
        p.write_text(r.text if r is not None else "{}", encoding="utf-8")
    try:
        u = json.loads(p.read_text(encoding="utf-8")).get("units", {}).get("USD", [])
    except json.JSONDecodeError:
        return None
    return {x["end"]: x["val"] for x in u}


def valid(rows, d0, d1, slack=30):
    """The name was valid somewhere within the trial window [d0, d1]."""
    s = pd.Timedelta(days=slack)
    vf, vt = pd.to_datetime(rows.valid_from), pd.to_datetime(rows.valid_to)
    return rows[(vf.isna() | (vf - s <= d1)) & (vt.isna() | (vt + s >= d0))]


def main():
    trials = pd.read_parquet(DATA / "trials.parquet")
    u = pd.read_parquet(DATA / "universe.parquet")
    names = name_table(u)
    by_norm = {k: v for k, v in names.groupby("name_norm")}
    choices = names.name_norm.tolist()
    sp = trials.groupby("sponsor").agg(n_trials=("nct_id", "size"), first=("first_posted", "min"),
                                       last=("last_posted", "max")).reset_index()
    sp["sponsor_norm"] = sp.sponsor.map(norm)
    rows = []
    for r in sp.itertuples():
        d0, d1 = pd.Timestamp(r.first), pd.Timestamp(r.last)
        base = dict(sponsor=r.sponsor, sponsor_norm=r.sponsor_norm, n_trials=r.n_trials)
        hits = by_norm.get(r.sponsor_norm)
        if hits is not None:
            ok = valid(hits, d0, d1)
            ciks = ok.cik.unique()
            if len(ciks) == 1:
                h = ok.iloc[0]
                rows.append(dict(base, cik=int(ciks[0]), method="exact", match_score=100.0, matched_name=h["name"],
                                 name_kind=h.kind, name_valid_from=h.valid_from, name_valid_to=h.valid_to))
                continue
            if len(ciks) > 1:
                rows.append(dict(base, cik=None, method="reject_ambiguous", match_score=0.0,
                                 matched_name=f"{len(ciks)} companies"))
                continue
            rows.append(dict(base, cik=None, method="reject_name_not_valid_then", match_score=0.0,
                             matched_name=hits.name.iloc[0]))
            continue
        res = process.extractOne(r.sponsor_norm, choices, scorer=fuzz.token_sort_ratio, score_cutoff=FUZZY_MIN)
        if res:
            h = names.iloc[res[2]]
            a, b = set(r.sponsor_norm.split()), set(h.name_norm.split())
            if a and len(a & b) / max(len(a), len(b)) >= 0.5:
                rows.append(dict(base, cik=int(h.cik), method="fuzzy", match_score=float(res[1]), matched_name=h["name"],
                                 name_kind=h.kind, name_valid_from=h.valid_from, name_valid_to=h.valid_to))
                continue
        rows.append(dict(base, cik=None, method="none", match_score=0.0))
    m = pd.DataFrame(rows)
    m["sic"] = m.cik.map(u.set_index("cik").sic.to_dict())
    m["status"] = m.apply(status, axis=1)
    m = apply_labels(m)
    enrich(m, u)
    m.to_parquet(DATA / "sponsors.parquet", index=False)
    write_review(m)
    report(m, trials)
    return m


HEALTH_SIC = lambda s: s is not None and str(s).isdigit() and (  # noqa: E731
    2830 <= int(s) <= 2839 or 3826 <= int(s) <= 3829 or 3840 <= int(s) <= 3851 or 5047 == int(s) or 5122 == int(s)
    or 8000 <= int(s) <= 8099 or 8730 <= int(s) <= 8734 or int(s) == 6770)  # 6770 — a SPAC before merging with a biotech


def status(r):
    """auto — only an exact match without trap signs; fuzzy ones — always manual review."""
    if pd.isna(r.cik):
        return "rejected" if str(r.method).startswith("reject") else "unmatched"
    if r.method != "exact":
        return "review"
    if len(r.sponsor_norm.split()) < 2 and norm_light(r.sponsor) != norm_light(r.matched_name):
        return "review"   # "Aspen USA Inc" and "ASPEN GROUP, INC." -> both "aspen"
    if not HEALTH_SIC(r.sic):
        return "review"   # the trial sponsor is a company outside pharma/biotech/medtech
    return "auto"


def apply_labels(m):
    if not LABELS.exists():
        return m
    lab = pd.read_csv(LABELS).dropna(subset=["label"]).drop_duplicates("sponsor", keep="last").set_index("sponsor")
    for i, r in m.iterrows():
        if r.sponsor in lab.index and pd.notna(r.cik) and int(lab.loc[r.sponsor, "cik"]) == int(r.cik):
            m.at[i, "status"] = "confirmed" if int(lab.loc[r.sponsor, "label"]) == 1 else "rejected_manual"
    return m


def enrich(m, u):
    """Ticker, exchange, listing period, float — for accepted and disputed matches."""
    c = sec_client()
    ui = u.set_index("cik")
    cols = dict(ticker=[], exchange=[], ticker_source=[], listed_from=[], listed_to=[], min_float=[], max_float=[])
    for r in m.itertuples():
        if pd.isna(r.cik) or r.status in ("rejected", "rejected_manual", "unmatched"):
            for k in cols:
                cols[k].append(None)
            continue
        x = ui.loc[int(r.cik)]
        ticks = [k for k in (x.tickers or "").split(",") if k] if isinstance(x.tickers, str) else []
        tick = next((k for k in ticks if not is_derivative(k)), ticks[0] if ticks else "")
        exch = (x.exchanges or "").split(",")[0] if isinstance(x.exchanges, str) else ""
        src = "edgar"
        on_exch_now = bool(re.search(r"nasdaq|nyse", exch or "", re.I))
        if not tick or not on_exch_now:
            # delisting or a move to OTC: the ticker and exchange are taken from a 10-K when the stock was still listed
            try:
                t2, e2 = cover_ticker(c, int(r.cik))
            except RuntimeError:
                t2, e2 = None, None
            if t2:
                tick, exch, src = t2, e2, "10-K"
            elif not tick:
                src = None
        fl = public_float(c, int(r.cik)) or {}
        cols["ticker"].append(tick or None)
        cols["exchange"].append(exch or None)
        cols["ticker_source"].append(src)
        cols["listed_from"].append(str((pd.Timestamp(x.first_10k) - pd.Timedelta(days=365)).date()))
        # form 25 is also filed when moving between exchanges — a delisting only if it is not on NYSE/Nasdaq now
        delist = x.last_delist_form if isinstance(x.last_delist_form, str) else None
        cols["listed_to"].append(None if on_exch_now else delist)
        vals = [v for d, v in fl.items() if d >= "2017-01-01"]
        cols["min_float"].append(min(vals) if vals else None)
        cols["max_float"].append(max(vals) if vals else None)
    for k, v in cols.items():
        m[k] = v
    m["on_exchange"] = m.exchange.fillna("").str.contains("nasdaq|nyse|new york", case=False)
    m["small"] = m.min_float.isna() | (m.min_float < CFG["universe"]["max_mcap_usd"])


def write_review(m):
    cols = ["sponsor", "n_trials", "method", "match_score", "matched_name", "cik", "ticker", "exchange", "status"]
    m[m.status == "review"][cols].sort_values("n_trials", ascending=False) \
        .to_csv(MATCH_DIR / "review_sponsors.csv", index=False, encoding="utf-8-sig")
    auto = m[m.status.isin(["auto", "confirmed"])]
    auto.sample(min(len(auto), 200), random_state=7)[cols] \
        .to_csv(MATCH_DIR / "review_auto_sample.csv", index=False, encoding="utf-8-sig")


def report(m, trials):
    th = CFG["thresholds"]
    ok = m[m.status.isin(["auto", "confirmed"])]
    usable = ok[ok.on_exchange & ok.small & ok.ticker.notna()]
    n_tr = trials[trials.sponsor.isin(usable.sponsor)]
    L = [f"# Stage 2 — sponsors and tickers ({TODAY})", "",
         f"Sponsors: {len(m)} ({len(trials)} trials).", "",
         "| Status | Sponsors | Trials |", "|---|---|---|"]
    for s, g in m.groupby("status"):
        L.append(f"| {s} | {len(g)} | {g.n_trials.sum()} |")
    L += ["", f"Accepted matches: {len(ok)} sponsors -> {ok.cik.nunique()} companies; methods {ok.method.value_counts().to_dict()}.",
          f"Of which NYSE/Nasdaq with a ticker and float < $10B in at least one year: **{usable.cik.nunique()} companies**, "
          f"{len(usable)} sponsors, {len(n_tr)} trials.",
          f"Delisted (form 25/15) among usable: {usable[usable.listed_to.notna()].cik.nunique()}; "
          f"ticker from a 10-K: {(usable.ticker_source == '10-K').sum()}.",
          f"Without a ticker (found neither in EDGAR nor on a cover): {ok.ticker.isna().sum()}; not on NYSE/Nasdaq: "
          f"{(ok.ticker.notna() & ~ok.on_exchange).sum()}; float ≥ $10B always: {(~ok.small).sum()}."]
    if LABELS.exists():
        lab = pd.read_csv(LABELS).dropna(subset=["label"])
        lab = lab[lab["sample"] == "auto"] if "sample" in lab else lab
        if len(lab):
            L += ["", f"**Precision on a random sample of automatic matches:** {lab.label.mean():.1%} (n = {len(lab)})."]
    n = usable.cik.nunique()
    L += ["", f"**Stage 2 criterion:** ≥ {th['stage2_min_companies']} companies with a ticker — {n} "
          f"({'met' if n >= th['stage2_min_companies'] else 'NOT met'}); precision ≥ 95% — see the labels."]
    (REPORTS / "stage2_sponsors.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
