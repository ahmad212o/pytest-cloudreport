# CHANGELOG


## v0.2.1 (2026-04-26)

### Bug Fixes

- Clean egg-info before build, let PSR produce dist artifacts
  ([`bc5a677`](https://github.com/ahmad212o/pytest-cloudreport/commit/bc5a6773e01033c00175cbcf1c7f0865fb98b3fe))

- Prevent egg-info permission conflict during PSR build
  ([`b12765d`](https://github.com/ahmad212o/pytest-cloudreport/commit/b12765d3de9f043bd4e6702fa280ca045be79c55))


## v0.2.0 (2026-04-26)

### Bug Fixes

- Write step outputs to actual GITHUB_OUTPUT path
  ([`739a0b5`](https://github.com/ahmad212o/pytest-cloudreport/commit/739a0b56d8416e39c345a6ccba6c70c61d4933d4))

The heredoc used <<'PY' (quoted), which suppresses shell variable expansion. Python received the
  literal string "$GITHUB_OUTPUT" as a path, wrote outputs to a throwaway file, and the
  version_check step outputs were never populated — causing every publish step to be skipped.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Align pricing to Free tier, fix per-day → per-month limits
  ([`8c4c551`](https://github.com/ahmad212o/pytest-cloudreport/commit/8c4c551ec4cdf7882f4102ea51fcf00dbc0bacb5))

Removes the "14-day Pro trial" claim (platform launches on Free tier), and corrects the pricing
  table to match cloudreport.dev: tests/month instead of tests/day, and updated Starter/Pro limits
  and history caps.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Rewrite README for conversion
  ([`414507d`](https://github.com/ahmad212o/pytest-cloudreport/commit/414507d3508511ac4d47b8f9ce98baa6f06f17ba))

- Lead with the outcome and a copy-pasteable command instead of the monorepo-split disclaimer. -
  Replace the separate Local/Cloud sections with a side-by-side feature table so readers pick the
  path in one glance. - Add a concrete "three pains" section (flaky tests, silent slowdowns, no
  cross-machine memory) before features. - Fix stale pricing: backend moved to daily buckets in
  migration 0004, so limits are 10k/100k/300k per day (not per month). Pro is not unlimited. - Add
  PyPI / Python / License badges and a zero-dependencies credibility section.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>

- Update free tier limits to 1 project, 5k tests/day, 7-day history
  ([`9367cda`](https://github.com/ahmad212o/pytest-cloudreport/commit/9367cdafb245e32ef5de47e19619e1377e06ea71))

### Features

- Add killswitch, xdist support, tighten upload timeouts
  ([`ad62a06`](https://github.com/ahmad212o/pytest-cloudreport/commit/ad62a068901abb4609bebcb6725011b647d7017f))

- CLOUDREPORT_DISABLE=1 env var hard-disables the plugin - Skip upload on pytest-xdist workers
  (controller only) - Replace single 25s timeout with 2s connect + 5s total - Handle
  pytest-rerunfailures intermediate retry reports - Wrap all hooks in try/except so plugin never
  breaks test runs - Switch to python-semantic-release for automated PyPI versioning - Opt into
  Node.js 24 for GitHub Actions to silence deprecation warning


## v0.1.2 (2026-04-22)

### Chores

- **release**: Prepare 0.1.2 PyPI publishing
  ([`8a469cf`](https://github.com/ahmad212o/pytest-cloudreport/commit/8a469cf6c5ef8c74d3bd4eebb6dc6c4803a16b56))

### Features

- Add soft cloud CTA to local report
  ([`cb6c09e`](https://github.com/ahmad212o/pytest-cloudreport/commit/cb6c09e956c5f05ebdb7d52e4cb5dc033b7dd2c4))


## v0.1.1 (2026-04-20)

### Chores

- Initial public release of pytest-cloudreport plugin
  ([`707fe94`](https://github.com/ahmad212o/pytest-cloudreport/commit/707fe94b29a50771775f9aee1fc6a5f33bdaee56))

Zero-dependency pytest plugin that uploads test results to the pytest-cloudreport dashboard.
  Includes local HTML report mode with trend accumulation for offline use.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>

### Documentation

- Note that plugin was extracted from original monorepo
  ([`b53197a`](https://github.com/ahmad212o/pytest-cloudreport/commit/b53197af24eaa1375a207c7ef804477d0c0d81a5))

Makes clear to first-time visitors that the plugin is mature and PyPI-published; the short git
  history reflects only the April 2026 extraction, not lack of work.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>

- Rebrand to cloudreport.dev and lead description with free local mode
  ([`5d3418b`](https://github.com/ahmad212o/pytest-cloudreport/commit/5d3418b2c6906779258f50308c61f349d321c847))

- Update pyproject description to lead with free local HTML reports, followed by cloud upload to
  cloudreport.dev - Update project URLs (Homepage, Documentation) to cloudreport.dev - Update
  README: point site links to cloudreport.dev, add a Support section with support@cloudreport.dev
  and the issues link

Version stays at 0.1.0 — no code changes.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>

- Restructure README — free local mode first, cloud second
  ([`615dc9c`](https://github.com/ahmad212o/pytest-cloudreport/commit/615dc9c69e554741d7014bc51c247af7535e14a4))

Lead with the zero-signup local HTML report so first-time visitors from PyPI can try the plugin
  without committing to an account. Cloud becomes the upgrade path. Also fix stale Railway URL and
  Proprietary license text (repo is MIT).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
