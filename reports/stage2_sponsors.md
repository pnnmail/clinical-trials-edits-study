# Stage 2 — sponsors and tickers (2026-10-06)

Sponsors: 5380 (34638 trials).

| Status | Sponsors | Trials |
|---|---|---|
| auto | 606 | 7469 |
| confirmed | 234 | 2421 |
| rejected | 12 | 47 |
| rejected_manual | 594 | 2795 |
| unmatched | 3934 | 21906 |

Accepted matches: 840 sponsors -> 765 companies; methods {'exact': 835, 'fuzzy': 5}.
Of which NYSE/Nasdaq with a ticker and float < $10B in at least one year: **717 companies**, 788 sponsors, 5841 trials.
Delisted (form 25/15) among usable: 265; ticker from a 10-K: 286.
Without a ticker (found neither in EDGAR nor on a cover): 16; not on NYSE/Nasdaq: 9; float ≥ $10B always: 28.

**Precision on a random sample of automatic matches:** 100.0% (n = 200).

**Stage 2 criterion:** ≥ 150 companies with a ticker — 717 (met); precision ≥ 95% — see the labels.

## Notes

- Manual labels (a sample of 200 automatic matches and a queue of 628 disputed ones) were made by Claude, file `match/labels.csv`
  (`labeled_by=claude`); the user's labels override them on the next run.
- Fuzzy matches are almost all false (Novartis -> ARS Pharmaceuticals, Sun Pharma -> Teva): 5 of 597 confirmed.
- The ticker of delisted companies comes from a 10-K filed while the stock was still listed (the 12(b) table; before 2019 — the phrase
  "under the symbol"); warrants/units are skipped. One SPAC unit ticker remained: Xynomic -> BCACU.
- "Delisting" = the company is not on NYSE/Nasdaq now; form 25 filed when moving between exchanges does not count as a delisting.
