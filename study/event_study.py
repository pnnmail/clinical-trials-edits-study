"""Stage 4: CAR after an edit is posted on ClinicalTrials.gov, separately by event type.

Day 0 — the first trading day strictly after posted_date. Market model on [−250, −30], market XBI;
check — return minus XBI (and IBB). Windows [−5,−1], [0,+5], [0,+20], [0,+60].
Filters: the company is listed on day 0; close on day −1 ≥ $2; median daily dollar volume
in the estimation window ≥ $500k; ≥ 200 observations in the estimation window (of 221); market cap on day −1 ≤ $10B;
no 8-K/press release about the trial in [−2, +2] (near_press). stale_update date slips — separately.
One company, one day 0, one type — one observation.
Significance: t across events; BMP; t across same-date portfolios (clustering).
Slices: type; is_lead_asset (≤ 2 active phase 2–3 programmes at the company on the date); market cap (terciles);
phase; size of the date slip. Report: reports/stage4_event_study.md, chart stage4_car.png."""
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CFG, DATA, REPORTS, TODAY, get_logger  # noqa: E402

log = get_logger("event_study")
EST = tuple(CFG["thresholds"]["estimation_window"])
P = CFG["prices"]
MAXCAP = CFG["universe"]["max_mcap_usd"]
LEAD_MAX = CFG["universe"]["lead_asset_max_programs"]
WINDOWS = {"[-5,-1]": (-5, -1), "[0,+5]": (0, 5), "[0,+20]": (0, 20), "[0,+60]": (0, 60)}
PATH = range(-10, 61)
ACTIVE = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}
MAIN_TYPES = ["date_slip", "enroll_cut", "suspended", "terminated_early", "endpoint_change", "sites_cut", "enroll_shortfall",
              "enroll_done", "date_pull_in"]


def load():
    px = pd.read_parquet(DATA / "prices.parquet")
    ret = px.pivot_table(index="date", columns="ticker", values="adj_close").sort_index().pct_change(fill_method=None)
    close = px.pivot_table(index="date", columns="ticker", values="close").sort_index()
    dvol = (px.assign(dv=px.close * px.volume).pivot_table(index="date", columns="ticker", values="dv").sort_index())
    return ret, close, dvol


def active_programs(versions, trial_cik):
    """A function (cik, date) -> number of active phase 2–3 trials at the company."""
    v = versions[["nct_id", "posted_date", "status"]].dropna().sort_values("posted_date")
    v["cik"] = v.nct_id.map(trial_cik)
    by_cik = {c: g for c, g in v.groupby("cik")}

    def f(cik, d):
        g = by_cik.get(cik)
        if g is None:
            return np.nan
        last = g[g.posted_date <= d].groupby("nct_id").status.last()
        return int(last.isin(ACTIVE).sum())
    return f


def build(ret, close, dvol, cal):
    ev = pd.read_parquet(DATA / "trial_events.parquet")
    sp = pd.read_parquet(DATA / "sponsors.parquet").drop_duplicates("sponsor").set_index("sponsor")
    ev["cik"], ev["ticker"] = ev.sponsor.map(sp.cik), ev.sponsor.map(sp.ticker)
    ev["listed_from"], ev["listed_to"] = ev.sponsor.map(sp.listed_from), ev.sponsor.map(sp.listed_to)
    ev = ev.dropna(subset=["cik", "ticker"]).explode("types").rename(columns={"types": "type"})
    ev = ev[ev.type.isin(MAIN_TYPES)]
    versions = pd.read_parquet(DATA / "trial_versions.parquet")
    trials = pd.read_parquet(DATA / "trials.parquet")
    trial_cik = trials.set_index("nct_id").sponsor.map(sp.cik).to_dict()
    nprog = active_programs(versions, trial_cik)
    sh = pd.read_parquet(DATA / "shares.parquet")
    sh_by = {c: g.set_index("end").shares.sort_index() for c, g in sh.groupby("cik")}
    i0 = np.searchsorted(cal.values, pd.to_datetime(ev.posted_date).values.astype("datetime64[ns]"), side="right")
    ev = ev[i0 < len(cal) - max(PATH)].copy()
    ev["d0_idx"] = i0[i0 < len(cal) - max(PATH)]
    ev["day0"] = cal[ev.d0_idx.values]
    ev = ev.drop_duplicates(["cik", "day0", "type", "stale_update"])
    rows, drop = [], {}

    def dropped(k):
        drop[k] = drop.get(k, 0) + 1
    xbi, ibb = ret["XBI"], ret["IBB"]
    for r in ev.itertuples():
        t, d0 = r.ticker, r.d0_idx
        if t not in ret:
            dropped("no prices"); continue
        if isinstance(r.listed_to, str) and r.day0 > pd.Timestamp(r.listed_to):
            dropped("after delisting"); continue
        if d0 + EST[0] < 0:
            dropped("short history"); continue
        pre = close[t].iloc[d0 - 1]
        if not pre >= P["min_price"]:
            dropped("price < $2"); continue
        est = slice(d0 + EST[0], d0 + EST[1] + 1)
        if not dvol[t].iloc[est].median() >= P["min_median_dollar_volume"]:
            dropped("turnover < $500k"); continue
        y, x = ret[t].iloc[est], xbi.iloc[est]
        ok = y.notna() & x.notna()
        if ok.sum() < 200:
            dropped("short history"); continue
        s = sh_by.get(int(r.cik))
        mcap = np.nan
        if s is not None and len(s[s.index <= cal[d0 - 1]]):
            mcap = s[s.index <= cal[d0 - 1]].iloc[-1] * pre
        if mcap > MAXCAP:
            dropped("market cap > $10B"); continue
        if r.near_press:
            dropped("8-K/press release nearby"); continue
        b, a = np.polyfit(x[ok], y[ok], 1)
        sigma = (y[ok] - (a + b * x[ok])).std(ddof=2)
        win = slice(d0 + min(PATH), d0 + max(PATH) + 1)
        ar = (ret[t].iloc[win] - (a + b * xbi.iloc[win])).values
        ar_x = (ret[t].iloc[win] - xbi.iloc[win]).values
        ar_i = (ret[t].iloc[win] - ibb.iloc[win]).values
        rel = np.array(list(PATH))
        n = nprog(int(r.cik), r.posted_date)
        row = dict(type=r.type, nct_id=r.nct_id, ticker=t, cik=r.cik, day0=r.day0, posted_date=r.posted_date,
                   phase=r.phase, stale=bool(r.stale_update), shift=getattr(r, "pcd_shift_days", np.nan), mcap=mcap,
                   n_programs=n, is_lead_asset=(n <= LEAD_MAX) if pd.notna(n) else np.nan, sigma=sigma)
        for name, (s0, s1) in WINDOWS.items():
            m = (rel >= s0) & (rel <= s1)
            row[f"car{name}"] = np.nansum(ar[m])
            row[f"scar{name}"] = np.nansum(ar[m]) / (sigma * np.sqrt(m.sum()))
            row[f"xbi{name}"] = np.nansum(ar_x[m])
            row[f"ibb{name}"] = np.nansum(ar_i[m])
            # without the intercept a: for small biotechs a run-up in the estimation window gives a large a and an "expected" rise
            row[f"beta{name}"] = np.nansum((ret[t].iloc[win] - b * xbi.iloc[win]).values[m])
        row["path"] = np.nancumsum(ar)
        rows.append(row)
    return pd.DataFrame(rows), drop


def stats(df, col, scol=None):
    x = df[col].dropna()
    n = len(x)
    if n < 5:
        return dict(n=n)
    o = dict(n=n, mean=x.mean(), median=x.median(), neg=(x < 0).mean(), t=x.mean() / (x.std() / np.sqrt(n)))
    if scol in df:
        s = df[scol].dropna()
        o["t_bmp"] = s.mean() / (s.std() / np.sqrt(len(s)))
    bd = df.groupby("day0")[col].mean().dropna()
    if len(bd) >= 5:
        o["t_date"] = bd.mean() / (bd.std() / np.sqrt(len(bd)))
    return o


def winsor(df, col, q=0.01):
    """A copy with CARs trimmed at the 1st and 99th percentiles (robustness to single outliers)."""
    d = df.copy()
    lo, hi = d[col].quantile(q), d[col].quantile(1 - q)
    d[col] = d[col].clip(lo, hi)
    return d


def fmt(s):
    if s.get("n", 0) < 5:
        return f"| {s.get('n', 0)} | — | — | — | — | — | — |"
    return (f"| {s['n']} | {s['mean']:+.2%} | {s['median']:+.2%} | {s['neg']:.0%} | {s['t']:+.2f} | "
            f"{s.get('t_bmp', np.nan):+.2f} | {s.get('t_date', np.nan):+.2f} |")


def main():
    ret, close, dvol = load()
    cal = pd.DatetimeIndex(ret.index)
    df, drop = build(ret, close, dvol, cal)
    df.drop(columns=["path"]).to_parquet(DATA / "car.parquet", index=False)
    plot(df)
    report(df, drop)


def plot(df):
    fig, ax = plt.subplots(figsize=(9, 5))
    x = list(PATH)
    for t in ["date_slip", "enroll_cut", "suspended", "terminated_early", "endpoint_change", "enroll_done"]:
        g = df[(df.type == t) & ~df.stale]
        if len(g) >= 20:
            ax.plot(x, np.vstack(g.path.values).mean(axis=0) * 100, label=f"{t} (n={len(g)})")
    ax.axvline(0, color="gray", lw=0.8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("trading days relative to day 0 (the first day after the edit was posted)")
    ax.set_ylabel("mean CAR from day −10, %")
    ax.set_title("ClinicalTrials.gov edits: CAR by type (market model, XBI)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(REPORTS / "stage4_car.png", dpi=130)


def report(df, drop):
    th = CFG["thresholds"]["stage4_min_abs_t"]
    hdr = ["| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |", "|---|---|---|---|---|---|---|---|"]
    L = [f"# Stage 4 — event study ({TODAY})", "",
         f"Observations (company × day 0 × type): **{len(df)}**. Dropped: {drop}.", "", "![CAR](stage4_car.png)", ""]
    verdict = []
    for t in MAIN_TYPES:
        for stale in (False, True):
            g = df[(df.type == t) & (df.stale == stale)]
            if t != "date_slip" and stale:
                continue
            if len(g) < 5:
                continue
            title = t + (" (stale_update — overdue date)" if stale else "")
            L += [f"## {title}", ""] + hdr
            for w in WINDOWS:
                L.append(f"| {w} " + fmt(stats(g, f"car{w}", f"scar{w}")))
            L.append(f"| [0,+20] without the intercept (β·XBI) " + fmt(stats(g, "beta[0,+20]")))
            L.append(f"| [0,+20] 1% winsorised " + fmt(stats(winsor(g, "car[0,+20]"), "car[0,+20]")))
            L.append(f"| [0,+20] minus XBI " + fmt(stats(g, "xbi[0,+20]")))
            L.append(f"| [0,+20] minus IBB " + fmt(stats(g, "ibb[0,+20]")))
            s = stats(g, "car[0,+20]")
            la, nl = stats(g[g.is_lead_asset == True], "car[0,+20]"), stats(g[g.is_lead_asset == False], "car[0,+20]")  # noqa: E712
            L += ["", f"is_lead_asset: yes — {fmt(la)}", f"is_lead_asset: no — {fmt(nl)}", ""]
            robust = (abs(stats(g, "beta[0,+20]").get("t", 0)) >= th
                      and abs(stats(winsor(g, "car[0,+20]"), "car[0,+20]").get("t", 0)) >= th)
            L.append(f"Robustness of [0,+20] (significant both without the intercept and after winsorising): "
                     f"{'yes' if robust else 'no'}.")
            L.append("")
            if not stale:
                sig = abs(s.get("t", 0)) >= th
                stronger = la.get("n", 0) >= 5 and nl.get("n", 0) >= 5 and abs(la.get("mean", 0)) > abs(nl.get("mean", 0)) \
                    and np.sign(la.get("mean", 0)) == np.sign(s.get("mean", 1))
                verdict.append((t, s, sig, stronger, la, nl, robust))
    # slices for negative types together
    neg = df[df.type.isin(["date_slip", "enroll_cut", "suspended", "terminated_early", "sites_cut"]) & ~df.stale].copy()
    if len(neg) >= 30:
        L += ["## Slices (negative types without stale_update, CAR [0,+20])", "", "| Slice | Group | N | Mean | t |",
              "|---|---|---|---|---|"]
        neg["cap_q"] = pd.qcut(neg.mcap, 3, labels=["small", "mid", "large"]) if neg.mcap.notna().sum() >= 15 else np.nan
        for col, name in (("cap_q", "market cap"), ("phase", "phase"), ("is_lead_asset", "lead asset")):
            for v, g in neg.groupby(col, observed=True):
                s = stats(g, "car[0,+20]")
                L.append(f"| {name} | {v} | {s['n']} | {s.get('mean', np.nan):+.2%} | {s.get('t', np.nan):+.2f} |")
        sl = df[(df.type == "date_slip") & ~df.stale].copy()
        if len(sl) >= 15:
            sl["sz"] = pd.cut(sl["shift"], [89, 180, 365, 100000], labels=["90–180 d.", "181–365", "> 365"])
            for v, g in sl.groupby("sz", observed=True):
                s = stats(g, "car[0,+20]")
                L.append(f"| slip size | {v} | {s['n']} | {s.get('mean', np.nan):+.2%} | {s.get('t', np.nan):+.2f} |")
        L.append("")
    ok = [v for v in verdict if v[2] and v[3] and v[1].get("mean", 0) < 0]
    ok_robust = [v for v in ok if v[6]]
    L += ["## Verdict on the stage 4 criterion", "",
          f"Condition: CAR [0,+20] is significant (|t| ≥ {th}) for at least one negative type and stronger for is_lead_asset.", ""]
    for t, s, sig, stronger, la, nl, robust in verdict:
        L.append(f"- {t}: [0,+20] {s.get('mean', np.nan):+.2%}, t = {s.get('t', np.nan):+.2f} — "
                 f"{'significant' if sig else 'not significant'}; for the lead asset {la.get('mean', np.nan):+.2%} vs "
                 f"{nl.get('mean', np.nan):+.2%} — {'stronger' if stronger else 'not stronger'}; "
                 f"robust: {'yes' if robust else 'no'}.")
    L += ["", f"**Spec result: {'condition met (' + ', '.join(v[0] for v in ok) + ')' if ok else 'condition NOT met'}"
          f"{'; robust: ' + (', '.join(v[0] for v in ok_robust) or 'none') if ok else ''}.**"]
    (REPORTS / "stage4_event_study.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
