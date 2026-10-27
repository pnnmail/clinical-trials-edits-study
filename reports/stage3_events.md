# Stage 3 — events from edits (2026-10-07)

Events (trial × posting day): **9582**; negative 7401, positive 3579. Date slips flagged stale_update: 2273.

Thresholds: slip ≥ 90 d., enrollment cut ≥ 20%, site reduction ≥ 25% (was ≥ 4).

| Type | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| date_pull_in | 133 | 142 | 144 | 158 | 190 | 197 | 199 | 208 | 124 | 1495 |
| date_slip | 405 | 481 | 518 | 537 | 570 | 524 | 437 | 368 | 280 | 4120 |
| endpoint_change | 223 | 245 | 271 | 271 | 311 | 279 | 279 | 270 | 187 | 2336 |
| enroll_cut | 21 | 17 | 29 | 33 | 33 | 33 | 23 | 17 | 23 | 229 |
| enroll_done | 214 | 240 | 265 | 199 | 274 | 305 | 252 | 242 | 200 | 2191 |
| enroll_shortfall | 119 | 122 | 127 | 128 | 194 | 186 | 143 | 132 | 79 | 1230 |
| sites_cut | 36 | 44 | 36 | 44 | 39 | 79 | 85 | 48 | 32 | 443 |
| suspended | 20 | 39 | 25 | 30 | 51 | 37 | 24 | 33 | 28 | 287 |
| terminated_early | 22 | 26 | 39 | 34 | 51 | 62 | 55 | 43 | 26 | 358 |
| Total | 1193 | 1356 | 1454 | 1434 | 1713 | 1702 | 1497 | 1361 | 979 | 12689 |

## Filter "8-K or press release about the trial within [−2, +2]"

Negative events: 7401. A company 8-K with the NCT number, a drug code or the trial acronym nearby: 320; news nearby: 38; news not checked (Google News answered 503, not re-requested): 1796.
**Without a press release nearby: 7047.** Stage 3 criterion (≥ 300) — met.

Endpoint change — only for ongoing trials (a manual review of 50 cases: detect/endpoint_review_50.csv, 7/50 substantive, 44/50 edits made after the trial was completed).
