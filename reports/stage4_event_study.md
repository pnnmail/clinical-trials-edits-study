# Stage 4 — event study (2026-10-07)

Observations (company × day 0 × type): **5265**. Dropped: {'turnover < $500k': 1514, 'price < $2': 2413, 'market cap > $10B': 820, 'after delisting': 703, '8-K/press release nearby': 304, 'short history': 166, 'no prices': 37}.

![CAR](stage4_car.png)

## date_slip

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 735 | +0.36% | -0.05% | 50% | +1.17 | +1.91 | +0.97 |
| [0,+5] | 735 | -0.32% | -0.61% | 54% | -0.81 | -0.45 | -0.37 |
| [0,+20] | 735 | -1.39% | -2.66% | 56% | -1.65 | -0.62 | -1.42 |
| [0,+60] | 735 | -4.01% | -4.22% | 57% | -2.64 | -0.78 | -2.88 |
| [0,+20] without the intercept (β·XBI) | 735 | +0.13% | -1.57% | 54% | +0.17 | +nan | +0.37 |
| [0,+20] 1% winsorised | 735 | -1.78% | -2.66% | 56% | -2.50 | +nan | -2.39 |
| [0,+20] minus XBI | 735 | +0.16% | -1.57% | 54% | +0.20 | +nan | +0.42 |
| [0,+20] minus IBB | 735 | +0.26% | -1.09% | 54% | +0.32 | +nan | +0.48 |

is_lead_asset: yes — | 133 | -4.87% | -4.18% | 59% | -2.21 | +nan | -2.36 |
is_lead_asset: no — | 602 | -0.62% | -2.37% | 56% | -0.69 | +nan | -0.50 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## date_slip (stale_update — overdue date)

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 916 | -0.42% | -0.82% | 56% | -1.38 | -1.03 | -1.15 |
| [0,+5] | 916 | -0.62% | -0.80% | 55% | -1.85 | -1.28 | -1.44 |
| [0,+20] | 916 | -1.09% | -1.64% | 55% | -1.42 | -0.31 | -0.92 |
| [0,+60] | 916 | -2.17% | -2.73% | 54% | -1.60 | -0.15 | -1.43 |
| [0,+20] without the intercept (β·XBI) | 916 | +0.26% | -0.15% | 51% | +0.35 | +nan | +0.71 |
| [0,+20] 1% winsorised | 916 | -1.77% | -1.64% | 55% | -3.00 | +nan | -2.23 |
| [0,+20] minus XBI | 916 | +0.48% | +0.00% | 50% | +0.66 | +nan | +1.00 |
| [0,+20] minus IBB | 916 | +0.43% | -0.22% | 51% | +0.58 | +nan | +0.88 |

is_lead_asset: yes — | 187 | -3.06% | -3.69% | 58% | -1.73 | +nan | -1.91 |
is_lead_asset: no — | 729 | -0.58% | -1.33% | 55% | -0.69 | +nan | -0.24 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## enroll_cut

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 99 | +0.70% | +0.10% | 48% | +0.83 | +0.54 | +0.81 |
| [0,+5] | 99 | +0.21% | +0.35% | 48% | +0.24 | +0.28 | +0.30 |
| [0,+20] | 99 | +4.13% | -0.54% | 51% | +1.33 | +1.30 | +1.36 |
| [0,+60] | 99 | +8.68% | -0.44% | 51% | +1.69 | +1.68 | +1.75 |
| [0,+20] without the intercept (β·XBI) | 99 | +4.21% | -0.46% | 53% | +1.40 | +nan | +1.44 |
| [0,+20] 1% winsorised | 99 | +3.46% | -0.54% | 51% | +1.31 | +nan | +1.34 |
| [0,+20] minus XBI | 99 | +4.33% | +0.24% | 48% | +1.42 | +nan | +1.47 |
| [0,+20] minus IBB | 99 | +5.12% | +0.15% | 49% | +1.66 | +nan | +1.71 |

is_lead_asset: yes — | 15 | +7.69% | +7.95% | 33% | +1.11 | +nan | +1.11 |
is_lead_asset: no — | 84 | +3.50% | -1.97% | 54% | +1.01 | +nan | +1.06 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## suspended

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 93 | -0.50% | +0.46% | 46% | -0.44 | -0.37 | -0.44 |
| [0,+5] | 93 | -1.60% | -0.77% | 59% | -1.30 | -0.59 | -1.28 |
| [0,+20] | 93 | -0.81% | -0.32% | 51% | -0.41 | +0.19 | -0.30 |
| [0,+60] | 93 | +7.36% | -3.62% | 56% | +1.44 | +1.79 | +1.47 |
| [0,+20] without the intercept (β·XBI) | 93 | -1.20% | -1.17% | 55% | -0.64 | +nan | -0.52 |
| [0,+20] 1% winsorised | 93 | -1.05% | -0.32% | 51% | -0.58 | +nan | -0.47 |
| [0,+20] minus XBI | 93 | -1.38% | -1.67% | 57% | -0.71 | +nan | -0.59 |
| [0,+20] minus IBB | 93 | -1.88% | -2.17% | 55% | -0.96 | +nan | -0.85 |

is_lead_asset: yes — | 33 | -0.68% | -4.84% | 52% | -0.18 | +nan | -0.18 |
is_lead_asset: no — | 60 | -0.87% | -0.07% | 50% | -0.40 | +nan | -0.24 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## terminated_early

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 123 | +0.66% | -0.04% | 50% | +0.77 | +1.05 | +0.53 |
| [0,+5] | 123 | -0.40% | -0.54% | 51% | -0.48 | -0.60 | -0.60 |
| [0,+20] | 123 | -0.02% | -2.29% | 58% | -0.01 | -0.01 | -0.10 |
| [0,+60] | 123 | +0.63% | -0.76% | 51% | +0.17 | +0.71 | +0.18 |
| [0,+20] without the intercept (β·XBI) | 123 | -0.73% | -2.01% | 59% | -0.34 | +nan | -0.42 |
| [0,+20] 1% winsorised | 123 | -0.78% | -2.29% | 58% | -0.49 | +nan | -0.63 |
| [0,+20] minus XBI | 123 | -0.37% | -2.80% | 57% | -0.17 | +nan | -0.23 |
| [0,+20] minus IBB | 123 | +0.93% | -0.91% | 53% | +0.43 | +nan | +0.40 |

is_lead_asset: yes — | 49 | -1.72% | -7.60% | 67% | -0.33 | +nan | -0.33 |
is_lead_asset: no — | 74 | +1.11% | -0.64% | 51% | +0.67 | +nan | +0.68 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## endpoint_change

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 939 | +0.56% | -0.25% | 52% | +1.70 | +2.88 | +1.34 |
| [0,+5] | 939 | -0.56% | -0.90% | 55% | -1.65 | -1.37 | -1.08 |
| [0,+20] | 939 | -1.03% | -1.50% | 54% | -1.45 | -1.02 | -1.30 |
| [0,+60] | 939 | -2.24% | -2.23% | 55% | -1.63 | -0.12 | -1.45 |
| [0,+20] without the intercept (β·XBI) | 939 | -0.00% | -1.16% | 54% | -0.00 | +nan | +0.02 |
| [0,+20] 1% winsorised | 939 | -1.11% | -1.50% | 54% | -1.73 | +nan | -1.56 |
| [0,+20] minus XBI | 939 | +0.48% | -0.77% | 53% | +0.70 | +nan | +0.68 |
| [0,+20] minus IBB | 939 | +0.71% | -0.95% | 52% | +0.99 | +nan | +0.89 |

is_lead_asset: yes — | 202 | -1.31% | -4.35% | 57% | -0.73 | +nan | -0.53 |
is_lead_asset: no — | 737 | -0.96% | -1.05% | 53% | -1.25 | +nan | -1.29 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## sites_cut

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 147 | -0.67% | -0.44% | 52% | -0.83 | -0.09 | -0.88 |
| [0,+5] | 147 | -0.28% | -0.02% | 50% | -0.32 | +0.23 | -0.35 |
| [0,+20] | 147 | +0.81% | +0.90% | 46% | +0.47 | +0.92 | +0.59 |
| [0,+60] | 147 | -0.18% | +0.39% | 50% | -0.05 | +0.77 | +0.13 |
| [0,+20] without the intercept (β·XBI) | 147 | +0.73% | +1.17% | 48% | +0.48 | +nan | +0.52 |
| [0,+20] 1% winsorised | 147 | +1.13% | +0.90% | 46% | +0.73 | +nan | +0.89 |
| [0,+20] minus XBI | 147 | +1.06% | +1.39% | 46% | +0.70 | +nan | +0.75 |
| [0,+20] minus IBB | 147 | +1.05% | +1.63% | 43% | +0.70 | +nan | +0.80 |

is_lead_asset: yes — | 31 | +5.04% | +1.80% | 42% | +1.08 | +nan | +0.97 |
is_lead_asset: no — | 116 | -0.32% | +0.81% | 47% | -0.18 | +nan | -0.18 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## enroll_shortfall

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 451 | -0.22% | -0.26% | 51% | -0.48 | -0.19 | -0.15 |
| [0,+5] | 451 | +0.16% | -0.05% | 51% | +0.29 | +0.77 | +0.32 |
| [0,+20] | 451 | +1.03% | -1.29% | 54% | +0.97 | +1.94 | +0.97 |
| [0,+60] | 451 | +2.16% | -0.33% | 51% | +1.08 | +2.61 | +0.99 |
| [0,+20] without the intercept (β·XBI) | 451 | +1.54% | -0.56% | 53% | +1.53 | +nan | +1.49 |
| [0,+20] 1% winsorised | 451 | +0.55% | -1.29% | 54% | +0.61 | +nan | +0.59 |
| [0,+20] minus XBI | 451 | +1.49% | -0.67% | 52% | +1.47 | +nan | +1.43 |
| [0,+20] minus IBB | 451 | +1.69% | -0.56% | 51% | +1.62 | +nan | +1.57 |

is_lead_asset: yes — | 125 | +3.05% | -4.60% | 59% | +1.07 | +nan | +1.04 |
is_lead_asset: no — | 326 | +0.25% | -0.44% | 52% | +0.26 | +nan | +0.19 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## enroll_done

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 845 | -0.22% | -0.35% | 52% | -0.57 | +0.04 | -0.41 |
| [0,+5] | 845 | +0.21% | -0.27% | 52% | +0.41 | +0.67 | +0.09 |
| [0,+20] | 845 | -0.08% | -0.11% | 51% | -0.10 | +0.49 | +0.19 |
| [0,+60] | 845 | -1.71% | -1.73% | 53% | -1.22 | -0.03 | -0.73 |
| [0,+20] without the intercept (β·XBI) | 845 | +0.92% | +0.54% | 48% | +1.21 | +nan | +1.55 |
| [0,+20] 1% winsorised | 845 | -0.19% | -0.11% | 51% | -0.30 | +nan | +0.25 |
| [0,+20] minus XBI | 845 | +1.05% | +0.75% | 47% | +1.39 | +nan | +1.73 |
| [0,+20] minus IBB | 845 | +1.04% | +0.61% | 47% | +1.34 | +nan | +1.86 |

is_lead_asset: yes — | 177 | -1.79% | -1.13% | 53% | -1.17 | +nan | -1.00 |
is_lead_asset: no — | 667 | +0.37% | +0.15% | 50% | +0.41 | +nan | +0.39 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## date_pull_in

| Window | N | Mean CAR | Median | Share < 0 | t | t BMP | t by date |
|---|---|---|---|---|---|---|---|
| [-5,-1] | 642 | +0.12% | -0.37% | 52% | +0.33 | +0.37 | +0.20 |
| [0,+5] | 642 | +0.07% | -0.23% | 51% | +0.17 | +0.37 | +0.27 |
| [0,+20] | 642 | +1.21% | -1.24% | 54% | +1.31 | +1.38 | +1.34 |
| [0,+60] | 642 | +1.30% | -0.52% | 51% | +0.86 | +1.93 | +1.20 |
| [0,+20] without the intercept (β·XBI) | 642 | +1.61% | -0.58% | 53% | +1.80 | +nan | +1.77 |
| [0,+20] 1% winsorised | 642 | +0.71% | -1.24% | 54% | +0.93 | +nan | +0.96 |
| [0,+20] minus XBI | 642 | +1.84% | -0.64% | 52% | +2.04 | +nan | +2.00 |
| [0,+20] minus IBB | 642 | +2.01% | -0.64% | 53% | +2.20 | +nan | +2.15 |

is_lead_asset: yes — | 181 | +1.92% | -2.54% | 59% | +0.87 | +nan | +0.86 |
is_lead_asset: no — | 461 | +0.93% | -0.69% | 53% | +0.98 | +nan | +0.99 |

Robustness of [0,+20] (significant both without the intercept and after winsorising): no.

## Slices (negative types without stale_update, CAR [0,+20])

| Slice | Group | N | Mean | t |
|---|---|---|---|---|
| market cap | small | 363 | +3.40% | +2.07 |
| market cap | mid | 362 | -2.68% | -2.36 |
| market cap | large | 362 | -2.03% | -2.25 |
| phase | PHASE1 | 18 | +0.86% | +0.18 |
| phase | PHASE1,PHASE2 | 258 | -1.80% | -1.42 |
| phase | PHASE2 | 496 | -1.45% | -1.59 |
| phase | PHASE2,PHASE3 | 54 | +1.74% | +0.50 |
| phase | PHASE3 | 371 | +1.37% | +0.93 |
| lead asset | False | 936 | -0.09% | -0.13 |
| lead asset | True | 261 | -1.85% | -1.08 |
| slip size | 90–180 d. | 194 | +0.61% | +0.31 |
| slip size | 181–365 | 293 | -2.62% | -2.17 |
| slip size | > 365 | 248 | -1.50% | -1.09 |

## Verdict on the stage 4 criterion

Condition: CAR [0,+20] is significant (|t| ≥ 2.0) for at least one negative type and stronger for is_lead_asset.

- date_slip: [0,+20] -1.39%, t = -1.65 — not significant; for the lead asset -4.87% vs -0.62% — stronger; robust: no.
- enroll_cut: [0,+20] +4.13%, t = +1.33 — not significant; for the lead asset +7.69% vs +3.50% — stronger; robust: no.
- suspended: [0,+20] -0.81%, t = -0.41 — not significant; for the lead asset -0.68% vs -0.87% — not stronger; robust: no.
- terminated_early: [0,+20] -0.02%, t = -0.01 — not significant; for the lead asset -1.72% vs +1.11% — stronger; robust: no.
- endpoint_change: [0,+20] -1.03%, t = -1.45 — not significant; for the lead asset -1.31% vs -0.96% — stronger; robust: no.
- sites_cut: [0,+20] +0.81%, t = +0.47 — not significant; for the lead asset +5.04% vs -0.32% — stronger; robust: no.
- enroll_shortfall: [0,+20] +1.03%, t = +0.97 — not significant; for the lead asset +3.05% vs +0.25% — stronger; robust: no.
- enroll_done: [0,+20] -0.08%, t = -0.10 — not significant; for the lead asset -1.79% vs +0.37% — stronger; robust: no.
- date_pull_in: [0,+20] +1.21%, t = +1.31 — not significant; for the lead asset +1.92% vs +0.93% — stronger; robust: no.

**Spec result: condition NOT met.**
