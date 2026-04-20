# pytest-cloudreport

A pytest plugin that uploads your test results to
[pytest-cloudreport](https://pytest-cloudreport-production.up.railway.app/)
for analytics, trend tracking, and flaky test detection.

## Install

```bash
pip install pytest-cloudreport
```

## Quickstart

1. Sign up for a free account and create a project:
   <https://pytest-cloudreport-production.up.railway.app/signup>
2. Copy your API key (shown once when the project is created).
3. Export it and run your tests:

```bash
export PYTEST_CLOUD_API_KEY=pcr_your_key_here
pytest
```

Test results appear on your dashboard within seconds. No CI plugin install or
GitHub app required — the plugin posts results from wherever `pytest` runs.

## Configuration

Values can come from environment variables or `pytest.ini`. Environment takes
precedence.

| Env var | `pytest.ini` | Default | What it does |
| --- | --- | --- | --- |
| `PYTEST_CLOUD_API_KEY` | `cloudreport_api_key` | — | Project API key. Setting this auto-enables the plugin. |
| `PYTEST_CLOUD_API_URL` | `cloudreport_api_url` | Production backend | Override for self-hosted or preview deployments. |
| `PYTEST_CLOUD_ENV` | `cloudreport_environment` | `ci` | Environment label attached to every run. |

### CLI flags

- `--cloudreport` — force-enable upload even without `PYTEST_CLOUD_API_KEY`
  set (surfaces a warning so missing keys aren't silent).
- `--cloudreport-verbose` — print upload result or error to stdout.
- `--cloudreport-local` — generate a local HTML report instead of uploading.
  No API key required.
- `--accumulate` — with `--cloudreport-local`, append this run to
  `~/.pytest-cloudreport/history.db` so the HTML report shows trends.

## Privacy

The plugin sends test names, statuses, durations, assertion messages, and
tracebacks. It does **not** send source code, test fixtures, environment
variables, or stdout/stderr captured during the run.

## License

Proprietary. See LICENSE for details.
