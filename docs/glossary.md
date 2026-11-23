# Glossary

- **VaR (Value at Risk).** The loss threshold that is expected to be exceeded
  with probability `1 - level` over one day. Reported as a positive loss.
- **CVaR (Conditional Value at Risk).** The average loss conditional on the
  loss being at or beyond the VaR threshold. Also called Expected Shortfall.
  Reported as a positive loss.
- **Violation.** A day whose realized loss is strictly greater than the VaR
  forecast for that day.
- **Coverage.** The fraction of days that should be violations under the
  nominal level. At 95%, the expected coverage is 5%.
- **Kupiec test.** A likelihood-ratio test of the null that the violation
  probability equals the nominal `1 - level`.
- **Christoffersen independence test.** A likelihood-ratio test of the null
  that a violation today does not change the probability of a violation
  tomorrow.
- **Conditional coverage test.** The joint test that combines Kupiec and
  Christoffersen. It uses two degrees of freedom.
- **Rolling window.** The fixed number of past observations used to estimate
  the model for each forecast. The main window is 500 days.
- **Walk-forward backtest.** A backtest that re-estimates the model on each
  date using only past data and then forecasts the next day.
- **Historical estimator.** Uses the empirical quantile of the window returns.
- **Parametric estimator.** Uses the sample mean and standard deviation and a
  normal quantile.
- **Monte Carlo estimator.** Simulates portfolio returns from a multivariate
  normal model fitted to the window.
- **Fat tail.** A loss distribution with more probability in the extreme left
  tail than a normal distribution with the same variance.
- **Adjusted close.** A price series adjusted for splits and dividends. The
  committed snapshot uses adjusted closes.
- **Seed.** The integer that makes a Monte Carlo run reproducible. The main
  run uses seed 42 and adds the forecast position.
- **EWMA (exponentially weighted moving average).** A variance recursion that
  gives more weight to recent returns. The weight of older observations decays
  by λ each day. The comparison uses λ = 0.94 and a zero mean.
- **GARCH(1,1).** A model in which today's variance depends on the last squared
  shock and on yesterday's variance: `σ²_t = ω + α ε²_{t-1} + β σ²_{t-1}`. The
  parameters are estimated by quasi-maximum likelihood.
- **Conditional volatility.** A volatility estimate that changes with the
  information available before each forecast, instead of being constant over
  the sample.
- **Adaptive window.** A rolling window that switches between 250 and 500 days
  when the ratio of 20-day to 250-day realized volatility crosses 1.25.
- **Filtered historical simulation (FHS).** A method that standardizes past
  returns by their conditional volatility, resamples the standardized
  residuals and rescales them by the current volatility forecast.
- **Quantile loss.** An asymmetric loss for a quantile forecast. It penalizes
  VaR forecasts that are too low more heavily than forecasts that are too high.
  The comparison uses it to rank models.
- **Diebold-Mariano test.** A test of equal predictive accuracy for two loss
  series, using a Newey-West estimate of the long-run variance.
- **Holm-Bonferroni correction.** A multiple-testing correction that sorts the
  p-values and multiplies each by its rank, enforcing monotonicity. It controls
  the family-wise error rate without assuming independence.
- **Moving block bootstrap.** A resampling method that draws contiguous blocks
  of a time series to preserve short-range dependence. The ES intervals use
  blocks of 20 days.
- **Pre-registration.** Writing and committing the model list, the tests and
  the decision rule before looking at the results, so the conclusion cannot be
  chosen after the fact.
- **Fresh snapshot.** A dated price download stored under `data/fresh`, with its
  own checksum. It never replaces the canonical `data/prices.csv`.
- **Common-period check.** Repeating the fresh comparison after cutting the new
  prices at the canonical end date, so price revisions can be separated from
  genuinely new trading days.
- **Degenerate GARCH fit.** A numerically accepted optimum with `alpha` near
  zero, `beta` near one, or `omega` far above the sample variance. It is not a
  stable economic estimate even when the optimizer reports success.
