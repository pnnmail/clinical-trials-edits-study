"""Stage 3: the filter "within [−2, +2] days of the edit's posting there was an 8-K or a company press release about this trial".

  8-K: EDGAR full-text search over the company's 8-Ks in the window: the NCT number, drug codes from the record
       (names with digits like "ABC-123"), the trial acronym;
  press release/news: Google News RSS search within ±3 days; a headline counts if it has the company
       name and (a drug code, the acronym, or the words trial/study/phase/topline/data).
Generic names (placebo, standard drugs without digits) are not searched — they give unrelated matches.
Result: columns near_8k, near_news, near_press (+ links) in data/trial_events.parquet."""
import re
import sys
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import html
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CFG, DATA, RAW, get_logger, sec_client  # noqa: E402
from match.normalize import norm  # noqa: E402

log = get_logger("press_filter")
FTS_DIR, NEWS_DIR = RAW / "SEC" / "fts", RAW / "NEWS"
for d in (FTS_DIR, NEWS_DIR):
    d.mkdir(parents=True, exist_ok=True)
NEWS_GAP = 8.0  # Google throttles frequent requests (503) — keep a pause
TRIAL_WORDS = r"(trial|study|phase|topline|data|results|enrollment|enrolment|discontinu|pause|halt|suspend)"


def drug_codes(interventions):
    """Drug codes (contain a digit: "ABBV-123", "LY3298176"), without placebo."""
    out = []
    for n in str(interventions or "").split(" | "):
        n = n.strip()
        if re.search(r"\d", n) and not re.search(r"placebo|saline|vehicle", n, re.I) and 3 <= len(n) <= 30:
            out.append(re.sub(r"\s*\(.*?\)", "", n))
    return list(dict.fromkeys(out))[:4]


_K8 = {}


def has_8k(cik, d0, d1):
    """Did the company file an 8-K in [d0, d1] — from the EDGAR card (raw/SEC/submissions), without requests."""
    if cik not in _K8:
        try:
            import json
            rec = json.loads((RAW / "SEC" / "submissions" / f"{cik}.json").read_text(encoding="utf-8"))["filings"]["recent"]
            _K8[cik] = pd.DatetimeIndex([pd.Timestamp(dd) for f, dd in zip(rec["form"], rec["filingDate"]) if f.startswith("8-K")])
        except (OSError, KeyError, ValueError):
            _K8[cik] = None  # no card — check via search
    k = _K8[cik]
    return True if k is None else bool(((k >= d0) & (k <= d1)).any())


def fts(c, cik, d0, d1, terms):
    q = " OR ".join(f'"{t}"' for t in terms)
    key = re.sub(r"[^\w]+", "_", f"{cik}_{d0.date()}_{q}")[:180]
    p = FTS_DIR / f"{key}.json"
    if not p.exists():
        r = c.get(f"https://efts.sec.gov/LATEST/search-index?q={quote(q)}&forms=8-K&dateRange=custom"
                  f"&startdt={d0.date()}&enddt={d1.date()}&ciks={cik:010d}")
        p.write_text(r.text if r is not None else "{}", encoding="utf-8")
    try:
        hits = pd.read_json(p, typ="series").get("hits", {}).get("hits", [])
    except ValueError:
        hits = []
    return [h["_source"].get("file_date") for h in hits]


class News:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = CFG["http"]["sec_user_agent"]
        self.last = 0.0
        self.blocked = False  # Google refused — skip the news check (no bypassing)
        self.cache_only = "--news-cache-only" in sys.argv  # only already downloaded responses, new ones are "not checked"

    def search(self, q, d0, d1):
        """A list of (date, headline, link), or None if the news could not be checked."""
        key = re.sub(r"[^\w]+", "_", f"{q}_{d0.date()}")[:180]
        p = NEWS_DIR / f"{key}.xml"
        if not p.exists():
            if self.blocked or self.cache_only:
                return None
            ok = False
            for i in range(2):
                wait = NEWS_GAP - (time.time() - self.last)
                if wait > 0:
                    time.sleep(wait)
                self.last = time.time()
                try:
                    r = self.s.get("https://news.google.com/rss/search", timeout=(10, 30),
                                   params=dict(q=f"{q} after:{d0.date()} before:{d1.date()}", hl="en-US", gl="US",
                                               ceid="US:en"))
                except requests.RequestException:
                    time.sleep(15)
                    continue
                if r.status_code == 200:
                    p.write_text(r.text, encoding="utf-8")
                    ok = True
                    break
                if r.status_code in (429, 503):
                    log.warning("Google News: HTTP %s — news check disabled until the next run", r.status_code)
                    self.blocked = True
                    return None
                time.sleep(30)
            if not ok:
                return None
        out = []
        for it in re.findall(r"<item>(.*?)</item>", p.read_text(encoding="utf-8"), re.S):
            t = html.unescape(re.search(r"<title>(.*?)</title>", it, re.S).group(1))
            d = pd.Timestamp(parsedate_to_datetime(re.search(r"<pubDate>(.*?)</pubDate>", it).group(1))).tz_convert(None)
            link = re.search(r"<link>(.*?)</link>", it, re.S)
            out.append((d.normalize(), t, link.group(1) if link else None))
        return out


def short(name):
    n = norm(name)
    n = re.sub(r"\b(holdings?|therapeutics|pharmaceuticals?|pharma|biosciences?|biotherapeutics|biopharma|bio|"
               r"technologies|medical|sciences|oncology|group|inc|corp|plc|ltd)\b", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n if len(n) >= 3 else norm(name)


def main():
    ev = pd.read_parquet(DATA / "trial_events.parquet")
    sp = pd.read_parquet(DATA / "sponsors.parquet").drop_duplicates("sponsor").set_index("sponsor")
    ev["cik"] = ev.sponsor.map(sp.cik)
    ev["company"] = ev.sponsor.map(sp.matched_name)
    # news is checked only where the event can enter the event study: the stock trades and the price ≥ $2
    # (stage 4 filters cut the rest; this halves the requests to Google)
    px = pd.read_parquet(DATA / "prices.parquet", columns=["date", "ticker", "close"])
    close = px.pivot_table(index="date", columns="ticker", values="close").sort_index()
    ev["ticker"] = ev.sponsor.map(sp.ticker)

    def tradable(r):
        if r.ticker not in close:
            return False
        s = close[r.ticker].loc[:r.posted_date].dropna()
        return len(s) > 0 and (r.posted_date - s.index[-1]).days <= 7 and s.iloc[-1] >= 2
    ev["check_news"] = ev.apply(tradable, axis=1)
    c, nw = sec_client(), News()
    near8, near_news, news_title = [], [], []
    for k, r in enumerate(ev.itertuples(), 1):
        d = pd.Timestamp(r.posted_date)
        terms = [r.nct_id] + drug_codes(r.interventions) + ([r.acronym] if isinstance(r.acronym, str) and len(r.acronym) >= 4 else [])
        hit8 = False
        # full-text search is needed only if the company filed any 8-K in the window (per the EDGAR card)
        if pd.notna(r.cik) and has_8k(int(r.cik), d - pd.Timedelta(days=2), d + pd.Timedelta(days=2)):
            try:
                hit8 = bool(fts(c, int(r.cik), d - pd.Timedelta(days=2), d + pd.Timedelta(days=2), terms))
            except RuntimeError as e:
                log.warning("fts %s: %s", r.nct_id, e)
        near8.append(hit8)
        # news: only for negative events (the filter is needed for them)
        hitn, title = False, None
        if r.negative and r.check_news and isinstance(r.company, str):
            co = short(r.company)
            extra = [t for t in terms[1:]]
            q = f'"{co}" ' + ("(" + " OR ".join(f'"{t}"' for t in extra) + " OR trial OR study)" if extra else "(trial OR study OR phase)")
            full = norm(r.company)  # "spectrum pharmaceuticals" — the short "spectrum" catches "Spectrum News"
            found = nw.search(q, d - pd.Timedelta(days=3), d + pd.Timedelta(days=3))
            if found is None:
                hitn = None  # news not checked
                found = []
            for dd, t, _ in found:
                if abs((dd - d).days) > 2:
                    continue
                tn = norm(t)
                has_code = any(re.search(r"\b" + re.escape(x) + r"\b", t, re.I) for x in extra)
                full_hit = re.search(r"\b" + re.escape(full) + r"\b", tn) and re.search(TRIAL_WORDS, t, re.I)
                short_hit = re.search(r"\b" + re.escape(co) + r"\b", tn) and has_code
                if full_hit or short_hit:
                    hitn, title = True, t
                    break
        near_news.append(hitn)
        news_title.append(title)
        if k % 200 == 0:
            log.info("%d/%d, 8-K nearby %d, news nearby %d", k, len(ev), sum(near8), sum(bool(x) for x in near_news))
    ev["near_8k"], ev["near_news"], ev["near_news_title"] = near8, near_news, news_title
    ev["near_news"] = ev.near_news.astype("boolean")
    ev["near_press"] = ev.near_8k | ev.near_news.fillna(False)  # unchecked news does not exclude the event
    ev.drop(columns=["company", "ticker"]).to_parquet(DATA / "trial_events.parquet", index=False)
    neg = ev[ev.negative]
    log.info("negative %d: 8-K nearby %d, news nearby %d, news not checked %d, clean (no press release) %d",
             len(neg), neg.near_8k.sum(), neg.near_news.fillna(False).sum(), neg.near_news.isna().sum(),
             (~neg.near_press).sum())


if __name__ == "__main__":
    main()
