# pytest-cloudreport

[![PyPI](https://img.shields.io/pypi/v/pytest-cloudreport.svg)](https://pypi.org/project/pytest-cloudreport/)
[![Python](https://img.shields.io/pypi/pyversions/pytest-cloudreport.svg)](https://pypi.org/project/pytest-cloudreport/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Pass-rate trends, flaky-test detection, and duration tracking for your pytest suite — straight from `pytest`, no CI plugin, no YAML edits.**

```bash
pip install pytest-cloudreport
pytest --cloudreport-local
```

Opens a self-contained `cloudreport.html` in your browser. No signup. No account. Nothing leaves your machine.

When you want history to survive across CI runs and developer laptops, point the plugin at **[cloudreport.dev](https://cloudreport.dev)** and every `pytest` invocation uploads automatically.

---

## Why pytest-cloudreport

Every pytest suite past ~50 tests develops the same three problems:

- **Flaky tests that fail once a week.** Impossible to spot from one CI log.
- **Runs that quietly get slower.** Until CI crawls and nobody knows which tests to blame.
- **No memory across machines.** Your local run, your coworker's run, and the last CI run all vanish the moment the process exits.

pytest-cloudreport records every run so the patterns show up on their own.

---

## What you get

| | Local (free, no account) | Hosted — [cloudreport.dev](https://cloudreport.dev) |
| --- | --- | --- |
| Self-contained HTML report | ✅ | ✅ |
| Pass / fail / skip counts, durations, tracebacks | ✅ | ✅ |
| 10-run trend chart | ✅ with `--accumulate` | ✅ |
| Persistent history across CI + developer machines | — | ✅ |
| Flaky test detection across runs | — | ✅ |
| Branch / commit / CI provider auto-tracking | — | ✅ |
| Team dashboards | — | ✅ |
| Web UI + JSON API | — | ✅ |

---

## 30-second start

### Local, no account

```bash
pip install pytest-cloudreport
pytest --cloudreport-local
```

Writes `cloudreport.html` and opens it. Everything stays on your machine.

Want trend charts across your last 10 runs?

```bash
pytest --cloudreport-local --accumulate
```

Each run is appended to `~/.pytest-cloudreport/history.db`.

### Hosted — [cloudreport.dev](https://cloudreport.dev)

Every new account starts on the **Free tier** — no credit card required.

1. Sign up at **[cloudreport.dev](https://cloudreport.dev)** — a default project and API key are created immediately.
2. ```bash
   export PYTEST_CLOUD_API_KEY=pcr_your_key_here
   ```
3. ```bash
   pytest
   ```

Runs appear on the dashboard within seconds. No CI plugin install. No GitHub App. No YAML edits beyond exporting the key.

---

## CI, out of the box

GitHub Actions, GitLab CI, Jenkins, and CircleCI are auto-detected — branch, commit SHA, and run ID are captured with zero configuration.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: pip install -r requirements.txt pytest-cloudreport
- run: pytest
  env:
    PYTEST_CLOUD_API_KEY: ${{ secrets.PYTEST_CLOUD_API_KEY }}
```

The upload runs in a background thread with a 25-second timeout — your build never waits for analytics, and never fails because of them.

---

## Configuration

Values come from environment variables or `pytest.ini`. Environment wins.

| Env var | `pytest.ini` | Default | What it does |
| --- | --- | --- | --- |
| `PYTEST_CLOUD_API_KEY` | `cloudreport_api_key` | — | Project API key. Setting this auto-enables cloud upload. |
| `PYTEST_CLOUD_API_URL` | `cloudreport_api_url` | Production backend | Override for self-hosted or preview deployments. |
| `PYTEST_CLOUD_ENV` | `cloudreport_environment` | `ci` | Environment label attached to every run. |

### CLI flags

- `--cloudreport-local` — generate a self-contained HTML report. **No API key required.** If a key is also configured, the run uploads to the cloud in the same invocation.
- `--accumulate` — with `--cloudreport-local`, append the run to the local history DB so the HTML report shows trends.
- `--cloudreport` — force-enable cloud upload even without `PYTEST_CLOUD_API_KEY` set (warns if the key is missing so failures aren't silent).
- `--cloudreport-verbose` — print upload status (or error) to stdout.

---

## Pricing

Free during early access. Paid pricing launches with **6 months free for early adopters** on any plan.

| | **Free** | **Starter** | **Pro** |
| --- | --- | --- | --- |
| Price | $0 | $24/month | $99/month |
| Projects | 2 | 10 | Unlimited |
| Tests per month | 10,000 | 500,000 | Unlimited |
| History retention | 14 days | 1 year | Unlimited |
| Flaky test detection | ✅ | ✅ | ✅ |
| CI provider auto-detect | ✅ | ✅ | ✅ |
| GitHub Action | ✅ | ✅ | ✅ |
| Team members | 1 | 10 | Unlimited |
| Priority support | — | ✅ | ✅ |

Setup is identical across all tiers — same plugin, same API key.

---

## Privacy

**Sent to the server:** test names, statuses, durations, assertion messages, tracebacks.
**Never sent:** source code, test fixtures, environment variables, or stdout/stderr captured during the run.

---

## Zero runtime dependencies

The plugin depends only on `pytest` and `jinja2`. No SDK, no telemetry library, no background daemon. Uploads use the Python standard library over plain HTTPS.

---

## Support

- Website: **[cloudreport.dev](https://cloudreport.dev)**
- Email: **[support@cloudreport.dev](mailto:support@cloudreport.dev)**
- Issues: [github.com/ahmad212o/pytest-cloudreport/issues](https://github.com/ahmad212o/pytest-cloudreport/issues)

## License

MIT. See [LICENSE](LICENSE).
