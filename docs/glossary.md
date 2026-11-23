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
