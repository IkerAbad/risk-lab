## Summary

Describe the change and why it is needed.

## Checks

- [ ] `python -m pytest -q --cov=risk_lab --cov-report=term-missing` passes.
- [ ] `python -m ruff check .` passes.
- [ ] `python -m ruff format --check .` passes.
- [ ] `python -m mypy src tests scripts` passes.
- [ ] `python -m bandit -r src scripts -q` passes.
- [ ] `python scripts/mutation_smoke.py` passes.

## Data changes

- [ ] The committed CSV and `data/prices.sha256` are unchanged, or the checksum,
      README hash, figures, tables and data quality report were regenerated.

## Notes

Anything else the reviewer should know.
