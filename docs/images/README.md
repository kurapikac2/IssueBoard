# Capture provenance

Captured 2026-11-09 using Playwright 1.56.1 / Chromium 141.0.7390.37 on Windows. Application source is the existing `bdb20a3bc357275791cb616b9f4d9558c1535b5a`; this branch changes documentation and the test capture timing only. The SQLite file is a separate ignored demo database, not an existing user's database.

- `issueboard-desktop.png`: 1440×900 viewport.
- `issueboard-mobile.png`: 390×844 viewport, full-page capture.

The generated `portfolio_...` username, "Portfolio website" project and "Fix mobile navigation" task are fictional test fixtures. The captures are copied directly from Playwright output without image editing. The transient notification is allowed to dismiss itself before capture.

## Reproduction

1. Start the real app on `http://127.0.0.1:8000` with `ISSUEBOARD_DB` pointing to a dedicated demo SQLite path.
2. Run `npm ci --prefix e2e`, then `cd e2e; npx playwright install chromium`.
3. From the repository root run `npx --prefix e2e playwright test e2e/issueboard.spec.cjs --browser=chromium --reporter=line` (or the installed executable under `e2e/node_modules/.bin`).
4. Review PNGs under ignored `test-results/` before copying selected images here.

The workflow verifies registration/login, project and issue creation, combined filters, status/history/metrics, mobile overflow and logout. Local result: **one complete browser test passed**, plus **33 pytest tests passed**. These counts describe software behavior, not accessibility certification. The updated browser dependency lockfile enables `npm ci` in CI. The local dependency advisory check reported no known vulnerabilities in the 18 resolved runtime packages; the full-history Gitleaks scan found no secrets.
