# TRIALS_PILOT — stage 0: where to get version history

Reconnaissance date: 2026-10-06. Everything verified with live requests.

## Summary

| Route | Version history | Version posting date | Script access | Verdict |
|---|---|---|---|---|
| API v2 (`/api/v2/studies`) | **no**, current version only (`/history` → 404) | only for the current one | yes, freely | for selecting NCTs and current fields |
| Record History (`/api/int/…`) | **yes**, all versions, the full record of each | **yes**, `lastUpdatePostDate` in every version | browser only (Playwright); robots.txt allows `/api/int/` with Crawl-delay 1 | **main source** |
| AACT | only via monthly snapshots | the date of the last version in the snapshot | only after registration (free account) | fallback, not needed |

**Stage 0 criterion** ("there is a way to get versions with a posting date for 2018 — now"): **met.**

## Edit date: submission ≠ appearance on the site

Every version has two dates:
- `statusModule.lastUpdateSubmitDate` — when the sponsor submitted the edit;
- `statusModule.lastUpdatePostDateStruct.date` — when the edit passed QC and **appeared on the site**. That is what the market saw, so it is used as `posted_date`.

The gap can be large: for NCT04368728 the last edit was submitted on 03.03.2026 and posted on 25.03.2026 (22 days). Usually it is 1–3 days (version 7 of the same trial: submitted 21.07.2020, posted 23.07.2020).

In the version list (`history.changes`) the `date` field is the submission date (equal to `lastUpdateSubmitQcDate`), **not the posting date**. The posting date must be taken from the version's full record.

## 1. API ClinicalTrials.gov v2

- `https://clinicaltrials.gov/api/v2/studies/{NCT}` — the current record in JSON; `/api/v2/version` — API version 2.0.5, data updated daily.
- No history: `/api/v2/studies/{NCT}/history` → 404.
- Selection works: `filter.advanced=AREA[StudyType]INTERVENTIONAL AND AREA[Phase](PHASE2 OR PHASE3) AND AREA[LeadSponsorClass]INDUSTRY AND AREA[LastUpdatePostDate]RANGE[2018-01-01,MAX]` → **34,638** trials (of which phase 3 — 15,171). Pages of 1000, `pageToken`.
- No limits encountered; we keep ≤ 1–2 requests/s.

## 2. Record History — the site's internal API (main)

What the Record History tab calls (seen in the page's network requests):
- `GET /api/int/studies/{NCT}?history=true` → `{study, topics, history}`; `history.changes` is the list of versions: `version`, `date` (submission), `status`, `moduleLabels` (which sections changed), `reviewNotPassed`, `unpostedEvents`. ~2 MB (includes the full current record).
- `GET /api/int/studies/{NCT}/history/{N}` → `{studyVersion, study}` — **the full record of version N** in the same schema as API v2 (~50 KB).

Fields in old versions (checked on versions 0, 1, 7, 30 of NCT04368728 and version 0 of NCT03548935):
- `statusModule`: `overallStatus`, `primaryCompletionDateStruct` (date + ESTIMATED/ACTUAL), `completionDateStruct`, `startDateStruct`, `lastUpdateSubmitDate`, `lastUpdatePostDateStruct`, `whyStopped` (if any);
- `designModule`: `phases`, `enrollmentInfo` (`count`, `type` ESTIMATED/ACTUAL);
- `outcomesModule.primaryOutcomes` (text, time frame);
- `contactsLocationsModule.locations` (number of sites);
- `sponsorCollaboratorsModule.leadSponsor` (`name`, `class`).

All fields of the `trial_versions` table from the spec are present.

**Access.** A direct request from curl/requests → **403** (the site's protection cuts off non-browser clients), while `robots.txt` explicitly allows `/api/int/` ("to let SPA function properly") with `Crawl-delay: 1`. From Playwright (an ordinary Chromium, a `fetch` request from a page of the site) — 200. Plan: a collector via Playwright, ≤ 1 request/s, as robots.txt asks.

**Quirks:**
- versions with `reviewNotPassed: true` did not pass QC and never appeared on the site — exclude them;
- versions are numbered from 0; a large trial has dozens of versions (NCT04368728 — 53);
- volume: 1 + N requests per trial. Estimate: after selecting public companies under $10B, ~8–10k trials × 10–30 versions ≈ 100–250k requests ≈ **1.5–3 days** at 1 request/s. Raw responses ~50 KB — stored gzipped (lossless);
- speed-up: download only versions whose `moduleLabels` include Study Status / Study Design / Outcome Measures / Contacts/Locations (the rest are edits of descriptions, contacts etc.).

## 3. AACT (Duke/CTTI)

- Previously: monthly database snapshots and an archive of pipe-delimited files on the `/download` page. Now `/download` → 404, snapshots (`/snapshots`) are available only after logging in.
- Even with the archive: one snapshot a month — intermediate versions within a month are lost; one snapshot is gigabytes. Worse than route 2 for the pilot.
- If needed, a free registration at aact.ctti-clinicaltrials.org is required.

## Prices and survivorship bias

- **yfinance** — currently traded tickers only.
- **Alpaca Market Data** returns daily bars adjusted for splits and dividends **including delisted** tickers: CLVS (Clovis) — 2018-01-02 … 2022-12-20, SAGE — … 2025-07-30, AKRO, ATHA. → **the main price source**, yfinance — for cross-checking. XBI/IBB — from the same place.
- Careful: after delisting a symbol may go to another company → prices are taken only up to the delisting date (Form 25/15 in EDGAR).

## Tickers of delisted companies

- SEC `company_tickers.json` — current ones only. In the EDGAR card (`submissions`) delisted companies have `tickers: []` (Clovis).
- Alpaca's list of inactive securities (`/v2/assets?status=inactive`, 19,169 items, 16k of them OTC) does not contain the old tickers CLVS/SAGE/AKRO → unreliable for matching.
- Plan for stage 2: search for the sponsor by name in EDGAR, and take a delisted company's ticker from the cover of its last 10-K (the "Trading Symbol(s)" field, mandatory since 2019). Delistings before 2019 — by hand.

## Decision

- Main source of versions — Record History (`/api/int/…`) via Playwright, 1 request/s.
- NCT list and current fields — API v2.
- Stage order: **stage 2 first** (sponsors → tickers, including delisted), then download versions only for the relevant sponsors — saves 2/3 of the requests (the spec allows this).
- Prices — Alpaca (with delisted tickers), XBI/IBB — from the same place.
