# Local demonstration — IssueBoard

This walkthrough uses **sample data only**. Do not put real passwords, client records or private screenshots in the repository.

## 1. Start the app on Windows

```powershell
git clone https://github.com/kurapikac2/IssueBoard.git
cd IssueBoard
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000`. The first run creates `data/issueboard.sqlite3`, which is excluded from Git.

## 2. Demonstrate the business flow

1. Select **Register**. Create a throwaway local account with a unique username and password of at least 10 characters, then sign in.
2. Create a project named **Portfolio website**.
3. Create an issue named **Fix mobile navigation**, type **Bug**, priority **High**, status **Open**.
4. Create another issue named **Write deployment guide**, type **Task**, priority **Medium**, status **Open**.
5. Verify the project counters: **Total 2**, **Open 2**.
6. Open **Fix mobile navigation** and change its status to **In Progress**. The history should show the old and new status.
7. Search for **mobile** and filter by **High** priority, then clear filters. Confirm the issue list and project-wide metrics behave independently.
8. Change the issue status to **Done**. Confirm the history includes the second transition.
9. Attempt to delete **Write deployment guide** and cancel in the confirmation prompt; the issue should remain.
10. Delete that sample issue after confirming the prompt; check the project metrics.
11. Sign out. A previously accessible project URL should no longer return private data through the API.

This is an instruction to **verify** behavior, not a claim that every browser interaction was tested here.

## 3. Run automated tests

Open a second terminal in the project directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m pip check
```

If Node.js is installed:

```powershell
node --check app/static/app.js
```

The GitHub Actions workflow runs these checks for new commits and pull requests. The database for tests is isolated from the local application database.

## 4. Visual verification before adding screenshots

Use [the manual QA checklist](MANUAL_QA.md) and check at least:

- Desktop at 1440×900.
- Mobile at 390×844 and 320×640.
- Keyboard navigation (Tab / Shift+Tab / Enter / Escape).
- Form errors, loading indicators, long text and empty lists.
- Login, logout and an independent second browser session.

Only add screenshots after this actual browser check. Use the disposable sample account; never show cookies, tokens, private information or browser developer tools.

## 5. Explain it in an interview

Be ready to answer:

- Why use FastAPI and SQLite for this scope?
- Where is user ownership enforced?
- Why does a session cookie not contain the password?
- Why do state-changing requests need CSRF protection?
- How do the issue update and history insert stay consistent?
- What would you change first for a publicly hosted multi-user version?

See [architecture](ARCHITECTURE.md) for the exact implementation and trade-offs.
