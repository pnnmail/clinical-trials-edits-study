"""Shared TRIALS_PILOT utilities: config, logs, paths, an SEC client (≤ 8 requests/s), a ClinicalTrials.gov client."""
import datetime as dt
import logging
import threading
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"
CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
TODAY = dt.date.today().isoformat()
PERIOD_START = dt.date.fromisoformat(str(CFG["period"]["start"]))
for d in (RAW, DATA, LOGS, REPORTS):
    d.mkdir(exist_ok=True)


def get_logger(name):
    log = logging.getLogger(name)
    if not log.handlers:
        log.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        for h in (logging.FileHandler(LOGS / f"{name}.log", encoding="utf-8"), logging.StreamHandler()):
            h.setFormatter(fmt)
            log.addHandler(h)
    return log


class RateClient:
    """requests.Session with a shared (thread-safe) rate limit and retries."""

    def __init__(self, user_agent, min_gap, timeout=(5, 30), name="http"):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = user_agent
        self.min_gap, self.timeout = min_gap, timeout
        self.lock, self.last = threading.Lock(), 0.0
        self.log = get_logger(name)

    def get(self, url, **kw):
        for i in range(5):
            with self.lock:
                wait = self.min_gap - (time.time() - self.last)
                if wait > 0:
                    time.sleep(wait)
                self.last = time.time()
            try:
                r = self.s.get(url, timeout=self.timeout, **kw)
            except requests.RequestException as e:
                self.log.warning("net %s: %s", url, type(e).__name__)
                time.sleep(1 + 2 * i)
                continue
            if r.status_code == 404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                self.log.warning("HTTP %s %s", r.status_code, url)
                time.sleep(10 * (i + 1))
                continue
            r.raise_for_status()
            return r
        raise RuntimeError(f"failed {url}")


def sec_client():
    return RateClient(CFG["http"]["sec_user_agent"], 1.0 / (CFG["http"]["sec_max_rps"] - 2), name="sec")


def ctgov_client():
    return RateClient(CFG["http"]["ctgov_user_agent"], CFG["http"]["ctgov_delay_sec"], timeout=(10, 60), name="ctgov")
