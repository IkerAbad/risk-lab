# risk-lab

One-day Value at Risk (VaR) and Conditional Value at Risk (CVaR) for a fixed
three-asset portfolio, with rolling backtests at 95% and 99%, coverage tests
and a reproducible data snapshot.

Author: Iker Abad (GitHub: [IkerAbad](https://github.com/IkerAbad))

License: MIT, Copyright (c) 2026 Iker Abad.

The repository is self-contained. The price snapshot, the figures and the
result tables are committed, so the tests and the figure pipeline run without
network access.

## Project layout

```text
risk-lab/
├── data/
│   ├── prices.csv
│   └── prices.sha256
├── docs/
│   ├── methodology.md
│   ├── results.md
│   ├── api.md
│   ├── fig1_returns_violations.png
│   ├── fig2_rolling_var.png
│   ├── full_sample_risk.csv
│   ├── backtest_summary.csv
│   ├── backtest_series.csv
│   ├── sensitivity.csv
│   └── violations_by_year.csv
├── scripts/
│   ├── download_data.py
│   ├── make_figures.py
│   ├── make_extended_analysis.py
│   └── check_all.py
├── src/risk_lab/
│   ├── data.py
│   ├── var.py
│   ├── backtest.py
│   ├── stats.py
│   └── plots.py
├── tests/
│   ├── test_data.py
│   ├── test_var.py
│   ├── test_backtest.py
│   ├── test_stats.py
│   ├── test_plots.py
│   ├── test_download.py
│   ├── test_scripts.py
│   ├── test_properties.py
│   ├── test_packaging.py
│   └── test_docs.py
├── .github/
│   ├── workflows/ci.yml
│   └── dependabot.yml
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── CITATION.cff
├── SECURITY.md
└── LICENSE
```

## Data

The portfolio holds three US ETFs with fixed long-only weights:

| Ticker | Exposure | Weight |
|---|---|---:|
| SPY | US large-cap equities | 0.50 |
| TLT | US long-term Treasuries | 0.35 |
| GLD | Gold | 0.15 |

The weights are a simple allocation across equity, duration and gold. They were
not optimized on the sample. The portfolio is rebalanced to the target weights
every day and pays no transaction costs.

`data/prices.csv` contains 2,513 daily adjusted closes from 2016-11-22 to
2026-11-20. Returns are computed from consecutive rows, so the first return is
2016-11-23 and the sample has 2,512 returns. The three series are aligned on
the intersection of US trading days. Missing calendar dates are non-trading
days.

SHA-256 of the committed CSV, also stored in `data/prices.sha256`:

```text
d33a038e9b4460468ca195b2f7c9c3374ce062d1ff7cf75280f6a8e300e2e3a1
```

### Source and provenance

`scripts/download_data.py` tries Stooq first, using the symbols `spy.us`,
`tlt.us` and `gld.us`. On 2026-11-22 the Stooq CSV endpoint returned
`Access denied` from the author's network, both from Python and from a normal
browser. The committed snapshot was therefore built from Yahoo Finance
adjusted closes. The adjusted close accounts for splits and dividends. The
downloader keeps the Stooq path for networks where the endpoint works and
falls back to Yahoo only when Stooq fails. The Stooq path uses its `Close`
column as provided. The committed results use the Yahoo adjusted close.

The command used for the committed file was:

```bash
python scripts/download_data.py --start 2016-11-22 --end 2026-11-22 --out data/prices.csv
```

The file is versioned. Re-running the downloader on a later date moves the
sample window and changes every result. Yahoo also revises adjusted closes
when dividend information changes, so a fresh download of the same date range
can differ from the committed snapshot in the last decimal places. The
committed CSV and its SHA-256 are the reference for every number in this
README.

## Methods

Let R_t be the daily portfolio return and L_t = -R_t the daily loss. All VaR
and CVaR figures in this repository are reported as positive losses. A VaR of
0.0103 means a one-day loss of 1.03% of portfolio value. The return quantile
is -VaR.

The main analysis uses α = 0.95 and a 500-day window. The extended analysis
uses α = 0.99 and windows of 250, 500 and 750 days.

### Historical

The empirical quantile with linear interpolation is Q_{1-α}. The estimators
are:

```text
VaR_t  = -Q_{1-α}(R_{t-500}, ..., R_{t-1})
CVaR_t = -mean(R_s | R_s <= Q_{1-α})
```

The CVaR is the negative mean of the returns in the empirical tail at or below
the quantile. No distributional assumption is made.

### Parametric

With μ_t and σ_t the sample mean and sample standard deviation of the window
(`ddof=1`), and z_p = Φ^{-1}(p):

```text
VaR_t  = -(μ_t + σ_t z_{1-α})
CVaR_t = -μ_t + σ_t φ(z_{1-α}) / (1 - α)
```

The CVaR expression is the closed-form mean of the normal loss tail. It is
not an average over a finite sample.

### Monte Carlo

The window gives an asset mean vector μ_t and a sample covariance matrix Σ_t
(`ddof=1`). The simulation draws 100,000 scenarios:

```text
R^(s) = μ_t + C_t z^(s),   z^(s) ~ N(0, I),   C_t C_t' = Σ_t
R_p^(s) = w' R^(s)
VaR_t  = -Q_{1-α}(R_p^(s))
CVaR_t = -mean(R_p^(s) | R_p^(s) <= Q_{1-α})
```

`C_t` is the lower Cholesky factor of Σ_t. The seed is fixed at 42. In the
rolling backtest the seed for forecast day t is 42 plus the integer position
of t in the return array, so every day has a deterministic and independent
stream. The committed results use 100,000 scenarios per day.

## Backtest design

The backtest is walk-forward:

- The first 500 returns form the initial estimation window.
- For each forecast date t, the model uses only returns from t-500 to t-1.
- The forecast is one day ahead. The estimation window rolls forward one day.
- A violation occurs when the realized loss is strictly greater than VaR.
- The sample has 2,012 forecasts, from 2018-11-19 to 2026-11-20.
- The expected number of violations at 95% is 2,012 × 0.05 = 100.6.

### Kupiec test

Let N be the number of forecasts, x the number of violations and p0 = 1 - α.
Under the null, the violation probability is p0. The likelihood-ratio
statistic is:

```text
LR_uc = -2 ln[ (1-p0)^(N-x) p0^x / ((1-x/N)^(N-x) (x/N)^x) ]
```

Under the null, LR_uc is asymptotically χ²(1). The p-value is
`chi2.sf(LR_uc, 1)`. The zero-violation and all-violation cases are handled as
limits.

### Christoffersen independence test

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

### Christoffersen conditional coverage test

The joint test combines correct unconditional coverage and independence:

```text
LR_cc = LR_uc + LR_ind
```

Under the null, LR_cc is asymptotically χ²(2). The p-value is
`chi2.sf(LR_cc, 2)`. If the independence component is undefined, the joint test
is undefined and the p-value is NaN.

All p-values are computed with SciPy. None are typed in from a table.

## Results

### Full-sample estimates

These are descriptive estimates on the 2,512 returns. They are not the
backtest.

| Method | VaR 95% | CVaR 95% |
|---|---:|---:|
| Historical | 1.031% | 1.574% |
| Parametric | 1.068% | 1.349% |
| Monte Carlo | 1.076% | 1.353% |

The empirical CVaR is 0.225 percentage points above the normal CVaR. The
empirical VaR is slightly lower than the normal VaR. This combination is what
a fat left tail looks like in this sample: the 5% quantile is close to the
normal one, while the average loss beyond it is larger.

### Rolling backtest

| Method | Violations | Expected | Rate | Kupiec LR | Kupiec p | Christoffersen LR | Christoffersen p | Conditional p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Historical | 120 | 100.6 | 5.96% | 3.719 | 0.0538 | 9.865 | 0.00168 | 0.00112 |
| Parametric | 114 | 100.6 | 5.67% | 1.805 | 0.1791 | 12.127 | 0.000497 | 0.000944 |
| Monte Carlo | 114 | 100.6 | 5.67% | 1.805 | 0.1791 | 12.127 | 0.000497 | 0.000944 |

The Monte Carlo and parametric rows are identical after rounding because both
models assume the same multivariate normal distribution. The Monte Carlo
estimate is a numerical approximation of the parametric one. The largest
absolute difference between their daily VaR estimates is 0.000202 in return
units, or 0.0202 percentage points, and the violation flags differ on 2 of the
2,012 days. Those two differences cancel in the totals and do not change the
transition counts.

Interpretation:

- Kupiec does not reject correct unconditional coverage for any method at the
  5% level. The historical method is borderline at p = 0.0538 and its observed
  rate is 5.96%, above the nominal 5%.
- Christoffersen rejects independence for all three methods. The p-values are
  0.00168, 0.000497 and 0.000497. The violations cluster in time, which is
  consistent with the models reacting too slowly to changes in volatility.
- The joint conditional coverage test also rejects all three methods, with
  p-values 0.00112, 0.000944 and 0.000944.
- No method passes all three tests. The normal models pass unconditional
  coverage but fail independence and conditional coverage. The historical
  model is close to failing unconditional coverage and also fails independence
  and conditional coverage.
- The historical method has the lowest average rolling VaR, 1.016% against
  1.091% for the normal models. That is consistent with its six more
  violations.
- The historical CVaR is higher on average, 1.564% against 1.378% for the
  normal models. The normal models underestimate the size of the tail losses.

The independence rejections survive a Bonferroni correction for the six
Kupiec and independence tests at the 5% level, whose threshold is 0.00833.
They do not disappear after rounding.

### Extended analysis

The full tables are in [docs/results.md](docs/results.md). The key results:

- At 99% with the 500-day window, the normal model has 40 violations against
  20.1 expected. Kupiec p = 8.64e-05. The historical model has 24 against 20.1,
  Kupiec p = 0.3988, but Christoffersen p = 0.00227. The normal tail is too
  thin.
- At 95%, the 750-day normal model is the only combination that passes
  Kupiec, Christoffersen and conditional coverage. It has 96 violations
  against 88.1 expected, Kupiec p = 0.3944, Christoffersen p = 0.1040 and
  conditional p = 0.1856. The 250-day and 500-day normal models fail
  independence. The window length matters.
- The yearly table shows the clustering. In 2022, the historical method has
  31 violations out of 251 forecasts (12.35%) and the normal model 37 (14.74%).
  In 2023, all methods have 5 out of 250 (2.00%).
- The 750-day pass is exploratory. It was selected after looking at the
  results and is not corrected for multiple testing.

The yearly counts are in `docs/violations_by_year.csv`. The full sensitivity
table is `docs/sensitivity.csv`.

### Figures

![Portfolio returns and 95% VaR violations](docs/fig1_returns_violations.png)

Figure 1: daily portfolio returns and the rolling historical VaR at 95%. Red
dots mark the 120 violations. The VaR line is the negative of the positive VaR
estimate.

![Rolling VaR versus realized loss](docs/fig2_rolling_var.png)

Figure 2: realized daily loss against the rolling VaR from the three methods.
The historical VaR is usually the lowest of the three. The parametric and Monte
Carlo lines are nearly identical.

## Documentation

- [docs/methodology.md](docs/methodology.md): estimation and testing details.
- [docs/results.md](docs/results.md): full tables for 95%, 99%, windows and
  calendar years.
- [docs/api.md](docs/api.md): public functions, arguments and error conditions.
- [CONTRIBUTING.md](CONTRIBUTING.md): setup, checks and how to add a method.
- [CHANGELOG.md](CHANGELOG.md): version history.
- [CITATION.cff](CITATION.cff): citation metadata.
- [SECURITY.md](SECURITY.md): vulnerability reporting and scope.

## Reproduce

Create an environment and install the package:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Run the tests and the static checks:

```bash
python -m pytest -q --cov=risk_lab --cov-report=term-missing
python -m ruff check .
python -m mypy src
python -m bandit -r src scripts -q
```

Or run the whole gate with one command:

```bash
python scripts/check_all.py
```

Regenerate the figures and main tables from the committed CSV:

```bash
python scripts/make_figures.py
```

The default run uses 100,000 Monte Carlo scenarios, a 500-day window and seed
42. It took about 11 seconds on the machine used to build the snapshot. A
quick run with fewer scenarios is possible, but its numbers will not match the
committed tables:

```bash
python scripts/make_figures.py --scenarios 10000
```

Regenerate the extended analysis with the 95% and 99% levels and the 250, 500
and 750-day windows:

```bash
python scripts/make_extended_analysis.py
```

This runs six backtests with 100,000 scenarios each. It took about 63 seconds
on the machine used to build the snapshot and writes `docs/sensitivity.csv` and
`docs/violations_by_year.csv`.

Refresh the price snapshot (needs network access):

```bash
python scripts/download_data.py
```

The script writes `data/prices.csv` and prints the source it used. If Stooq
rejects the request, it prints the reason and switches to Yahoo Finance. Use
`--source stooq` or `--source yahoo` to force one source.

The pipeline writes:

- `docs/fig1_returns_violations.png`
- `docs/fig2_rolling_var.png`
- `docs/full_sample_risk.csv`
- `docs/backtest_summary.csv`
- `docs/backtest_series.csv`
- `docs/sensitivity.csv`
- `docs/violations_by_year.csv`

`backtest_series.csv` contains one row per forecast date, with the realized
return, the three VaR and CVaR estimates, and the three violation flags.

## Tests

The suite has 118 tests, grouped by module and by script:

- `tests/test_data.py`: price validation, simple and log returns, weighted
  portfolio returns, weight validation and the committed snapshot checksum.
- `tests/test_var.py`: historical VaR against a hand-built empirical quantile,
  the parametric formula against μ + σ z, CVaR against a known tail mean, the
  normal CVaR closed form, Monte Carlo reproducibility with the same seed, and
  input validation.
- `tests/test_stats.py`: Kupiec with N = 250, x = 10 and p0 = 0.05, whose
  p-value is checked to 1e-6 against 0.4529124499351952, plus a known
  Christoffersen independence case, a known conditional coverage case and the
  undefined-state behaviour.
- `tests/test_backtest.py`: no lookahead, the violation flag, summary counts,
  the Monte Carlo path, yearly violation counts and argument validation.
- `tests/test_plots.py`: both figures are written, missing methods are skipped
  and missing columns are rejected.
- `tests/test_download.py`: Stooq and Yahoo parsing with mocked HTTP responses,
  fallback behaviour, malformed payloads and the command-line error path.
- `tests/test_scripts.py`: end-to-end runs of both scripts on synthetic data
  and clean error handling when the input file is missing.
- `tests/test_properties.py`: Hypothesis checks for CVaR >= VaR, monotonicity
  in the confidence level, the empirical quantile identity and p-value ranges.
- `tests/test_packaging.py`: version consistency across `pyproject.toml`, the
  package, `CITATION.cff` and `CHANGELOG.md`, plus the `py.typed` marker.
- `tests/test_docs.py`: relative Markdown links and consistency between the
  README tables, `docs/results.md` and the committed CSV files.

The tests do not need network access. They use hand-built arrays, mocked HTTP
responses and temporary files. The committed CSV is checked byte for byte
against `data/prices.sha256`.

CI runs on Ubuntu, Windows and macOS with Python 3.12 and 3.14. The workflow
installs the package with the development extra, runs `ruff`, runs `mypy`, runs
Bandit and runs `pytest` with a 99% coverage threshold.

## Robustness

- The committed CSV is checked against `data/prices.sha256` by the test suite.
  A corrupted or accidentally regenerated snapshot fails the tests.
- The suite has 118 tests and 99.5% statement coverage of `src/risk_lab`. CI
  enforces a 99% threshold.
- Property-based tests cover the numerical invariants: CVaR is at least VaR,
  VaR is monotone in the confidence level, the empirical VaR is the negative
  quantile and every p-value is a probability.
- The package ships a `py.typed` marker, so type checkers use its annotations.
- Every public function validates its inputs. The estimators reject empty
  arrays, NaN, infinite values, invalid levels and bad weights.
- The downloader has unit tests with mocked HTTP responses, so Stooq errors,
  Yahoo errors and malformed payloads are tested without network access.
- `make_figures.py` and `make_extended_analysis.py` return a non-zero exit code
  and a one-line error message instead of a traceback.
- CI runs `ruff`, `mypy`, Bandit and the test suite on Ubuntu, Windows and
  macOS with Python 3.12 and 3.14.
- `scripts/check_all.py` runs the checksum, `ruff`, `mypy`, Bandit and the test
  suite with coverage in one command.
- Dependabot keeps the GitHub Actions and the Python dependencies current.
- The repository is versioned with tags. The current release is `v0.2.2`.

## Limitations

- The parametric and Monte Carlo methods assume multivariate normality. The
  data have a fatter left tail. The full-sample empirical CVaR is 1.574%
  against 1.349% for the normal model, so the normal model understates the
  average tail loss by 0.225 percentage points. At 99%, the normal model
  produces about twice the expected number of violations at every window and
  Kupiec rejects it.
- The main window is fixed at 500 days. It does not adapt to regime changes.
  The 750-day normal model passes all three tests at 95%, so the window length
  matters. That pass was selected after inspecting the results and is
  exploratory, not a validated production choice. An exponentially weighted or
  GARCH-based volatility model would react faster, but it would add parameters
  and estimation risk.
- The portfolio is static. Weights are rebalanced daily to 50/35/15 with no
  transaction costs, no taxes and no liquidity constraints. A real portfolio
  would drift between rebalances and pay to trade.
- The sample is one path of history. The backtest has 2,012 forecasts, which
  is enough to detect large coverage errors but not enough for precise tail
  estimates at 99%, where the expected count is about 20.
- The tests are asymptotic. Kupiec and Christoffersen have low power in small
  samples. The independence test only checks first-order Markov dependence.
  The conditional coverage test combines Kupiec and first-order independence,
  but it does not model higher-order dependence or covariates.
- The figures use the 95% level. The extended analysis also backtests 99%, but
  the figures are not redrawn at that level.
- VaR is not subadditive and can penalize diversification. CVaR is coherent.
  The report shows both.
- The committed data come from Yahoo Finance, not Stooq, because the Stooq CSV
  endpoint returned `Access denied` on 2026-11-22. The adjusted close assumes
  dividends are reinvested and ignores taxes and trading costs. If the
  downloader is run on a network where Stooq works, the sample changes and the
  results must be recomputed.
- Monte Carlo does not add model diversity here. It simulates the same normal
  model as the parametric method, so the two sets of results are nearly
  identical. The simulation only adds sampling noise.
- No multiple-testing correction is applied. The main table has nine tests and
  the sensitivity analysis has 18 method-window-level combinations. The
  750-day pass is exploratory. The 99% rejections are strong enough that a
  multiple-testing correction does not change the conclusion.

## License

MIT. See `LICENSE`.

## Resumen en español

Este repositorio calcula el VaR y el CVaR a un día de una cartera fija de SPY,
TLT y GLD con pesos 50/35/15. Usa tres métodos: histórico, paramétrico normal
y Monte Carlo multivariante con 100.000 escenarios y semilla fija. El backtest
principal es rolling, con una ventana de 500 días, reestimación diaria y
predicción a un día. La muestra tiene 2.012 predicciones, del 19/11/2018 al
20/11/2026. El análisis extendido añade el nivel 99% y ventanas de 250, 500 y
750 días.

Los datos versionados en el repositorio son cierres ajustados de Yahoo
Finance, no de Stooq. La descarga CSV de Stooq devolvió `Access denied` el
22/11/2026 desde esta red y también desde el navegador. El script intenta
Stooq primero y cae a Yahoo cuando falla. La procedencia está documentada
arriba y el CSV lleva su hash SHA-256.

Resultados reales:

- En la muestra completa, el VaR histórico al 95% es 1,031%, el paramétrico
  1,068% y el de Monte Carlo 1,076%. El CVaR histórico es 1,574%, frente a
  1,349% del paramétrico y 1,353% del Monte Carlo. La cola empírica es más
  pesada que la normal.
- En el backtest principal, el método histórico tiene 120 violaciones frente a
  100,6 esperadas. Kupiec da p = 0,0538, justo por encima del 5%.
  Christoffersen da p = 0,00168 y rechaza la independencia. El test condicional
  conjunto da p = 0,00112.
- Los métodos paramétrico y Monte Carlo tienen 114 violaciones. Kupiec da
  p = 0,1791 y no rechaza la cobertura. Christoffersen da p = 0,000497 y el
  test condicional p = 0,000944. Los tres rechazan la independencia.
- Ningún método pasa los tres tests. Las violaciones se agrupan en el tiempo,
  lo que es coherente con una ventana fija que reacciona despacio a los
  cambios de volatilidad.
- A 99% con 500 días, el modelo normal tiene 40 violaciones frente a 20,1
  esperadas y Kupiec da p = 8,64e-05. El histórico tiene 24 frente a 20,1,
  Kupiec p = 0,3988, pero Christoffersen p = 0,00227.
- La ventana de 750 días es la única combinación que pasa los tres tests al
  95% con el modelo normal: 96 violaciones frente a 88,1, Kupiec p = 0,3944,
  Christoffersen p = 0,1040, condicional p = 0,1856. Es un resultado
  exploratorio, elegido después de ver los datos.
- En 2022 el histórico tiene 31 violaciones de 251 (12,35%) y el normal 37
  (14,74%). En 2023 todos tienen 5 de 250 (2,00%).
- Monte Carlo y paramétrico dan resultados casi idénticos porque simulan el
  mismo supuesto de normalidad. La diferencia máxima diaria de VaR es 0,000202
  en unidades de retorno, o 0,0202 puntos porcentuales, y las violaciones solo
  difieren en 2 de los 2.012 días.

Limitaciones principales: la normalidad no recoge las colas gruesas (a 99%
produce el doble de violaciones esperadas), la ventana fija no se adapta a los
cambios de régimen, la cartera es estática y no paga costes, y los tests
asintóticos tienen poca potencia en muestras pequeñas. No se maquillan los
resultados: a 95% y 500 días los tres métodos fallan la independencia, y a 99%
el modelo normal falla Kupiec.

Robustez: 118 tests, 99,5% de cobertura, tests de propiedades, comprobación
del checksum del CSV, paquete con `py.typed`, CI en Ubuntu, Windows y macOS
con Python 3.12 y 3.14, ruff, mypy, bandit y Dependabot.

Para reproducir todo:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/make_figures.py
python scripts/make_extended_analysis.py
```
