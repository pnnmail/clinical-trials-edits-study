"""Stage 3: comparing neighbouring versions -> data/trial_events.parquet + the stage3_events.md report.

Types (thresholds — config.yaml/events):
  date_slip        primary_completion_date moved later by ≥ date_shift_days              (−)
  enroll_cut       planned (ESTIMATED -> ESTIMATED) enrollment cut by ≥ enrollment_cut_pct (−)
  suspended        status became SUSPENDED or WITHDRAWN                                  (−)
  terminated_early status became TERMINATED before the planned completion date           (−)
  endpoint_change  primary_outcome text changed for an ONGOING trial                     (− to check)
  sites_cut        number of sites decreased by ≥ sites_cut_pct (was ≥ sites_min)       (−)
  enroll_shortfall enrollment closed short: plan -> actual, actual ≤ 80% of plan (outside the spec) (−)
  enroll_done      RECRUITING -> ACTIVE_NOT_RECRUITING before the planned completion date (+)
Flag prev_ongoing=False: an edit to an already completed/terminated trial (analysed separately).
  date_pull_in     primary_completion_date moved earlier by ≥ date_shift_days           (+)
Flag stale_update: a date slip when the previous planned date had already passed at the time of the edit
(the sponsor simply updated an overdue record) — analysed separately.
Edits of one trial posted on the same day form one event with several types.
An event is dated by the posted_date of the new version (its appearance on the site)."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CFG, DATA, PERIOD_START, REPORTS, TODAY, get_logger  # noqa: E402

log = get_logger("detect")
E = CFG["events"]
SHIFT = E["date_shift_days"]
ENR = E["enrollment_cut_pct"]
SITES = E["sites_cut_pct"]
SITES_MIN = E.get("sites_min", 4)
NEG = {"date_slip", "enroll_cut", "suspended", "terminated_early", "endpoint_change", "sites_cut", "enroll_shortfall"}
ONGOING = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}


def to_date(s):
    """"2019-08" -> 15.08.2019 (mid-month), "2019-08-03" -> as is."""
    if not isinstance(s, str) or not s:
        return pd.NaT
    return pd.to_datetime(s + "-15", errors="coerce") if len(s) == 7 else pd.to_datetime(s, errors="coerce")


def norm_text(s):
    return re.sub(r"[\W_]+", " ", str(s or "").lower()).strip()


def diff(prev, cur):
    types, info = [], {}
    d0, d1 = to_date(prev.primary_completion_date), to_date(cur.primary_completion_date)
    if pd.notna(d0) and pd.notna(d1):
        shift = (d1 - d0).days
        info["pcd_shift_days"] = shift
        if shift >= SHIFT:
            types.append("date_slip")
            info["stale_update"] = bool(d0 < cur.posted_date)
        elif shift <= -SHIFT:
            types.append("date_pull_in")
    e0, e1 = prev.enrollment, cur.enrollment
    if pd.notna(e0) and pd.notna(e1) and e0 > 0 and prev.enrollment_type == "ESTIMATED" and cur.enrollment_type == "ESTIMATED":
        ch = (e1 - e0) / e0
        info["enroll_change"] = ch
        if ch <= -ENR:
            types.append("enroll_cut")
    # shortfall: enrollment closed (plan -> actual), actual ≤ (1 − threshold) of plan; this type is not in the spec — kept separate
    if pd.notna(e0) and pd.notna(e1) and e0 > 0 and prev.enrollment_type == "ESTIMATED" and cur.enrollment_type == "ACTUAL":
        ch = (e1 - e0) / e0
        info["enroll_change"] = ch
        if ch <= -ENR:
            types.append("enroll_shortfall")
    if cur.status != prev.status:
        if cur.status in ("SUSPENDED", "WITHDRAWN"):
            types.append("suspended")
        if cur.status == "TERMINATED" and (pd.isna(d0) or d0 > cur.posted_date):
            types.append("terminated_early")
        if prev.status == "RECRUITING" and cur.status == "ACTIVE_NOT_RECRUITING" and (pd.isna(d1) or d1 > cur.posted_date):
            types.append("enroll_done")
    # endpoint change — only for an ongoing trial: a manual review of 50 cases (detect/endpoint_review_50.csv)
    # showed that 44/50 edits are made after completion, when results are posted, and are rewordings
    if prev.status in ONGOING and norm_text(prev.primary_outcome) and norm_text(cur.primary_outcome) and \
            norm_text(prev.primary_outcome) != norm_text(cur.primary_outcome):
        types.append("endpoint_change")
    s0, s1 = prev.sites_count, cur.sites_count
    if s0 >= SITES_MIN and (s0 - s1) / s0 >= SITES:
        types.append("sites_cut")
        info["sites_change"] = (s1 - s0) / s0
    return types, info


def main():
    v = pd.read_parquet(DATA / "trial_versions.parquet").sort_values(["nct_id", "version"])
    rows = []
    for nct, g in v.groupby("nct_id"):
        g = g.reset_index(drop=True)
        for i in range(1, len(g)):
            prev, cur = g.iloc[i - 1], g.iloc[i]
            if pd.isna(cur.posted_date) or cur.posted_date < pd.Timestamp(PERIOD_START):
                continue
            types, info = diff(prev, cur)
            if types:
                rows.append(dict(nct_id=nct, version=int(cur.version), prev_version=int(prev.version),
                                 posted_date=cur.posted_date, submitted_date=cur.submitted_date,
                                 types=types, sponsor=cur.sponsor, phase=cur.phase, status_prev=prev.status,
                                 status=cur.status, why_stopped=cur.why_stopped,
                                 interventions=cur.get("interventions"), acronym=cur.get("acronym"),
                                 prev_ongoing=prev.status in ONGOING, **info))
    ev = pd.DataFrame(rows)
    if ev.empty:
        log.warning("no events")
        return
    # edits of one trial on one day — one event
    ev = (ev.groupby(["nct_id", "posted_date"], as_index=False)
          .agg({**{c: "last" for c in ev.columns if c not in ("nct_id", "posted_date", "types")},
                "types": lambda s: sorted({t for ts in s for t in ts})}))
    ev["negative"] = ev.types.map(lambda ts: bool(set(ts) & NEG))
    ev["positive"] = ev.types.map(lambda ts: bool(set(ts) & {"enroll_done", "date_pull_in"}))
    ev["stale_update"] = ev.get("stale_update", pd.Series(False, index=ev.index)).astype("boolean").fillna(False)
    ev.to_parquet(DATA / "trial_events.parquet", index=False)
    report(ev)


def report(ev):
    ex = ev.explode("types")
    ex["year"] = ex.posted_date.dt.year
    tab = pd.crosstab(ex.types, ex.year, margins=True, margins_name="Total")
    L = [f"# Stage 3 — events from edits ({TODAY})", "",
         f"Events (trial × posting day): **{len(ev)}**; negative {int(ev.negative.sum())}, "
         f"positive {int(ev.positive.sum())}. Date slips flagged stale_update: "
         f"{int((ex.types.eq('date_slip') & ex.stale_update).sum())}.", "",
         f"Thresholds: slip ≥ {SHIFT} d., enrollment cut ≥ {ENR:.0%}, site reduction ≥ {SITES:.0%} (was ≥ {SITES_MIN}).", "",
         "| Type | " + " | ".join(str(c) for c in tab.columns) + " |", "|---" * (len(tab.columns) + 1) + "|"]
    for t, r in tab.iterrows():
        L.append(f"| {t} | " + " | ".join(str(int(x)) for x in r.values) + " |")
    (REPORTS / "stage3_events.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
