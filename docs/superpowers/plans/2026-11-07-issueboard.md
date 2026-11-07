# IssueBoard Implementation Plan

**Goal:** учебное приложение для личных проектов и issues.
**Architecture:** FastAPI routers -> services -> sqlite3. HTML/CSS/JS same-origin frontend.
**Tech Stack:** Python 3.11+, FastAPI, SQLite, Argon2id, pytest, httpx.

## Constraints
Никакого deployment. Данные в локальном файле, не в Git. Пользователь работает только со своими данными.
Passwords не попадают в responses или logs; JSON only и CSRF для изменений.

## Tasks
- [x] Auth и проекты: app/config.py, database.py, dependencies.py, schemas.py,
  services/auth.py, services/board.py, routers/auth.py, routers/projects.py.
  Проверки: register, duplicate username, login, logout, чужие ресурсы.
- [x] Issues CRUD и frontend: app/static/index.html, styles.css, app.js.
  Проверки: create, PUT, DELETE, валидация; подтверждение удаления в UI.
- [x] Filters, history, metrics: title casefold search, allowlisted sort, SQL filters.
  Проверки: combined filters, timestamps, no-op status, actor, audit atomicity.
- [ ] Review и README: pytest, compileall, browser desktop/mobile и сценарий CRUD.

## Review focus
Cross-user access to every nested endpoint; SQL injection in title search;
rejected secrets in validation responses; expired/revoked sessions; Unicode titles.
Tests use tmp_path SQLite and never touch the default database.

## Design decisions
Обычный sqlite3 вместо ORM снижает число зависимостей и делает SQL видимым.
Sessions хранят hash случайного token; CSRF token доступен frontend только через API.
Argon2id: 19 MiB, 2 iterations, parallelism=1. Cookies HttpOnly и SameSite=Strict.
SQLite update + status audit выполняются в одной serialized transaction.
История создания содержит NULL -> initial status. Удаление issue удаляет его историю.
Дизайн Swiss: white, Helvetica/Arial, blue #002FA7, hairline grid.
Verification: pytest 33 passed, 1 warning. Syntax checks and pip check passed. Browser visual QA blocked by unavailable browser tooling; see docs/REVIEW.md.
