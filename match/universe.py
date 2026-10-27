"""Stage 2, step 1: the universe of companies, including delisted ones.
Everyone who filed a 10-K from 2018 to now (EDGAR quarterly master.idx), + EDGAR cards (submissions):
name, former names with dates, SIC, EIN, current tickers and exchanges, 10-K dates, delisting forms (25/15).
Result: data/universe.parquet. Cache: raw/SEC/master, raw/SEC/submissions."""
import gzip
import io
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, PERIOD_START, RAW, TODAY, get_logger, sec_client  # noqa: E402

log = get_logger("universe")
SEC = RAW / "SEC"
MASTER, SUB = SEC / "master", SEC / "submissions"
for d in (MASTER, SUB):
    d.mkdir(parents=True, exist_ok=True)
WARN_SUB = Path(os.environ.get("WARN_SUBMISSIONS_DIR", "../warn-notices-study/raw/SEC/submissions"))  # cards already downloaded by a sibling project, if any
TENK = {"10-K", "10-K405", "10-KT", "10-K/A"}
DELIST = {"25", "25-NSE", "15-12B", "15-12G", "15-15D"}


def quarters():
    y, q = PERIOD_START.year, 1
    end = pd.Timestamp(TODAY)
    while (y, q) <= (end.year, (end.month - 1) // 3 + 1):
        yield y, q
        y, q = (y, q + 1) if q < 4 else (y + 1, 1)


def tenk_filers(c):
    rows = []
    for y, q in quarters():
        p = MASTER / f"{y}Q{q}.idx.gz"
        if not p.exists() or (y, q) == list(quarters())[-1]:
            r = c.get(f"https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/master.gz")
            if r is None:
                continue
            p.write_bytes(r.content)
        txt = gzip.decompress(p.read_bytes()).decode("latin-1")
        for line in txt.splitlines():
            parts = line.split("|")
            if len(parts) == 5 and parts[2] in TENK:
                rows.append((int(parts[0]), parts[1], parts[3]))
        log.info("%dQ%d: total 10-K rows %d", y, q, len(rows))
    df = pd.DataFrame(rows, columns=["cik", "name_idx", "date"])
    return df.groupby("cik").agg(name_idx=("name_idx", "last"), first_10k=("date", "min"), last_10k=("date", "max")).reset_index()


def submissions(c, cik):
    p = SUB / f"{cik}.json"
    if not p.exists():
        w = WARN_SUB / f"{cik}.json"
        if w.exists():
            shutil.copy(w, p)
        else:
            try:
                r = c.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
            except RuntimeError as e:  # one card must not break the build; it will be downloaded on a re-run
                log.warning("cik %s: %s", cik, e)
                return {}
            p.write_bytes(r.content if r is not None else b"{}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def summarize(cik, s):
    if not s:
        return dict(cik=cik)
    rec = s.get("filings", {}).get("recent", {})
    forms = list(zip(rec.get("form", []), rec.get("filingDate", []), rec.get("accessionNumber", []),
                     rec.get("primaryDocument", [])))
    tenk = [f for f in forms if f[0] in TENK and not f[0].endswith("/A")]
    delist = sorted(d for f, d, *_ in forms if f in DELIST)
    last10k = max(tenk, key=lambda f: f[1]) if tenk else None
    return dict(cik=cik, name=s.get("name"), former_names=json.dumps(s.get("formerNames") or []),
                sic=s.get("sic"), sic_desc=s.get("sicDescription"), ein=s.get("ein"),
                state_inc=s.get("stateOfIncorporation"), tickers=",".join(s.get("tickers") or []),
                exchanges=",".join(x for x in (s.get("exchanges") or []) if x),
                last_10k_acc=last10k[2] if last10k else None, last_10k_doc=last10k[3] if last10k else None,
                last_10k_date=last10k[1] if last10k else None, first_delist_form=delist[0] if delist else None,
                last_delist_form=delist[-1] if delist else None)


def main():
    c = sec_client()
    filers = tenk_filers(c)
    log.info("filed a 10-K since %s: %d companies", PERIOD_START, len(filers))
    with ThreadPoolExecutor(max_workers=4) as ex:
        subs = list(ex.map(lambda k: summarize(k, submissions(c, k)), filers.cik))
    u = filers.merge(pd.DataFrame(subs), on="cik", how="left")
    u.to_parquet(DATA / "universe.parquet", index=False)
    log.info("universe: %d; with a current ticker %d; with a delisting form %d", len(u), (u.tickers.fillna("") != "").sum(),
             u.first_delist_form.notna().sum())


if __name__ == "__main__":
    main()
