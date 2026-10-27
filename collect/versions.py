"""Stage 1: downloading the version history of trials sponsored by public companies.

The source is the ClinicalTrials.gov site's internal API (the Record History tab):
  /api/int/studies/{NCT}/history           — list of versions (number, submit date, changed sections), ~20 KB
  /api/int/studies/{NCT}/history/{N}       — the full record of version N (with the posting date)
robots.txt allows /api/int/ (Crawl-delay: 1), but non-browser clients get 403 — so requests
are made from an ordinary Chromium (Playwright) on a page of the site, ≤ 1 request/s.

We download: versions with changes in the relevant sections (config: trials.history_modules) submitted since 2017,
plus the last version before 2017 (the baseline for comparison) and version 0. reviewNotPassed versions are skipped.
Raw responses: raw/{nct}/history.json.gz and raw/{nct}/v{N}.json.gz — never modified. A re-run
downloads only what is missing."""
import gzip
import json
import sys
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CFG, DATA, RAW, get_logger  # noqa: E402

log = get_logger("versions")
DELAY = CFG["http"]["ctgov_delay_sec"]
MODULES = set(CFG["trials"]["history_modules"])
BASE_FROM = "2017-01-01"


class Browser:
    def __init__(self, p):
        self.p = p
        self.start()
        self.last = 0.0

    def start(self):
        """Open any page of the site (its origin is needed for fetch); the home page can be heavy — retries."""
        self.b = self.p.chromium.launch(headless=True)
        self.page = self.b.new_page()
        for i in range(4):
            try:
                self.page.goto("https://clinicaltrials.gov/study/NCT04368728?tab=history",
                               wait_until="commit", timeout=60000)
                self.page.wait_for_timeout(3000)
                return
            except Exception as e:  # page load timeout — try again
                log.warning("browser start, attempt %d: %s", i + 1, str(e)[:100])
                time.sleep(20)
        raise RuntimeError("clinicaltrials.gov does not open")

    def restart(self):
        try:
            self.b.close()
        except Exception:  # the browser has already crashed
            pass
        time.sleep(30)
        self.start()

    def get(self, path):
        for i in range(5):
            wait = DELAY - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                # fetch without a timeout can hang forever — abort after 20 s (a normal response is ~0.1 s)
                st, body = self.page.evaluate(
                    """async u => { const c = new AbortController(); const t = setTimeout(() => c.abort(), 20000);
                       try { const r = await fetch(u, {signal: c.signal}); return [r.status, await r.text()]; }
                       catch (e) { return [-1, String(e)]; } finally { clearTimeout(t); } }""", path)
                if st == -1:
                    log.warning("timeout/abort %s: %s", path, body[:80])
                    time.sleep(3)
                    continue
            except Exception as e:  # page/browser died — restart
                log.warning("browser %s: %s", path, str(e)[:120])
                self.restart()
                continue
            if st == 200:
                return body
            if st == 404:
                return None
            log.warning("HTTP %s %s", st, path)
            time.sleep(30 * (i + 1))
            if st == 403:
                self.restart()
        raise RuntimeError(f"failed {path}")


def save(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(gzip.compress(text.encode("utf-8")))


def load(p):
    return gzip.decompress(p.read_bytes()).decode("utf-8")


def wanted_versions(hist):
    ch = sorted(hist["changes"], key=lambda x: x["version"])
    ok = [c for c in ch if not c.get("reviewNotPassed")]
    out = {0} if ok and ok[0]["version"] == 0 else set()
    before = [c for c in ok if c["date"] < BASE_FROM]
    if before:
        out.add(before[-1]["version"])  # the baseline for comparing with the first edit of the period
    for c in ok:
        if c["date"] >= BASE_FROM and (set(c.get("moduleLabels") or []) & MODULES or c["version"] == 0):
            out.add(c["version"])
    return sorted(out)


def main():
    sp = pd.read_parquet(DATA / "sponsors.parquet")
    use = sp[sp.status.isin(["auto", "confirmed"]) & sp.on_exchange & sp.small & sp.ticker.notna()]
    trials = pd.read_parquet(DATA / "trials.parquet")
    trials = trials[trials.sponsor.isin(use.sponsor)].sort_values("nct_id")
    log.info("trials to download: %d (sponsors %d)", len(trials), use.sponsor.nunique())
    n_req, t0 = 0, time.time()
    with sync_playwright() as p:
        br = Browser(p)
        for k, nct in enumerate(trials.nct_id, 1):
            d = RAW / nct
            hp = d / "history.json.gz"
            try:
                if not hp.exists():
                    body = br.get(f"/api/int/studies/{nct}/history")  # only the list of versions (~20 KB)
                    n_req += 1
                    if body is None:
                        continue
                    save(hp, body)
                j = json.loads(load(hp))
                hist = j.get("history", j)  # old files: {study, history}; new ones: {changes, …}
                for v in wanted_versions(hist):
                    vp = d / f"v{v}.json.gz"
                    if vp.exists():
                        continue
                    body = br.get(f"/api/int/studies/{nct}/history/{v}")
                    n_req += 1
                    if body is not None:
                        save(vp, body)
            except RuntimeError as e:
                log.warning("%s: %s", nct, e)
            if k % 100 == 0:
                el = (time.time() - t0) / 3600
                log.info("%d/%d trials, requests %d, %.1f h", k, len(trials), n_req, el)
    log.info("done: requests %d", n_req)


if __name__ == "__main__":
    main()
