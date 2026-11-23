# Design decisions

## D1. Positive-loss sign convention

**Decision.** VaR and CVaR are reported as positive losses. A VaR of 0.02 means
a one-day loss of 2% of portfolio value.

**Context.** Returns are naturally signed, but risk reports are easier to read
when a larger number always means more risk.

**Consequence.** The return quantile is -VaR. A normal VaR is
`-(mu + sigma z)`, not `mu + sigma z`. Every test and document follows this
convention.

## D2. Fixed 50/35/15 weights

**Decision.** SPY 50%, TLT 35%, GLD 15%, long-only, rebalanced daily.

**Context.** The project measures the risk of a fixed portfolio. It does not
optimize weights on the sample.

**Consequence.** The results are conditional on this allocation. A different
portfolio would produce different VaR, CVaR and violations. The weights are
documented in the README and in the code.

## D3. 500-day main window

**Decision.** The main backtest uses a 500-day rolling window. The extended
analysis also uses 250 and 750 days.

**Context.** A short window reacts faster but is noisier. A long window is
smoother but slower to adapt. 500 days is a round choice that covers about two
years of trading.

**Consequence.** The main results depend on that choice. The sensitivity
analysis shows that the 750-day normal model passes all tests at 95%, while the
250-day and 500-day normal models fail independence. The 750-day pass is
exploratory, not a validated production choice.

## D4. Simple returns and daily rebalancing

**Decision.** Use simple returns `P_t / P_t-1 - 1` and compute the portfolio
return as `w' R_t`.

**Context.** The backtest needs a one-day horizon and a transparent portfolio
return. Log returns are available but are not used for the committed results.

**Consequence.** The portfolio is assumed to be rebalanced to the target
weights every day. Transaction costs, taxes and drift between rebalances are
ignored.

## D5. 100,000 Monte Carlo scenarios and seed 42

**Decision.** Draw 100,000 multivariate normal scenarios per forecast date and
use `seed + position` for the forecast date.

**Context.** The simulation must be reproducible and stable enough for daily
comparison with the parametric estimator.

**Consequence.** The Monte Carlo estimator converges to the parametric one
because both use the same normal model. The simulation adds sampling noise, not
model diversity. Repeating the run with the same seed produces the same
numbers.

## D6. Linear empirical quantile

**Decision.** Use NumPy's linear interpolation for the historical quantile.

**Context.** The empirical quantile needs a rule when the sample size times the
tail probability is not an integer.

**Consequence.** The historical VaR is a linear interpolation between the two
neighbouring order statistics. Other interpolation rules would give slightly
different numbers.

## D7. 95% main level and 99% extension

**Decision.** The main backtest and figures use 95%. The extended analysis also
backtests 99%.

**Context.** 95% gives enough violations for the coverage tests. 99% tests
whether the tail assumption holds.

**Consequence.** The normal model passes Kupiec at 95% with the 500-day window
but fails it at 99%, where it produces about twice the expected number of
violations. The 99% result is the clearest evidence against the normal tail.

## D8. Yahoo Finance snapshot when Stooq is blocked

**Decision.** The downloader tries Stooq first and falls back to Yahoo Finance
adjusted closes. The committed CSV is the Yahoo snapshot.

**Context.** On 2026-11-22 the Stooq CSV endpoint returned `Access denied` from
the author's network, both from Python and from a normal browser.

**Consequence.** The committed prices are adjusted closes, not raw closes. The
snapshot is versioned with a SHA-256 checksum. A fresh download can differ in
the last decimal places because vendors revise dividend adjustments.

## D9. 100% coverage and mutation smoke

**Decision.** Require 100% statement coverage of `src/risk_lab` and run five
source mutations in CI.

**Context.** Coverage alone does not prove that the tests detect wrong results.
The mutation checks verify that sign errors, a wrong quantile level, a wrong
p-value tail and a wrong violation comparison all fail the suite.

**Consequence.** New untested lines fail CI. The mutation checks are a small,
fixed set, not a full mutation campaign. They catch common regressions in the
core risk logic.

## D10. Pre-registered conditional volatility protocol

**Decision.** Write the six-model comparison protocol in
`docs/methodology.md` section 10 and commit it before computing any comparison
result. The protocol fixes the models, the EWMA λ = 0.94, the GARCH(1,1)
settings, the adaptive rule, the quantile loss, the 15 pairwise
Diebold-Mariano tests with 5 Newey-West lags, the Holm correction, the block
bootstrap and the winner rule.

**Context.** The earlier 750-day window was chosen after looking at the
results, and that pass is exploratory. Repeating that pattern with EWMA,
GARCH and adaptive windows would produce a result that cannot be distinguished
from a search over specifications.

**Consequence.** The protocol commit is `78143d0`. The winner rule requires
the best model to beat the second-best with a Holm-adjusted p-value below
0.05. On the committed snapshot the rule returns no clear winner between
GARCH(1,1) and EWMA. The repository keeps that result instead of promoting
the lowest point estimate.

## D11. Conditional normal risk and filtered historical ES

**Decision.** Use the conditional normal VaR and CVaR for the EWMA, GARCH and
parametric models, and filtered historical simulation for the ES of the
historical and adaptive models.

**Context.** EWMA and GARCH estimate a conditional variance but not a full
conditional distribution. The normal quantile is the simplest choice and
matches the existing parametric method. For the historical models, the
unconditional empirical tail does not respond to the volatility forecast, so
the ES is built by rescaling the standardized residuals to the current
volatility.

**Consequence.** At 99%, the conditional normal models still fail Kupiec. The
filtered historical ES is more responsive than the raw empirical tail but
still assumes that the standardized residuals are independent and identically
distributed. The ES bootstrap uses moving blocks of 20 days and does not
capture longer dependence.

## D12. Dated fresh snapshots with an immutable canonical file

**Decision.** `data/prices.csv` is never overwritten. Refreshes write a dated
file to `data/fresh/prices_<date>.csv` with its own SHA-256, and the comparison
writes to `docs/fresh`.

**Context.** The committed snapshot makes the results reproducible, but a
pipeline that only works on one frozen file cannot show how the model behaves
on new data. Overwriting the canonical file in place would silently change
every published table and break the checksum.

**Consequence.** `scripts/fetch_live_data.py` verifies the canonical checksum
before and after the download and refuses to replace a changed dated file
without `--force`. `scripts/make_fresh_analysis.py` verifies both checksums and
repeats the backtest on the fresh file and on the common period. The fresh
results in `docs/results_fresh.md` are tied to
`data/fresh/prices_2026-11-23.csv`. A new download on another day creates a new
file and does not alter the published comparison.

The first fresh run changed the point-estimate winner from GARCH(1,1) to EWMA.
The repository publishes that change. The pre-registered winner rule still
returns no clear winner, and the GARCH diagnostics show that the change comes
from numerical instability, not from a new economic regime.
