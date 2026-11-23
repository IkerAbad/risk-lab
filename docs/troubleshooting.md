# Troubleshooting

## `ModuleNotFoundError: No module named 'risk_lab'`

Install the package in editable mode from the repository root:

```bash
python -m pip install -e ".[dev]"
```

## `FileNotFoundError: data/prices.csv`

Run the commands from the repository root, or pass an explicit path:

```bash
python scripts/make_figures.py --data data/prices.csv
python scripts/data_quality.py --data data/prices.csv
```

## Stooq returns `Access denied`

The Stooq CSV endpoint blocks some networks. The downloader falls back to
Yahoo Finance. The committed `data/prices.csv` is already the Yahoo adjusted
close snapshot, so the offline pipeline does not need Stooq.

## Checksum mismatch after editing the CSV

The snapshot hash is stored in `data/prices.sha256` and in the README. If you
change the CSV on purpose, update the hash, the figures, the tables, the data
quality report and `docs/checksums.sha256`.

## The checksum test fails on Windows

The repository forces LF on CSV, Markdown and checksum files through
`.gitattributes`. Re-checkout the affected files if the working tree was
created before that rule existed:

```bash
git rm --cached -r .
git reset --hard
```

## `ruff format --check` fails

Apply the formatter and commit the result:

```bash
python -m ruff format .
```

## Coverage is below 100%

Add a test for the new branch. The project enforces 100% statement coverage of
`src/risk_lab` in `pyproject.toml`.

## The mutation script reports `PATTERN NOT FOUND`

The source line changed and the mutation list in `scripts/mutation_smoke.py`
is stale. Update the mutation to the new line and run the script again.

## `pip-audit` cannot reach the network

The dependency audit needs network access. It runs in CI. Local offline runs
of `scripts/check_all.py` skip it.

## Matplotlib cannot open a display

Set the headless backend:

```bash
export MPLBACKEND=Agg        # Windows PowerShell: $env:MPLBACKEND="Agg"
```

The scripts already call `matplotlib.use("Agg")` before importing pyplot.

## `data/prices.csv does not match data/prices.sha256`

The canonical snapshot was modified. Restore it from git:

```bash
git checkout -- data/prices.csv
```

Do not refresh it in place. Use `scripts/fetch_live_data.py`, which writes a
dated file under `data/fresh`.

## A fresh file already exists with different content

Yahoo returned different decimals for the same date. Keep the published file,
or rerun with `--force` if the new download is deliberate. Then rerun
`scripts/make_fresh_analysis.py`.

## `fresh checksum not found`

Run `scripts/fetch_live_data.py` first. It writes
`data/fresh/prices_<date>.sha256` next to the CSV.
