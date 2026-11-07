# IssueBoard

Учебный portfolio project для учёта ошибок и задач в небольших программных проектах.
Backend: Python + FastAPI, база: SQLite, frontend: HTML/CSS/JavaScript без сборщика.

## Возможности

- Регистрация, вход и выход; Argon2id hashes вместо паролей в базе.
- Личные проекты, доступные только владельцу.
- Issues: название, описание, bug/task, low/medium/high, open/in_progress/done.
- Создание, редактирование, смена статуса и удаление после подтверждения.
- Поиск по названию без учёта регистра, в том числе на кириллице.
- Одновременные фильтры статуса и приоритета, сортировка по updated_at.
- История статусов: пользователь, предыдущий и новый статус, время в UTC.
- Показатели всего проекта: всего, открыто, в работе, завершено.
- Адаптивная CSS сетка, сообщения пустых списков, ошибок форм и соединения.

История начинается с записи «Создано → начальный статус». Изменение только названия
не добавляет запись истории статусов. Удаление issue удаляет и его историю.
Показатели проекта не меняются при применении фильтров списка.

## Быстрый запуск: Windows PowerShell

Понадобится Python 3.11+ с pip. Фактически проверено на Python 3.14.8 / Windows.

Откройте PowerShell в папке IssueBoard:

~~~powershell
cd .\IssueBoard
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

Откройте http://127.0.0.1:8000 . Остановка — Ctrl+C.
Если .venv уже создан, пропустите команду создания. Активация окружения
не нужна: поэтому не требуется менять PowerShell ExecutionPolicy.
Если порт занят, используйте --port 8001 и соответствующий URL.

Сначала нажмите «Зарегистрироваться», затем войдите. Имя пользователя:
3–32 символа, латиница, цифры и _. Пароль: 10–128 символов.
Имена пользователей сохраняются в нижнем регистре.

Для воспроизводимого окружения разработки вместо requirements.txt можно установить
requirements-lock.txt: там закреплены и прямые, и транзитивные зависимости
фактически проверенного Windows / Python 3.14 окружения, включая тестовые инструменты.

## Переменные окружения

Задавайте в том же окне PowerShell **до** запуска сервера:

~~~powershell
$env:ISSUEBOARD_DB = "data/issueboard.sqlite3"
$env:ISSUEBOARD_COOKIE_SECURE = "false"
$env:ISSUEBOARD_SESSION_HOURS = "24"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| ISSUEBOARD_DB | data/issueboard.sqlite3 | Файл SQLite; относительный путь считается от корня проекта |
| ISSUEBOARD_COOKIE_SECURE | false | true — cookie отправляется только по HTTPS |
| ISSUEBOARD_SESSION_HOURS | 24 | Срок session от 1 до 168 часов |

.env.example — справочный пример; приложение **не загружает .env автоматически**.
Для локального HTTP оставьте COOKIE_SECURE=false, иначе вход не сохранится.
Для будущего HTTPS окружения нужен COOKIE_SECURE=true.
Общий SECRET_KEY не нужен: sessions используют случайные непрозрачные tokens,
их SHA-256 hashes хранятся в SQLite; raw token находится только в HttpOnly cookie.
CSRF token frontend получает через API. Не помещайте реальные tokens в документацию.

SQLite создаётся при старте через lifespan. Данные сохраняются между запусками,
включая sessions до истечения срока. Каталог data/, .env и .venv исключены из Git.
SQLite содержит чувствительные данные аккаунтов: храните его локально и
не включайте в публичное портфолио. Для резервной копии остановите приложение
и скопируйте весь каталог data, включая возможные WAL/SHM файлы.

## Структура

~~~text
app/
  main.py             app factory, lifespan, обработка ошибок, security headers
  config.py           environment settings
  database.py         схема SQLite, соединения, foreign keys
  dependencies.py     текущая session, CSRF, проверка JSON и Origin
  schemas.py          Pydantic input/output models
  routers/
    auth.py           HTTP auth endpoints
    projects.py       HTTP проекты, issues, history, metrics
  services/
    auth.py           hashes, sessions, ограничение попыток
    board.py          ownership, SQL, transactions, бизнес-правила
    errors.py         ошибки business layer
  static/
    index.html        доступные формы и dialogs
    styles.css        desktop/mobile CSS
    app.js            API requests и безопасное обновление DOM
tests/
  conftest.py         общие fixtures с отдельной временной SQLite
  helpers.py          создание тестовых аккаунтов и issues
  test_core.py        auth, CRUD, ownership, валидация, persistence
  test_extended.py    фильтры, история, показатели, security cases
docs/
  REVIEW.md           результаты и ограничения проверки
  MANUAL_QA.md        сценарий browser проверки
  superpowers/plans/  план и решения
~~~

## Почему так устроено

Router переводит HTTP request в вызов service. Service проверяет владельца,
выполняет SQL и управляет transaction. Валидацией полей занимается Pydantic.
Это позволяет читать поведение без сложных abstractions и тестировать реальный API.

Обычный sqlite3 не требует ORM. Синхронные routes выполняются FastAPI в thread pool.
Каждый request получает отдельное соединение; foreign keys включены для каждого
соединения. UPDATE статуса и INSERT истории выполняются в одной transaction.
BEGIN IMMEDIATE защищает чтение предыдущего статуса от параллельной записи.

Параметры SQL передаются через placeholders. Порядок сортировки выбирается из
фиксированного allowlist. Поиск использует Python casefold: стандартный SQLite
LOWER не обеспечивает полноценный поиск кириллицы без дополнительных расширений.

## API

JSON requests/response. Для изменений после входа нужен X-CSRF-Token из login
или GET /api/auth/session; session cookie браузер передаёт автоматически.
Frontend и API находятся на одном origin.

| Method | URL | Назначение |
| --- | --- | --- |
| POST | /api/auth/register | Создать аккаунт |
| POST | /api/auth/login | Войти и получить CSRF token |
| GET | /api/auth/session | Текущий пользователь и CSRF token |
| POST | /api/auth/logout | Отозвать session |
| GET, POST | /api/projects | Список / создание проектов |
| GET | /api/projects/{id} | Свой проект |
| GET, POST | /api/projects/{id}/issues | Список / создание issues |
| GET, PUT, DELETE | /api/projects/{id}/issues/{issue_id} | Просмотр / замена полей / удаление |
| GET | /api/projects/{id}/issues/{issue_id}/history | История статусов |
| GET | /api/projects/{id}/metrics | Показатели проекта |

PUT заменяет все редактируемые поля. Передавайте title, description, type,
priority и status, чтобы сохранить необходимые значения.
Список принимает q, status, priority, sort=asc или desc (по умолчанию desc).
Пример: /api/projects/1/issues?q=вход&status=open&priority=high&sort=desc

Создание возвращает 201, удаление и logout — 204.
Ошибки: 401 — нужна session, 403 — CSRF/Origin, 404 — ресурс не найден
или принадлежит другому человеку, 409 — занятое имя, 415 — нужен JSON,
422 — неверные поля, 429 — превышен лимит попыток.
OpenAPI доступен по /openapi.json. Swagger UI не подключён, чтобы frontend
не зависел от внешнего CDN и работал с ограничивающим CSP.

## Безопасность

- Argon2id: memory_cost=19456 KiB, time_cost=2, parallelism=1, случайная salt.
- Каждый endpoint проверяет session, project owner и принадлежность issue проекту.
- Чужой и отсутствующий ресурс возвращают одинаковый 404.
- Sessions отзываются при logout и заменяются при повторном входе в том же браузере.
- Cookie: HttpOnly, SameSite=Strict; Secure настраивается для HTTPS.
- CSRF token проверяется на всех авторизованных изменениях.
- JSON-only и Origin проверяются для защиты auth от cross-site requests.
- Auth limit: 20 попыток за 10 минут на IP, хранится в SQLite.
  Ограничиваются и успешные входы, и регистрации; за общим IP лимит общий.
- Ошибки validation не возвращают введённые password/token.
- User content выводится через textContent, а не innerHTML.
- CSP блокирует inline scripts, framing, плагины и внешние ресурсы.
- Нет сохранения auth tokens в localStorage и нет CORS доступа сторонним сайтам.

Рекомендация Argon2id: [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
Подход к тестированию: [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/).

## Проверки

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m pip check
~~~

При установленном Node.js можно отдельно проверить синтаксис JavaScript:

~~~powershell
node --check app/static/app.js
~~~

Node.js не нужен для запуска приложения.
Тесты используют tmp_path, не рабочую базу. В том числе проверяется rollback
изменения issue при реальной ошибке INSERT в историю через SQLite trigger.

Результат запуска 2026-11-07: **33 passed, 1 warning** (5.74s).
Предупреждение Starlette: использование httpx в TestClient deprecated,
в будущем предлагается httpx2. Сейчас тесты выполняются; предупреждение не скрыто.
compileall, node --check и pip check завершились успешно.

## Примеры экранов

Ниже **схемы интерфейса**, а не screenshots выполненного browser теста.
Тексты данных в схемах — обозначения полей, не реальные проекты.

~~~text
ВХОД
IssueBoard                 Войти в IssueBoard
От ошибки к решению.       Имя пользователя [             ]
                          Пароль           [             ]
                          [ Войти ]
                          Зарегистрироваться
~~~

~~~text
ПРОЕКТ: DESKTOP
Мои проекты | Название и описание проекта      [Создать issue]
[название]  | Всего | Открыто | В работе | Завершено
[Создать]   | Поиск [       ] Статус [  ] Приоритет [  ]
            | Название issue | Статус | Приоритет | Обновление
[Выйти]     | Нажмите название, чтобы открыть редактор
~~~

~~~text
ISSUE: DIALOG
Название     [                                ]
Описание     [                                ]
Тип [      ] Приоритет [      ] Статус [       ]
История статусов:
  Создано -> Открыто · автор · время
  Открыто -> В работе · автор · время
[Удалить issue]               [Отмена] [Сохранить]
~~~

На узком экране sidebar становится верхней областью, показатели располагаются
в две колонки, поля редактора — в одну. Это реализовано в CSS; фактическое
поведение на телефоне в текущей среде визуально не проверено.
Chrome отсутствовал, browser host был недоступен, native Zen не предоставил
screenshot/input geometry. Ручной сценарий: [docs/MANUAL_QA.md](docs/MANUAL_QA.md).

## Следующая версия

- Browser E2E tests и настоящие desktop/mobile screenshots после настройки браузера.
- Pagination и поиск в SQLite FTS для больших списков.
- Миграции схемы вместо одного CREATE TABLE IF NOT EXISTS.
- Optimistic locking: сейчас последнее сохранение полей побеждает.
- Редактирование проектов, участники/роли и восстановление удалённых issues.
- Password reset, session management UI и дополнительные лимиты запросов.

Это локальный учебный проект. Deployment не выполнялся.
