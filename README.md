# IssueBoard

A small issue tracker for personal software projects, built with **FastAPI, SQLite and vanilla JavaScript**.

IssueBoard is a learning project focused on the backend decisions behind a task board: session security, per-user data access, transactional status history and straightforward SQL. It is designed for **local use**, not as a hosted multi-user service.

## What it does

- Register, sign in and sign out. Passwords are hashed with Argon2id.
- Create personal projects and track their bugs and tasks.
- Assign priorities (low / medium / high) and statuses (open / in progress / done).
- Search issue titles, including case-insensitive Cyrillic text; combine status and priority filters.
- See counts by status and a status-change history with actor and UTC timestamps.
- Use a responsive browser interface without a front-end build step.

## Inside the project

| Area | Implementation |
| --- | --- |
| API | FastAPI routers and Pydantic input/output models |
| Business logic | Service functions that enforce ownership and data rules |
| Database | SQLite with foreign keys, SQL placeholders and explicit transactions |
| Authentication | Argon2id passwords and expiring server-side sessions |
| Browser UI | HTML, CSS, plain JavaScript, same-origin API requests |
| Testing | pytest + FastAPI TestClient, with temporary SQLite databases |

[Architecture and important trade-offs](docs/ARCHITECTURE.md) · [Hands-on demo walkthrough](docs/DEMO.md) · [Manual browser QA checklist](docs/MANUAL_QA.md)

## Quick start

**Requirements:** Python 3.11+ and pip. The project was previously reported as tested locally on Python 3.14.8 on Windows.

```powershell
git clone https://github.com/kurapikac2/IssueBoard.git
cd IssueBoard
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Register an account, sign in, and create your first project. Stop the server with Ctrl+C. Using the virtual environment's Python directly avoids changing PowerShell execution policies.

On macOS/Linux, create a virtual environment with `python3 -m venv .venv`, use `.venv/bin/python` instead, and run the same Python modules.

The database is created on first start under `data/issueboard.sqlite3` and remains between runs. That directory and `.env` are ignored by Git.

### Configuration

Environment variables (set before starting):

| Name | Default | Purpose |
| --- | --- | --- |
| `ISSUEBOARD_DB` | `data/issueboard.sqlite3` | Local SQLite database path |
| `ISSUEBOARD_SESSION_HOURS` | `24` | Session lifetime (1–168 hours) |
| `ISSUEBOARD_COOKIE_SECURE` | `false` | Set `true` only when serving over HTTPS |

`.env.example` is a reference only; `.env` is **not** loaded automatically. Do not commit a real database or session cookies.

## Test it

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m pip check
```

If Node.js is available, run `node --check app/static/app.js` to check JavaScript syntax. GitHub Actions checks Python versions and JavaScript syntax on pushes and pull requests.

The previous local review reports **33 passing pytest tests**. The tests include login/logout, ownership boundaries, CSRF, validation, issue filters, state history and a transaction rollback on database failure. See [the review report](docs/REVIEW.md) for its exact scope.

## API overview

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | Create an account |
| POST | `/api/auth/login` | Sign in |
| GET | `/api/auth/session` | Current session |
| POST | `/api/auth/logout` | Sign out |
| GET, POST | `/api/projects` | List/create projects |
| GET | `/api/projects/{id}` | View own project |
| GET, POST | `/api/projects/{id}/issues` | List/create issues |
| GET, PUT, DELETE | `/api/projects/{id}/issues/{issue_id}` | Read/update/delete an issue |
| GET | `/api/projects/{id}/issues/{issue_id}/history` | Status history |
| GET | `/api/projects/{id}/metrics` | Status counts |

OpenAPI JSON: `/openapi.json`. Swagger UI is deliberately disabled.

For authenticated writes, the browser sends an HttpOnly session cookie and an `X-CSRF-Token` returned by the API. Users cannot access someone else's projects or issues through direct URLs.

## Security model and limitations

Passwords use Argon2id. Sessions store SHA-256 hashes of random tokens in SQLite; the raw token is held in an HttpOnly, SameSite=Strict cookie. The API checks ownership and CSRF on changes. HTML is rendered without inserting untrusted issue titles as markup.

**This is a local portfolio application, not a production-ready collaboration system.** It has no password reset, team roles, project sharing, schema migrations or pagination. Concurrent field edits use last-write-wins behavior. Rate limits are IP-based and are not suitable as the only abuse control behind all proxies.

The database holds account data and must stay private. Deployment would require HTTPS configuration, proxy/security review, backup procedures, schema migrations and monitoring.

## Demo and screenshots

Start with the [step-by-step local demo](docs/DEMO.md). GitHub Actions now runs an automated **Chromium end-to-end test** covering registration, project and issue creation, status filters, status history, logout and mobile horizontal overflow. Each browser workflow run uploads actual desktop/mobile screenshots as a temporary `issueboard-browser-evidence` artifact under [Actions](https://github.com/kurapikac2/IssueBoard/actions). These are genuine automated browser captures, **not** a substitute for a separate human visual and cross-browser QA review. Use the [manual browser checklist](docs/MANUAL_QA.md) for that final review.

## Next improvements

- Run a manual desktop/mobile browser pass and capture genuine screenshots using sample data.
- Add versioned SQLite schema migrations.
- Add pagination and a scalable search method for larger datasets.
- Improve edit-conflict handling and session management.

The point of this repository is to show readable code and explicit trade-offs, not to claim a production-ready Jira alternative.
