"""Stage 1: raw versions raw/{nct}/v{N}.json.gz -> data/trial_versions.parquet + the stage1_versions.md report.
posted_date — statusModule.lastUpdatePostDateStruct (appearance on the site), submitted_date — lastUpdateSubmitDate."""
import gzip
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, RAW, REPORTS, TODAY, get_logger  # noqa: E402

log = get_logger("parse")


def g(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def parse_version(nct, v, j):
    s = j["study"]["protocolSection"]
    st, des = s.get("statusModule", {}), s.get("designModule", {})
    prim = g(s, "outcomesModule", "primaryOutcomes") or []
    return dict(
        nct_id=nct, version=v,
        posted_date=g(st, "lastUpdatePostDateStruct", "date"),
        submitted_date=st.get("lastUpdateSubmitDate"),
        status=st.get("overallStatus"),
        why_stopped=st.get("whyStopped"),
        phase=",".join(des.get("phases") or []),
        enrollment=g(des, "enrollmentInfo", "count"),
        enrollment_type=g(des, "enrollmentInfo", "type"),
        primary_completion_date=g(st, "primaryCompletionDateStruct", "date"),
        primary_completion_type=g(st, "primaryCompletionDateStruct", "type"),
        completion_date=g(st, "completionDateStruct", "date"),
        start_date=g(st, "startDateStruct", "date"),
        primary_outcome=" || ".join(f"{o.get('measure', '')} [{o.get('timeFrame', '')}]" for o in prim),
        n_primary_outcomes=len(prim),
        sites_count=len(g(s, "contactsLocationsModule", "locations") or []),
        interventions=" | ".join(sorted({i.get("name", "") for i in (g(s, "armsInterventionsModule", "interventions") or [])
                                         if i.get("type") in ("DRUG", "BIOLOGICAL", "GENETIC", "DEVICE", "COMBINATION_PRODUCT")})),
        acronym=g(s, "identificationModule", "acronym"),
        title=g(s, "identificationModule", "briefTitle"),
        sponsor=g(s, "sponsorCollaboratorsModule", "leadSponsor", "name"),
        sponsor_class=g(s, "sponsorCollaboratorsModule", "leadSponsor", "class"),
    )


def main():
    rows, bad = [], 0
    for d in sorted(RAW.glob("NCT*")):
        for f in d.glob("v*.json.gz"):
            try:
                j = json.loads(gzip.decompress(f.read_bytes()))
                rows.append(parse_version(d.name, int(f.name[1:].split(".")[0]), j))
            except (ValueError, KeyError, OSError) as e:
                bad += 1
                log.warning("%s: %s", f, e)
    df = pd.DataFrame(rows).sort_values(["nct_id", "version"])
    for c in ("posted_date", "submitted_date"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["post_lag_days"] = (df.posted_date - df.submitted_date).dt.days
    df.to_parquet(DATA / "trial_versions.parquet", index=False)
    report(df, bad)


def report(df, bad):
    n_tr = df.nct_id.nunique()
    per = df.groupby("nct_id").size()
    empty = {c: f"{df[c].isna().mean() if df[c].dtype != object else (df[c].isna() | (df[c] == '')).mean():.1%}"
             for c in ["posted_date", "status", "phase", "enrollment", "primary_completion_date", "primary_outcome",
                       "why_stopped", "sponsor"]}
    lag = df.post_lag_days.dropna()
    L = [f"# Stage 1 — trial versions ({TODAY})", "",
         f"Trials: **{n_tr}**, versions: **{len(df)}** (on average {per.mean():.1f} per record, median {per.median():.0f}); "
         f"unreadable files: {bad}.",
         f"Version period: {df.posted_date.min():%Y-%m-%d} — {df.posted_date.max():%Y-%m-%d}.", "",
         "Share of empty fields: " + ", ".join(f"{k} {v}" for k, v in empty.items()) + " (why_stopped is empty if not stopped).",
         "", f"Posting lag (posted − submitted): median {lag.median():.0f} d., p75 {lag.quantile(.75):.0f}, "
         f"p90 {lag.quantile(.9):.0f}, p99 {lag.quantile(.99):.0f}; > 7 days — {(lag > 7).mean():.0%}."]
    (REPORTS / "stage1_versions.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
