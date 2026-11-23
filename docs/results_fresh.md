# Fresh-data comparison

The committed `data/prices.csv` snapshot is frozen. This page repeats the
comparison on a dated fresh download and publishes both tables side by side.
The fresh file is `data/fresh/prices_2026-11-23.csv`, downloaded on 2026-11-23
with `scripts/fetch_live_data.py`. Its SHA-256 is stored next to it and is
checked before the analysis.

The canonical snapshot is unchanged: 2,513 rows from 2016-11-22 to 2026-11-20.
The fresh file has 2,514 rows from 2016-11-22 to 2026-11-23. The only new
trading day is 2026-11-23.

## Data differences

Yahoo Finance revised the adjusted closes of the overlapping dates. The
revisions are tiny, but they are not zero.

| Ticker | Common dates | Max absolute revision | Max relative revision |
|---|---:|---:|---:|
| SPY | 2513 | 0.00021362 | 7.06e-05% |
| TLT | 2513 | 0.00018310 | 1.37e-04% |
| GLD | 2513 | 0.00000000 | 0.00e+00% |

3,790 of the 7,539 price cells differ by more than `1e-8`. The exact fresh CSV
is committed, because a new download on the same day can return different
decimals after another vendor revision.

## Main backtest at 95%

| Method | Violations snapshot | Violations fresh | Kupiec p snapshot | Kupiec p fresh | Christoffersen p snapshot | Christoffersen p fresh |
|---|---:|---:|---:|---:|---:|---:|
| Historical | 120 | 120 | 0.0538 | 0.0545 | 0.0017 | 0.0018 |
| Parametric | 114 | 114 | 0.1791 | 0.1808 | 0.0005 | 0.0005 |
| Monte Carlo | 114 | 114 | 0.1791 | 0.1808 | 0.0005 | 0.0005 |

The main three-method table does not change. The fresh sample adds one
forecast, so the expected count moves from 100.6 to 100.65 and the p-values
move only slightly. The conclusions are the same: the historical model is close
to failing Kupiec and all three fail independence.

## Conditional models at 95%

| Model | Violations snapshot | Violations fresh | Δ violations | Mean loss snapshot (bp) | Mean loss fresh (bp) | Δ mean loss (bp) | Rank snapshot | Rank fresh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GARCH(1,1) | 102 | 105 | 3 | 7.83 | 8.71 | +0.87 | 1 | 6 |
| EWMA | 102 | 102 | 0 | 8.08 | 8.09 | +0.01 | 2 | 1 |
| Historical 500 | 120 | 120 | 0 | 8.59 | 8.60 | +0.01 | 3 | 2 |
| Parametric adaptive | 109 | 109 | 0 | 8.62 | 8.63 | +0.01 | 4 | 3 |
| Historical adaptive | 116 | 116 | 0 | 8.63 | 8.64 | +0.01 | 5 | 4 |
| Parametric 500 | 114 | 114 | 0 | 8.63 | 8.64 | +0.01 | 6 | 5 |

The rank of every model except GARCH moves up by one. EWMA becomes the best
point estimate, Historical 500 becomes second and GARCH falls from first to
last. GARCH adds three violations and its mean quantile loss rises by 0.87 bp.
The other five models change by at most 0.01 bp.

## Conditional models at 99%

| Model | Violations snapshot | Violations fresh | Δ violations | Mean loss snapshot (bp) | Mean loss fresh (bp) | Δ mean loss (bp) | Rank snapshot | Rank fresh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GARCH(1,1) | 36 | 37 | 1 | 2.38 | 2.72 | +0.35 | 1 | 2 |
| EWMA | 42 | 42 | 0 | 2.56 | 2.56 | +0.00 | 2 | 1 |
| Historical 500 | 24 | 24 | 0 | 3.03 | 3.03 | +0.00 | 4 | 4 |
| Parametric adaptive | 40 | 40 | 0 | 3.12 | 3.12 | +0.00 | 6 | 6 |
| Historical adaptive | 27 | 27 | 0 | 2.92 | 2.92 | +0.00 | 3 | 3 |
| Parametric 500 | 40 | 40 | 0 | 3.09 | 3.09 | +0.00 | 5 | 5 |

At 99%, EWMA takes the first place from GARCH. The change is smaller than at
95%, but it is in the same direction. No model passes Kupiec and independence
at the same time in either sample. GARCH has 37 violations against 20.1
expected, so the lower mean loss is not a valid 99% model.

## Winner rule

The rule was fixed in `docs/methodology.md`: the best model wins clearly only
when the Holm-adjusted Diebold-Mariano p-value against the second-best is below
0.05.

| Dataset | Level | Best | Second | Holm p | Clear winner | Decision |
|---|---:|---|---|---:|---|---|
| Snapshot | 95% | GARCH(1,1) | EWMA | 0.7039 | False | No clear winner between GARCH(1,1) and EWMA |
| Snapshot | 99% | GARCH(1,1) | EWMA | 1.0000 | False | No clear winner between GARCH(1,1) and EWMA |
| Fresh, full | 95% | EWMA | Historical 500 | 1.0000 | False | No clear winner between EWMA and Historical 500 |
| Fresh, full | 99% | EWMA | GARCH(1,1) | 1.0000 | False | No clear winner between EWMA and GARCH(1,1) |
| Fresh, common period | 95% | EWMA | Historical 500 | 1.0000 | False | No clear winner between EWMA and Historical 500 |
| Fresh, common period | 99% | EWMA | GARCH(1,1) | 1.0000 | False | No clear winner between EWMA and GARCH(1,1) |

The point-estimate winner changes at both levels: GARCH becomes EWMA. The
pre-registered conclusion does not change: there is no clear winner. EWMA has
the lowest mean loss, but the corrected difference against the second model is
not significant.

The common-period rows repeat the analysis on the fresh prices cut at
2026-11-20. They are almost identical to the full fresh rows, so the flip is
caused by the price revisions, not by the extra trading day.

## GARCH fit diagnostics

The GARCH model is refit every 21 days. The diagnostics below refit it on the
same windows and count how often the optimizer returns an extreme solution.

| Dataset | Refits | Failed fits | alpha < 1e-8 | beta > 0.99 | Max omega / variance |
|---|---:|---:|---:|---:|---:|
| Snapshot | 96 | 2 | 2 | 0 | 6.652 |
| Fresh, full | 96 | 0 | 3 | 1 | 159.3 |
| Fresh, common period | 96 | 0 | 3 | 1 | 159.3 |

The canonical run has two failed fits and uses the pre-registered fallback. The
fresh run reports success on every fit, but three fits have `alpha < 1e-8` and
one has `beta > 0.99`. The worst fit puts `omega` at 159 times the sample
variance, which implies a constant volatility around 7.6% for that window. The
affected refits are dated 2025-01-28, 2025-02-27 and 2025-03-28.

The cause is numerical, not economic. A price revision of the order of
`1e-4` changes the likelihood surface enough for SLSQP to end in a different
local point. The GARCH point estimate was already fragile in `v1.0.0`: the
canonical run needed the fallback twice. The fresh data makes the fragility
visible in the ranking.

This does not invalidate the pre-registered comparison, because the protocol
fixed the optimizer and the fallback before the results. It does mean that the
GARCH first place in `v1.0.0` should not be read as a stable economic result.

## Expected Shortfall

At 95%, GARCH has a mean CVaR of 1.5165% on fresh data against 1.3492% on the
snapshot. The confidence interval widens to [1.3245%, 1.8136%]. The simulated
ES is almost unchanged, 1.4373% against 1.4394%, because the simulation
residuals absorb part of the variance spike. EWMA is stable: 1.3632% against
1.3629%, with a simulated ES of 1.5892% against 1.5888%.

At 99%, GARCH has a mean CVaR of 1.9708% against 1.7545%, and a simulated ES
of 2.0595% against 2.0611%. EWMA stays at 1.7614% and 2.3214%.

The CVaR jump is the same numerical problem: the degenerate refits produce a
volatility forecast far above the sample. The ES is less affected because the
filtered simulation rescales the residuals, but the interval is wider.

## Conclusion

- The committed snapshot does not change. The update command writes to
  `data/fresh` and verifies both checksums before and after.
- The main historical, parametric and Monte Carlo results are unchanged.
- The conditional point-estimate winner changes from GARCH(1,1) to EWMA at 95%
  and at 99%. The change is published.
- The formal winner rule still returns no clear winner at both levels. The
  corrected Diebold-Mariano p-values are 1.0000 in every fresh comparison.
- EWMA is the stable model in this test: its mean loss moves by 0.01 bp at 95%
  and 0.00 bp at 99%.
- GARCH is not stable. Tiny vendor revisions change the optimizer path and
  produce degenerate fits. The first place in `v1.0.0` was within that noise.
- The fresh sample adds one trading day. This is a data-revision stress test,
  not a long out-of-sample test. A longer fresh period is needed before
  changing the production model.

## Files

- `data/fresh/prices_2026-11-23.csv`
- `data/fresh/prices_2026-11-23.sha256`
- `docs/fresh/tables.md`
- `docs/fresh/comparison_fresh_95.csv`
- `docs/fresh/comparison_fresh_99.csv`
- `docs/fresh/comparison_common_95.csv`
- `docs/fresh/comparison_common_99.csv`
- `docs/fresh/conditional_summary_fresh.csv`
- `docs/fresh/conditional_summary_common.csv`
- `docs/fresh/conditional_dm_fresh.csv`
- `docs/fresh/conditional_dm_common.csv`
- `docs/fresh/main_comparison.csv`
- `docs/fresh/main_summary_fresh.csv`
- `docs/fresh/winners.csv`
- `docs/fresh/garch_diagnostics.csv`
- `docs/fresh/garch_diagnostics_summary.csv`
