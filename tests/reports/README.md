# Test Reports

This folder stores timestamped markdown reports generated from test runs.

## Layout

- scripts/: report generation scripts
- templates/: markdown templates used by the generator
- history/: generated reports, one file per run

## Usage

Run the generator from the repository root:

```bash
bash tests/reports/scripts/generate_report.sh
```

The script creates a new markdown file under history/ using the current UTC time.

If no API base URL is supplied, reports default to https://fit5120-tm11.onrender.com.
