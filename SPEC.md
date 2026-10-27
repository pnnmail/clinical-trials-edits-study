# Spec: TRIALS_PILOT — clinical trial record edits and biotech stocks

## Goal and hypothesis

Test whether quiet edits to clinical trial records on ClinicalTrials.gov
predict a drop in the sponsor's stock. Every record on ClinicalTrials.gov keeps
all of its versions. Companies must update dates, enrollment and status, and
such edits appear in the registry without a press release and with almost no
attention.

- **H1.** Bad edits (a completion date slip, an enrollment cut, a suspension)
  at small biotechs produce a negative abnormal return over the 5–20 trading
  days after the edit is posted.
- **H2.** The effect is stronger when the trial is the company's main asset
  (one or two late-stage programmes).
- **H0.** The market prices edits immediately, or they carry no information.

## Pilot scope

| Parameter | Value |
|---|---|
| Trials | interventional, phases 2, 2/3 and 3, industry sponsor |
| Companies | ticker on NYSE/NASDAQ, market cap up to $10B |
| Edit period | 2018 — now |
| Prices | daily, adjusted |
| Benchmark | XBI; IBB as a check |

Big pharma is excluded: one trial in a portfolio of a hundred programmes does
not move the price.

## Stage 0 — reconnaissance: how to get version history

The key question of the project: where to get past versions of records, and
with which dates. Decide before writing code. Check three routes and record in
`sources.md` what each gives:

1. ClinicalTrials.gov API v2 — current records in JSON. Does it return version
   history or only the latest version?
2. The Record History tab on a trial's page — a list of versions with dates and
   a diff of two versions. If the API gives no history, parse it from here.
3. AACT (the Duke Postgres copy of ClinicalTrials.gov) — daily snapshots and an
   archive. How deep do old snapshots go?

For each route: which fields exist in old versions, whether a version has a
posting date, request limits, how long a full collection takes.

**Edit date.** Each version has the date the sponsor submitted the change and
the date it passed QC and appeared on the site. The second one is needed — only
that one was visible to the market.

## Stage 1 — collecting history

1. Via API v2, get NCT numbers: interventional, phases 2–3, industry sponsor,
   record updated after 2018.
2. Keep only sponsors matched at stage 2 (stages 1 and 2 may be swapped to
   avoid downloading too much).
3. Download all versions of each NCT; store raw responses unchanged in
   `raw/{nct_id}/`.
4. Parse each version into `trial_versions`: nct_id, version, posted_date,
   status, phase, enrollment and its type (planned/actual), primary completion
   and completion dates, primary outcome text, number of sites, why_stopped,
   sponsor.

## Stage 2 — sponsors and tickers

1. Matching: the SEC reference plus Exhibit 21 subsidiaries, name
   normalisation, exact and fuzzy matching, manual review of borderline cases.
   Account for renames and mergers.
2. Importance: for each company on the event date, the number of active phase
   2–3 trials; `is_lead_asset` = at most two such programmes.
3. Size: market cap on the event date.

Result: `sponsors` (sponsor → CIK, ticker, match score) and match precision on a
manual sample (target ≥ 95%).

## Stage 3 — change detector

Compare each version with the previous one and turn differences into typed,
signed events.

| Event type | Condition | Expected sign |
|---|---|---|
| Date slip | primary_completion_date moved later by ≥ 90 days | − |
| Enrollment cut | planned enrollment reduced by ≥ 20% | − |
| Suspension | status became Suspended or Withdrawn | − |
| Early termination | status Terminated before the planned date | − |
| Endpoint change | primary_outcome text changed | − (to verify) |
| Site reduction | number of sites reduced by ≥ 25% | − |
| Early end of enrollment | Recruiting → Active, not recruiting ahead of plan | + |
| Date pulled in | primary_completion_date moved earlier | + |

Rules: edits of one trial posted on the same day form one event with several
types; a slip that only updates an already-passed planned date gets a separate
`stale_update` flag; for endpoint changes, review 50 cases by hand first; drop
events with a company 8-K or press release about the trial within [−2, +2]
days.

## Stage 4 — event study

CAR after the edit is posted, separately for each event type. Market model
estimated on [−250, −30], market XBI; check: return minus XBI. Day 0: the first
trading day after posted_date. Windows: [−5, −1], [0, +5], [0, +20], [0, +60].
Significance: t across events and BMP; clustering by date. Slices: type,
is_lead_asset, market-cap tercile, phase, size of the date slip. Filters: price
≥ $2, median daily dollar volume ≥ $500k, 250 days of history.

## Stopping criteria

The project closes at the first stage whose continuation condition fails.

| After stage | Continue if | Otherwise |
|---|---|---|
| 0 | versions with a posting date are obtainable for 2018 — now | close: no history, no project |
| 2 | ≥ 150 companies with a ticker, match precision ≥ 95% | close |
| 3 | ≥ 300 negative events without a press release nearby | close |
| 4 | CAR [0, +20] significant (\|t\| ≥ 2) for at least one type and stronger for the lead asset | close; keep the detector as a dataset |

## Technical requirements

Python 3.11+, data in Parquet, each stage runs separately and can be re-run.
ClinicalTrials.gov requests with pauses, at most 1–2 per second; SEC with a
User-Agent and at most 10 per second. Event thresholds (90 days, 20%, 25%) live
in `config.yaml` to test robustness. Each stage writes a report to `reports/`.
Watch for survivorship bias: delisted biotechs must stay in the sample, with
prices up to delisting.
