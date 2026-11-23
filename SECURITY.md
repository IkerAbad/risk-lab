# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.2.x | Yes |
| 0.1.x | No |

## Reporting a vulnerability

Use GitHub private vulnerability reporting:

https://github.com/IkerAbad/risk-lab/security/advisories/new

Do not open a public issue with exploit details. If private reporting is not
available, open an issue that describes the affected component without
sensitive information and ask for a private channel.

Include the version, the operating system, the Python version, the steps to
reproduce the problem and the impact.

## Scope

The package reads local CSV files and performs numerical calculations. The
downloader makes HTTP requests to fixed HTTPS endpoints at Stooq and Yahoo
Finance. The project does not handle credentials, personal data or user
accounts.

The most relevant risks are therefore:

- A malicious or corrupted input CSV.
- A dependency vulnerability.
- A regression in the numerical code that produces wrong risk figures.

The test suite covers input validation, the committed snapshot checksum, the
estimators, the backtest, the statistical tests and the plotting code. CI runs
Bandit and `pip-audit`. CodeQL scans the repository on every push and pull
request. Dependabot keeps the actions and the Python dependencies current.

## Response

This is a personal project. Reports are handled on a best-effort basis. There
is no guaranteed response time.
