# Methodology

This document records the estimation and testing choices behind the numbers in
`docs/results.md`. It is the reference for the code in `src/risk_lab/`.

## 1. Scope and sign convention

The horizon is one trading day. Let R_t be the daily portfolio return and
L_t = -R_t the daily loss. All VaR and CVaR figures are positive losses. A VaR
of 0.0103 means a one-day loss of 1.03% of portfolio value. The return
quantile is -VaR.

The confidence level is α. The main analysis uses α = 0.95. The extended
analysis also uses α = 0.99.

## 2. Data

The portfolio holds three US ETFs with fixed long-only weights:

| Ticker | Exposure | Weight |
|---|---|---:|
| SPY | US large-cap equities | 0.50 |
| TLT | US long-term Treasuries | 0.35 |
| GLD | Gold | 0.15 |

The weights are a simple allocation across equity, duration and gold. They
were not optimized on the sample. The portfolio is rebalanced to the target
weights every day and pays no transaction costs.

`data/prices.csv` contains 2,513 adjusted closes from 2016-11-22 to
2026-11-20. Returns are computed from consecutive rows, so the first return is
2016-11-23 and the sample has 2,512 returns. The three series are aligned on
the intersection of US trading days. Missing calendar dates are non-trading
days.

The committed snapshot uses Yahoo Finance adjusted closes, which account for
splits and dividends. The downloader tries Stooq first. On 2026-11-22 the
Stooq CSV endpoint returned `Access denied` from the author's network, both
from Python and from a normal browser. The provenance note is in the README.
The SHA-256 of the committed CSV is
`d33a038e9b4460468ca195b2f7c9c3374ce062d1ff7cf75280f6a8e300e2e3a1` and is also
stored in `data/prices.sha256`.

## 3. Portfolio returns

Simple returns are used:

```text
R_i,t = P_i,t / P_i,t-1 - 1
R_p,t = sum_i w_i R_i,t
```

The portfolio return is the weighted sum of the asset returns. This is the
return of a portfolio rebalanced to the target weights at the start of each
day. Log returns are available in the code but are not used for the committed
results.

## 4. VaR and CVaR estimators

### 4.1 Historical

The empirical quantile of the estimation window is Q_{1-α}. The estimators
are:

```text
VaR_t  = -Q_{1-α}(R_{t-w}, ..., R_{t-1})
CVaR_t = -mean(R_s | R_s <= Q_{1-α})
```

The quantile uses linear interpolation, which is the NumPy default. The CVaR
is the negative mean of the returns at or below that quantile. No
distributional assumption is made.

### 4.2 Parametric

With μ_t and σ_t the sample mean and sample standard deviation of the window
(`ddof=1`), and z_p = Φ^{-1}(p):

```text
VaR_t  = -(μ_t + σ_t z_{1-α})
CVaR_t = -μ_t + σ_t φ(z_{1-α}) / (1 - α)
```

The CVaR expression is the closed-form mean of the normal loss tail. It is
the limit of the average loss beyond VaR under normality, not an average over
a finite sample.

If μ_t is large and positive relative to σ_t, the normal quantile can be
positive and the reported VaR can be negative. A negative VaR is a predicted
gain at the lower tail quantile, not a data error. This does not occur in the
committed portfolio results.

### 4.3 Monte Carlo

The window gives an asset mean vector μ_t and a sample covariance matrix Σ_t
(`ddof=1`). The simulation draws 100,000 scenarios:

```text
R^(s) = μ_t + C_t z^(s),   z^(s) ~ N(0, I),   C_t C_t' = Σ_t
R_p^(s) = w' R^(s)
VaR_t  = -Q_{1-α}(R_p^(s))
CVaR_t = -mean(R_p^(s) | R_p^(s) <= Q_{1-α})
```

`C_t` is the lower Cholesky factor of Σ_t. The seed is 42. In the rolling
backtest the seed for forecast day t is 42 plus the integer position of t in
the return array, so every day has a deterministic and independent stream.
The simulation is the same normal model as the parametric estimator, with
sampling noise added by the finite number of scenarios. For a fixed-weight
portfolio, the two estimators converge to the same value as the number of
scenarios grows.

## 5. Walk-forward backtest

The backtest is walk-forward:

- The first 500 returns form the initial estimation window.
- For each forecast date t, the model uses only returns from t-500 to t-1.
- The forecast is one day ahead. The estimation window rolls forward one day.
- A violation occurs when the realized loss is strictly greater than VaR.
- The main sample has 2,012 forecasts, from 2018-11-19 to 2026-11-20.
- The expected number of violations at 95% is 2,012 × 0.05 = 100.6.

The extended analysis repeats the same design with windows of 250, 500 and 750
days and levels of 95% and 99%. A longer window uses more history but reacts
more slowly to changes in volatility. A shorter window reacts faster but is
noisier.

## 6. Coverage tests

### 6.1 Kupiec

Let N be the number of forecasts, x the number of violations and p0 = 1 - α.
Under the null, the violation probability is p0. The likelihood-ratio
statistic is:

```text
LR_uc = -2 ln[ (1-p0)^(N-x) p0^x / ((1-x/N)^(N-x) (x/N)^x) ]
```

Under the null, LR_uc is asymptotically χ²(1). The p-value is
`chi2.sf(LR_uc, 1)`. The zero-violation and all-violation cases are handled as
limits.

### 6.2 Christoffersen independence

Let n_ij be the number of transitions from state i on one day to state j on
the next day, where 0 means no violation and 1 means violation. Define:

```text
π01 = n01 / (n00 + n01)
π11 = n11 / (n10 + n11)
π   = (n01 + n11) / (n00 + n01 + n10 + n11)

LR_ind = -2 ln[ (1-π)^(n00+n10) π^(n01+n11)
                / ((1-π01)^n00 π01^n01 (1-π11)^n10 π11^n11) ]
```

Under the null, LR_ind is asymptotically χ²(1). The p-value is
`chi2.sf(LR_ind, 1)`. If one of the two states never follows a transition,
the test is undefined and the implementation returns a NaN p-value instead of
inventing one.

### 6.3 Conditional coverage

The joint test combines correct unconditional coverage and independence:

```text
LR_cc = LR_uc + LR_ind
```

Under the null, LR_cc is asymptotically χ²(2). The p-value is
`chi2.sf(LR_cc, 2)`. If the independence component is undefined, the joint
test is undefined and the p-value is NaN.

All p-values are computed with SciPy. None are typed in from a table.

## 7. Violations by year

For the main 95% and 500-day backtest, violations are grouped by calendar
year. The table reports observations, violations, expected violations and the
violation rate. The first year is partial because the first forecast is
2018-11-19, and the last year is partial because the sample ends on
2026-11-20. The yearly counts are descriptive. They are not a formal test,
and the annual samples are small. The CSV files store rates as fractions. The
Markdown tables show percentages.

## 8. Reproducibility

The committed data, figures and tables are the reference. The main pipeline
uses 100,000 Monte Carlo scenarios and seed 42. `scripts/make_figures.py`
writes the main tables and figures. `scripts/make_extended_analysis.py` writes
the level and window sensitivity tables and the yearly counts.

Two runs with the same seed produce identical estimators. The Monte Carlo
stream is deterministic per forecast date. The only source of variation is a
change in the input data or in the code.

## 9. Design choices and limitations

The main limitations are documented in the README. The most important are:

- The parametric and Monte Carlo estimators assume multivariate normality.
  The empirical tail is fatter, especially at 99%.
- The rolling window is fixed. It does not adapt to regime changes.
- The portfolio is static and ignores transaction costs.
- The coverage tests are asymptotic and have low power in small samples.
- The analysis is one sample and one portfolio. The results should not be read
  as evidence about other assets or other periods.

## 10. Pre-registered conditional-volatility comparison (2026-11-23)

This protocol was written before running the conditional-volatility comparison.
The model list, the adaptive rule, the GARCH settings, the loss function, the
DM lag, the bootstrap settings, the stress years and the winner rule are fixed.
No choice below is changed after seeing the comparison table.

### 10.1 Evaluation period

The common evaluation period is the same as the main backtest: 2,012 one-day
forecasts from 2018-11-19 to 2026-11-20. Every model uses only data available
before the forecast date. The common start is the first date with 500 portfolio
returns.

### 10.2 Models

1. **Historical 500.** Empirical 5% quantile of the previous 500 portfolio
   returns. CVaR is the mean of the tail.
2. **Parametric 500.** Normal VaR and CVaR from the sample mean and sample
   standard deviation of the previous 500 returns.
3. **EWMA normal.** Lambda = 0.94, mean = 0. The variance is initialized with
   the sample variance of the first 500 returns and updated daily as
   `sigma2_t = 0.94 sigma2_t-1 + 0.06 r_t-1^2`. VaR and CVaR use the normal
   quantile and the normal tail mean at the conditional volatility.
4. **GARCH(1,1) normal.** Constant mean, Gaussian quasi-maximum likelihood on
   the previous 500 returns. Parameters are re-estimated every 21 trading days.
   The variance is filtered daily with the latest return and the current
   parameters. The one-step forecast is
   `sigma2_t = omega + alpha (r_t-1 - mu)^2 + beta sigma2_t-1`. Starting values
   are `(omega, alpha, beta) = (0.05 var, 0.05, 0.90)`, with bounds
   `omega > 0`, `0 <= alpha < 1`, `0 <= beta < 1` and `alpha + beta < 0.999`.
   If the optimizer fails, the last successful parameters are kept. If the first
   estimation fails, the fallback is `alpha = 0.05`, `beta = 0.90`,
   `omega = var (1 - 0.95)`.
5. **Historical adaptive window.** At each date, compute the 20-day and 250-day
   realized volatilities of portfolio returns. If the ratio is at least 1.25,
   use a 250-day window. Otherwise use 500 days. The empirical quantile and tail
   mean use the chosen window.
6. **Parametric adaptive window.** Same window rule as model 5, applied to the
   normal mean and standard deviation.

The 750-day window is not part of the adaptive rule. It is already covered by
the exploratory sensitivity analysis, and excluding it keeps a common start
without a 750-day warm-up asymmetry.

### 10.3 VaR and ES

VaR and CVaR are positive losses. The confidence levels are 95% and 99%.

- **Parametric ES.** Closed-form normal tail mean for models 2, 3, 4 and 6.
  Models 1 and 5 do not have a parametric ES and are reported as not applicable.
- **Simulation ES.** Filtered historical simulation for every model. For each
  forecast date, standardize the estimation-window returns with the model's
  conditional mean and volatility. Draw 10,000 standardized residuals with
  replacement, with seed `42 + position`. Simulate one-day returns at the
  forecast mean and volatility. The simulated VaR is the 5% quantile and the
  simulated ES is the mean of the losses beyond it.
- **Bootstrap interval.** The interval is for the mean ES over the evaluation
  period. Use a moving block bootstrap of the daily ES series with block length
  20, 10,000 resamples, seed 42 and the percentile method. Report the 2.5% and
  97.5% quantiles. Parametric and simulation ES have separate intervals.

### 10.4 Diebold-Mariano

The forecast loss is the quantile loss with `tau = 1 - level` and
`q_t = -VaR_t`:

```text
rho_tau(R_t - q_t) = (tau - 1{R_t < q_t}) (R_t - q_t)
```

For each pair of models, `d_t = L_A,t - L_B,t`. The DM statistic uses the
Newey-West long-run variance with 5 lags. The p-value is two-sided from the
standard normal distribution. All 15 pairwise comparisons are reported. The
Holm-Bonferroni correction is applied to the 15 p-values. A negative mean
difference favors the first model.

### 10.5 Winner rule

The winner is the model with the lowest mean quantile loss over the full
evaluation period. It is a clear winner only if its Holm-adjusted DM p-value
against the second-best model is below 0.05. If no model meets both conditions,
the result is reported as "no clear winner".

The best model by mean quantile loss in each stress year is also reported, with
no formal test. The stress years are 2020, 2022 and 2026. They are fixed before
the comparison.

### 10.6 Coverage

Kupiec and Christoffersen are reported for every model at 5%. The conditional
coverage test is also reported. A model can have the lowest forecast loss and
still fail coverage. The comparison reports both facts without selecting a
different winner.

### 10.7 Selection honesty

The existing 750-day sensitivity result is exploratory and remains labelled as
such. It is not used to choose the conditional-volatility winner. The new
winner rule is fixed in this section and is applied exactly once to the
comparison table.

