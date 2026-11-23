# Fresh-data comparison

Canonical snapshot: `data/prices.csv`, 2513 rows, 2016-11-22 to 2026-11-20.

Fresh snapshot: `data/fresh/prices_2026-11-23.csv`, 2514 rows, 2016-11-22 to 2026-11-23.

New trading days: 1. The common-period tables use only dates available in both snapshots.

## Data differences

| Ticker | Common dates | Max absolute revision | Max relative revision |
|---|---:|---:|---:|
| SPY | 2513 | 0.00021362 | 7.06e-05% |
| TLT | 2513 | 0.00018310 | 1.37e-04% |
| GLD | 2513 | 0.00000000 | 0.00e+00% |

Cells with an absolute revision above 1e-8: 3790 of 7539.

## Main backtest at 95%

| Method | Violations snapshot | Violations fresh | Kupiec p snapshot | Kupiec p fresh | Christoffersen p snapshot | Christoffersen p fresh |
|---|---:|---:|---:|---:|---:|---:|
| Historical | 120 | 120 | 0.0538 | 0.0545 | 0.0017 | 0.0018 |
| Parametric | 114 | 114 | 0.1791 | 0.1808 | 0.0005 | 0.0005 |
| Monte Carlo | 114 | 114 | 0.1791 | 0.1808 | 0.0005 | 0.0005 |

## GARCH refit diagnostics

| Dataset | Refits | Failed fits | alpha < 1e-8 | beta > 0.99 | Max omega / variance |
|---|---:|---:|---:|---:|---:|
| snapshot | 96 | 2 | 2 | 0 | 6.652 |
| fresh_full | 96 | 0 | 3 | 1 | 159.3 |
| fresh_common | 96 | 0 | 3 | 1 | 159.3 |

## Winner rule

| Dataset | Level | Best | Second | Holm p | Clear winner | Decision |
|---|---:|---|---|---:|---|---|
| snapshot | 95% | GARCH(1,1) | EWMA | 0.7039 | False | No clear winner between GARCH(1,1) and EWMA |
| snapshot | 99% | GARCH(1,1) | EWMA | 1.0000 | False | No clear winner between GARCH(1,1) and EWMA |
| fresh_full | 95% | EWMA | Historical 500 | 1.0000 | False | No clear winner between EWMA and Historical 500 |
| fresh_full | 99% | EWMA | GARCH(1,1) | 1.0000 | False | No clear winner between EWMA and GARCH(1,1) |
| fresh_common | 95% | EWMA | Historical 500 | 1.0000 | False | No clear winner between EWMA and Historical 500 |
| fresh_common | 99% | EWMA | GARCH(1,1) | 1.0000 | False | No clear winner between EWMA and GARCH(1,1) |

## Conditional models at 95%

| Model | Violations snapshot | Violations fresh | Δ violations | Mean loss snapshot (bp) | Mean loss fresh (bp) | Δ mean loss (bp) | Rank snapshot | Rank fresh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GARCH(1,1) | 102 | 105 | 3 | 7.83 | 8.71 | +0.87 | 1 | 6 |
| EWMA | 102 | 102 | 0 | 8.08 | 8.09 | +0.01 | 2 | 1 |
| Historical 500 | 120 | 120 | 0 | 8.59 | 8.60 | +0.01 | 3 | 2 |
| Parametric adaptive | 109 | 109 | 0 | 8.62 | 8.63 | +0.01 | 4 | 3 |
| Historical adaptive | 116 | 116 | 0 | 8.63 | 8.64 | +0.01 | 5 | 4 |
| Parametric 500 | 114 | 114 | 0 | 8.63 | 8.64 | +0.01 | 6 | 5 |

### Expected Shortfall at 95%, fresh data

| Model | Mean CVaR | CVaR CI | Mean simulated ES | ES CI |
|---|---:|---|---:|---|
| GARCH(1,1) | 1.5165% | [1.3245%, 1.8136%] | 1.4373% | [1.3564%, 1.5250%] |
| EWMA | 1.3632% | [1.2618%, 1.4813%] | 1.5892% | [1.4605%, 1.7379%] |
| Historical 500 | 1.5635% | [1.5060%, 1.6254%] | 1.5532% | [1.4963%, 1.6145%] |
| Parametric adaptive | 1.3861% | [1.3364%, 1.4398%] | 1.5595% | [1.5019%, 1.6221%] |
| Historical adaptive | 1.5691% | [1.5112%, 1.6324%] | 1.5595% | [1.5019%, 1.6221%] |
| Parametric 500 | 1.3778% | [1.3302%, 1.4285%] | 1.5532% | [1.4963%, 1.6145%] |

### Common-period revision check at 95%

| Model | Violations snapshot | Violations fresh | Δ violations | Mean loss snapshot (bp) | Mean loss fresh (bp) | Δ mean loss (bp) | Rank snapshot | Rank fresh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GARCH(1,1) | 102 | 105 | 3 | 7.83 | 8.70 | +0.87 | 1 | 6 |
| EWMA | 102 | 102 | 0 | 8.08 | 8.08 | +0.00 | 2 | 1 |
| Historical 500 | 120 | 120 | 0 | 8.59 | 8.59 | -0.00 | 3 | 2 |
| Parametric adaptive | 109 | 109 | 0 | 8.62 | 8.62 | -0.00 | 4 | 3 |
| Historical adaptive | 116 | 116 | 0 | 8.63 | 8.63 | +0.00 | 5 | 4 |
| Parametric 500 | 114 | 114 | 0 | 8.63 | 8.63 | +0.00 | 6 | 5 |

## Conditional models at 99%

| Model | Violations snapshot | Violations fresh | Δ violations | Mean loss snapshot (bp) | Mean loss fresh (bp) | Δ mean loss (bp) | Rank snapshot | Rank fresh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GARCH(1,1) | 36 | 37 | 1 | 2.38 | 2.72 | +0.35 | 1 | 2 |
| EWMA | 42 | 42 | 0 | 2.56 | 2.56 | +0.00 | 2 | 1 |
| Historical 500 | 24 | 24 | 0 | 3.03 | 3.03 | +0.00 | 4 | 4 |
| Parametric adaptive | 40 | 40 | 0 | 3.12 | 3.12 | +0.00 | 6 | 6 |
| Historical adaptive | 27 | 27 | 0 | 2.92 | 2.92 | +0.00 | 3 | 3 |
| Parametric 500 | 40 | 40 | 0 | 3.09 | 3.09 | +0.00 | 5 | 5 |

### Expected Shortfall at 99%, fresh data

| Model | Mean CVaR | CVaR CI | Mean simulated ES | ES CI |
|---|---:|---|---:|---|
| GARCH(1,1) | 1.9708% | [1.7227%, 2.3539%] | 2.0595% | [1.9400%, 2.1907%] |
| EWMA | 1.7614% | [1.6304%, 1.9140%] | 2.3214% | [2.1242%, 2.5505%] |
| Historical 500 | 2.6276% | [2.4695%, 2.8029%] | 2.5492% | [2.3990%, 2.7166%] |
| Parametric adaptive | 1.8015% | [1.7381%, 1.8701%] | 2.5379% | [2.3859%, 2.7109%] |
| Historical adaptive | 2.6068% | [2.4488%, 2.7873%] | 2.5379% | [2.3859%, 2.7109%] |
| Parametric 500 | 1.7916% | [1.7303%, 1.8568%] | 2.5492% | [2.3990%, 2.7166%] |

### Common-period revision check at 99%

| Model | Violations snapshot | Violations fresh | Δ violations | Mean loss snapshot (bp) | Mean loss fresh (bp) | Δ mean loss (bp) | Rank snapshot | Rank fresh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GARCH(1,1) | 36 | 37 | 1 | 2.38 | 2.72 | +0.35 | 1 | 2 |
| EWMA | 42 | 42 | 0 | 2.56 | 2.56 | -0.00 | 2 | 1 |
| Historical 500 | 24 | 24 | 0 | 3.03 | 3.03 | -0.00 | 4 | 4 |
| Parametric adaptive | 40 | 40 | 0 | 3.12 | 3.12 | -0.00 | 6 | 6 |
| Historical adaptive | 27 | 27 | 0 | 2.92 | 2.92 | -0.00 | 3 | 3 |
| Parametric 500 | 40 | 40 | 0 | 3.09 | 3.09 | -0.00 | 5 | 5 |
