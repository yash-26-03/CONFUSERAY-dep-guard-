# ConfuseRay (dep-guard)

A static scanner that detects **dependency confusion** vulnerabilities in your projects. It reads dependency manifests (`package.json`, `requirements.txt`, `pom.xml`), checks every declared package against public registries (npm, PyPI, Maven Central), and flags internal package names that also exist publicly — exactly the setup a dependency-confusion attack exploits.

## Why

Dependency confusion attacks happen when an attacker publishes a malicious package on a public registry using the same name as your private/internal package. If your build system isn't locked down, it may pull the attacker's version instead of yours. dep-guard catches this before it hits production.


## Features

- **Multi-ecosystem** — scans npm, PyPI, and Maven dependencies in a single run
- **Risk scoring** — findings are scored and ranked (critical / high / medium / low) based on factors like whether a higher public version exists, missing registry config, and typosquatting signals
- **Typosquatting detection** — flags dependencies whose names are suspiciously similar to your internal packages (Levenshtein distance)
- **Registry config checks** — warns when `.npmrc`, `pip.conf`, or `settings.xml` are missing
- **Multiple output formats** — console, JSON, Markdown, and [SARIF 2.1](https://sarifweb.azurewebsites.net/) (for GitHub Code Scanning)
- **MongoDB storage** — optionally persist scan reports to MongoDB for historical tracking
- **Dashboard** — built-in web dashboard with trend charts and scan history
- **CI/CD ready** — exits with non-zero status when findings exceed your severity threshold
- **Offline mode** — scan against a local registry cache when network access isn't available


## Installation

```bash
# clone and install in editable mode
git clone https://github.com/yash-26-03/ConfuseRay.git
cd ConfuseRay
pip install -e .
```

**Requirements:** Python ≥ 3.8, `requests` ≥ 2.28.0.


## Quick Start

### 1. Create a config file

List your internal/private packages so dep-guard knows what to watch for:

```bash
depguard init > depguard.config.json
```

Edit the generated file:

```json
{
  "internal_scopes": ["@yourcompany"],
  "internal_packages": [
    "yourcompany-utils",
    "yourcompany-auth"
  ],
  "ecosystems": ["npm", "pypi", "maven"],
  "fail_on": "high",
  "warn_unpinned": false
}
```

| Field              | Description |
|--------------------|-------------|
 `internal_scopes` -> npm scope prefixes (e.g. `@acme`) treated as internal 
 `internal_packages` -> Exact package names treated as internal 
 `ecosystems` -> Which registries to check (`npm`, `pypi`, `maven`) 
 `fail_on` -> Minimum severity to trigger a non-zero exit (`critical`, `high`, `medium`, `low`) 
 `warn_unpinned` -> Also report dependencies without pinned versions 

### 2. Scan a project

```bash
depguard scan ./my-project --config depguard.config.json
```

### 3. Generate reports

```bash
depguard scan ./my-project \
  --config depguard.config.json \
  --report-json report.json \
  --report-md report.md \
  --report-sarif report.sarif
```


## CLI Reference

```
depguard <command> [options]

Commands:
  scan        Scan a project directory for dependency confusion risks
  init        Print a starter config to stdout
  dashboard   Launch the scan-history web dashboard
```


### `depguard scan`

```
depguard scan <path> -c <config> [options]

Required:
  path                  Project root to scan
  -c, --config          Path to internal-package config (JSON)

Options:
  --report-json FILE    Write findings as JSON
  --report-md FILE      Write findings as Markdown
  --report-sarif FILE   Write findings in SARIF 2.1 format
  --fail-on LEVEL       Override fail severity (critical|high|medium|low)
  --warn-unpinned       Also flag unpinned dependency versions
  --offline             Use local registry cache instead of live HTTP
  -q, --quiet           Suppress progress output
```


### `depguard dashboard`

```
depguard dashboard [options]

Options:
  --reports-dir DIR     Directory of JSON report files (default: ./reports)
  --port PORT           Port to serve on (default: 8085)
  --no-open             Don't auto-open browser
  --mongo-uri URI       Read reports from MongoDB
```


## Exit Codes

| Code        | Meaning |
|-------------|---------|
 `0` -> Clean — no findings above threshold 
 `1` -> Findings detected at or above the `fail_on` severity 
 `2` -> Error — bad config, missing files, network failure, etc. 


## Risk Scoring

Each finding is assigned a numeric risk score based on these factors:

| Factor                       | Points |
|------------------------------|--------|
 Package is in internal scope ->   +3 
 Public package exists on registry ->   +4 
 Public version is higher than declared ->   +5 
 No registry config protection ->   +2 
 Typosquatting detected ->   +4 

Scores map to severities: **critical** (≥12), **high** (≥8), **medium** (≥4), **low** (<4).


## CI/CD Integration

### GitHub Actions

A workflow is included at `.github/workflows/depguard.yml`:

```yaml
name: dep-guard scan

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: |
          depguard scan . \
            --config depguard.config.json \
            --report-md report.md \
            --report-json report.json \
            --fail-on high
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: depguard-report
          path: |
            report.md
            report.json
```


### Pre-commit Hook

```bash
cp scripts/pre-commit-hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

This runs `depguard scan` on every commit and blocks if high/critical findings are detected.


## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

