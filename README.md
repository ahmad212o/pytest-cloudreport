# pytest-cloudreport

A pytest plugin for test analytics, trend tracking, and flaky test detection.

Two ways to use it: **free local HTML reports** with no account, or
**[pytest-cloudreport.com](https://pytest-cloudreport.com)** for cloud history,
team dashboards, and CI trends.

> **About this repo:** This plugin was extracted from the original
> pytest-cloudreport monorepo in April 2026 and open-sourced under MIT so the
> community can contribute. It is **mature, PyPI-published, and battle-tested**
> — the short git history here reflects only the split, not the amount of work
> behind it. All prior development history lives in the private platform repo.

## Install

```bash
pip install pytest-cloudreport
```

---

## Free — Local HTML Reports (no account)

Zero signup, zero network calls. Run your tests and get a self-contained HTML
report on disk.

### One-off report

```bash
pytest --cloudreport-local
```

Writes `cloudreport.html` in the current directory. Open it in a browser to see
pass/fail counts, durations, and any failing tests with tracebacks.

### Accumulated history (track trends over time)

```bash
pytest --cloudreport-local --accumulate
```

Appends the run to a local SQLite database at
`~/.pytest-cloudreport/history.db` and renders a 10-run trend chart in the HTML
report. Everything stays on your machine.

Use this if you want:
- a human-readable report as a CI artifact
- offline or air-gapped environments
- a try-before-you-sign-up look at what the plugin produces

---

## Cloud — Hosted Dashboard

Sign up once, get persistent history, team dashboards, flaky test detection
across runs, and CI-provider auto-detection.

**Free during early access** — no card, no limits. See the
[pricing page](https://pytest-cloudreport.com) for the Free / Team / Business
breakdown once paid plans launch.

### 5-step quickstart

1. **Sign up** at [pytest-cloudreport.com](https://pytest-cloudreport.com) — a
   default project is created for you.
2. **Copy your API key** (shown once when the project is created; starts with
   `pcr_`).
3. **Install the plugin** — `pip install pytest-cloudreport`.
4. **Set the key:**
   ```bash
   export PYTEST_CLOUD_API_KEY=pcr_your_key_here
   ```
5. **Run your tests:**
   ```bash
   pytest
   ```

Results appear on your dashboard within seconds. No CI plugin install or
GitHub App required — the plugin posts from wherever `pytest` runs.

---

## Configuration

Values can come from environment variables or `pytest.ini`. Environment takes
precedence.

| Env var | `pytest.ini` | Default | What it does |
| --- | --- | --- | --- |
| `PYTEST_CLOUD_API_KEY` | `cloudreport_api_key` | — | Project API key. Setting this auto-enables cloud upload. |
| `PYTEST_CLOUD_API_URL` | `cloudreport_api_url` | Production backend | Override for self-hosted or preview deployments. |
| `PYTEST_CLOUD_ENV` | `cloudreport_environment` | `ci` | Environment label attached to every run. |

### CLI flags

- `--cloudreport-local` — generate a local HTML report. **No API key
  required.**
- `--accumulate` — with `--cloudreport-local`, append this run to
  `~/.pytest-cloudreport/history.db` so the HTML report shows trends.
- `--cloudreport` — force-enable cloud upload even without
  `PYTEST_CLOUD_API_KEY` set (surfaces a warning so missing keys aren't
  silent).
- `--cloudreport-verbose` — print upload result or error to stdout.

---

## Privacy

The plugin sends test names, statuses, durations, assertion messages, and
tracebacks. It does **not** send source code, test fixtures, environment
variables, or stdout/stderr captured during the run.

## License

MIT. See [LICENSE](LICENSE).
