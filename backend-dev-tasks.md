# Задачи для Backend-разработчика — PsychoGraph

Дата выдачи: 2026-04-27. Этот документ — самодостаточный, всё, что нужно для работы, прямо здесь.

---

## 1. Что за проект

PsychoGraph — веб-платформа психодиагностики сотрудников через чат. Сотрудник проходит опрос анонимно по invite-ссылке от HR; NLP-сервис конвертирует развёрнутые тексты ответов в числовые шкалы 0–100; HR видит агрегированную аналитику. Принципиальное требование — **тексты ответов сотрудников нигде не сохраняются**, ни в БД, ни в логах, ни в ответах API. Тексты живут только в Redis-очереди до обработки NLP, потом стираются. В БД — только числа по шкалам.

Состав:
- **Backend (FastAPI)** — основной API: auth, методики, опросы, аналитика. Это твоя зона.
- **NLP-сервис (отдельный FastAPI)** — микросервис в `nlp_service/` с ruBERT. Им занимается другой человек.
- **Frontend (React + Vite)** — `src/`. Им занимается другой человек.
- **Celery worker** — фоновая обработка ответов через NLP.
- Postgres 16, Redis 7, MinIO (S3-совместимый сторадж).

Роли пользователей в системе:
- `respondent` — анонимный сотрудник, без аккаунта, по invite-ссылке.
- `researcher` — HR, регистрируется по email/паролю (или по invite от админа).
- `admin` — управляет методиками и пользователями.
- `pending` — зарегистрировавшийся сам, но без подтверждённой роли researcher (одобряет админ).

---

## 2. Технический стек backend

- **Python 3.12** + **FastAPI 0.115** (async)
- **SQLAlchemy 2.0** (async, декларативный синтаксис) + **asyncpg 0.30**
- **Alembic 1.13** — миграции, async-mode, уже инициализирован
- **Pydantic 2.9** + **pydantic-settings 2.5**
- **python-jose** — JWT (HS256)
- **bcrypt** — пароли, rounds=12
- **slowapi** — rate-limiting на Redis
- **email-validator**, **python-dotenv**
- **cryptography** (Fernet) — для шифрования профилей (понадобится позже)
- **httpx** — клиент к NLP-сервису
- **Celery 5** + **Redis 7** — очереди
- **pytest 8.3**, **ruff 0.6.9**, **mypy 1.11** — тулчейн (уже стоит)

Versions зафиксированы в `backend/requirements.txt` и `backend/requirements-dev.txt`.

---

## 3. Архитектура backend (как в Sota — наш референс)

Слоёная: `router → service → repository → model`. Не используй сырой `HTTPException` в сервисах — у нас есть набор кастомных исключений (см. TASK-013), кидаешь их, FastAPI-handler превратит в правильный JSONResponse.

Структура папок:

```
backend/
  app/
    main.py                    # FastAPI app, mount routers, exception handlers
    core/
      config.py                # Pydantic Settings (УЖЕ ЕСТЬ — твоё дело только пользоваться)
      exceptions.py            # 8 кастомных исключений + handlers (TASK-013, твоё)
      security.py              # bcrypt + JWT + CSRF (TASK-012, твоё)
      limiter.py               # slowapi.Limiter (создашь в TASK-018)
      redis.py                 # async Redis client (если понадобится; в auth-цепочке — нет)
    db/
      models.py                # Base + User + Session + AuditLog (TASK-011, твоё). Base УЖЕ ЕСТЬ
      session.py               # async engine + sessionmaker (УЖЕ ЕСТЬ, не трогай)
      repository.py            # BaseRepository[T] (TASK-014, твоё)
      repositories.py          # UserRepository, SessionRepository, AuditLogRepository (TASK-014)
    schemas/
      auth_schemas.py          # Pydantic-модели запросов/ответов (TASK-015, твоё)
    services/
      auth_service.py          # Бизнес-логика auth (TASK-016, твоё)
      audit_service.py         # AuditService (TASK-020, твоё)
    api/
      deps.py                  # DI: get_db, get_current_user, require_role и т.д. (TASK-017, твоё)
      routers/
        auth.py                # /api/auth/* (TASK-018, твоё)
        admin/
          invitations.py       # POST /api/admin/invitations (TASK-019, твоё)
    tasks/
      celery_app.py            # Celery (УЖЕ ЕСТЬ, не трогай)
  migrations/
    env.py                     # async, импортирует Base.metadata (УЖЕ настроен)
    versions/                  # сюда лягут твои миграции
  tests/
    conftest.py                # env-vars setdefault (УЖЕ ЕСТЬ)
    test_health.py             # smoke-тесты (УЖЕ ЕСТЬ)
    test_auth_*.py             # тесты, которые ты добавишь
  alembic.ini                  # настроен, sqlalchemy.url подставляется из Settings
  pyproject.toml               # ruff/mypy/pytest конфиг
  requirements.txt             # prod deps
  requirements-dev.txt         # ruff/mypy/pytest/httpx
```

---

## 4. Что уже сделано (на 2026-04-27)

Когда ты подключаешься к проекту, в нём уже:

- **Каркас FastAPI** в `backend/app/main.py`. Эндпоинт `GET /health` и его alias `GET /api/health` отвечают `{"status":"ok","nlp_service":"..."}`.
- **Settings** в `backend/app/core/config.py`. Поля: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `ENCRYPTION_KEY`, `CSRF_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `NLP_SERVICE_URL`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`. Импортируется как `from app.core.config import settings`. Все обязательные поля валидируются через `Field(..., min_length=1)` — пустое значение или отсутствие в `.env` ронит старт.
- **Async SQLAlchemy 2.0**: `app/db/session.py` — `engine` (async) + `AsyncSessionLocal`. `app/db/models.py` — пустой `Base(DeclarativeBase)` (твоя задача — наполнить).
- **Alembic** в async-режиме. Уже есть пустая initial-миграция (`e5a4b77dd748_init.py`). `migrations/env.py` подменяет `sqlalchemy.url` из Settings.
- **Тулчейн**: `ruff`, `mypy` (с `pydantic.mypy` plugin), `pytest`. Конфиг в `pyproject.toml`.
- **Smoke-тесты**: `tests/test_health.py` (2 теста). `tests/conftest.py` ставит env-vars через `os.environ.setdefault` до импорта `app`, чтобы Settings не падал.
- **CI**: `.github/workflows/ci.yml` с 4 jobs (`no-text-storage` / `backend` / `frontend` / `docker-build`), триггеры `pull_request` + `push: main`. На GitHub workflow ещё не запускался (репо без remote), но команды все работают локально.
- **No-text-storage check**: `scripts/check-no-text-storage.sh` — bash-скрипт, exit 1 при совпадении паттернов в `migrations/` и `backend/app/db/`. Подключён в CI и через `.pre-commit-config.yaml` (активируется `pre-commit install` после `git init`).
- **docker-compose**: 7 сервисов (postgres, redis, minio, backend, nlp_service, celery_worker, frontend) + опциональный mailhog. Запускается локально, всё healthy.

---

## 5. Зона твоей ответственности

**Создаёшь / правишь свободно:**

- `backend/app/core/exceptions.py`, `backend/app/core/security.py`, `backend/app/core/limiter.py` — твои файлы целиком.
- `backend/app/db/models.py` — добавь enum-ы, классы `User`, `Session`, `AuditLog`. `class Base(DeclarativeBase)` уже там, не трогай его.
- `backend/app/db/repository.py`, `backend/app/db/repositories.py` — твои.
- `backend/app/schemas/auth_schemas.py` — твоё.
- `backend/app/services/auth_service.py`, `backend/app/services/audit_service.py` — твоё.
- `backend/app/api/deps.py` — твоё.
- `backend/app/api/routers/auth.py` — твоё.
- `backend/app/api/routers/admin/invitations.py` — создаёшь папку `admin/` (с `__init__.py`) и файл.
- `backend/migrations/versions/*.py` — твои миграции (auto-generate).
- `backend/tests/test_*.py` — тесты под auth.
- `backend/app/main.py` — добавляешь только: регистрацию exception-handlers (TASK-013) и `app.include_router(auth_router, prefix="/api/auth")` (TASK-018), `app.include_router(invitations_router, prefix="/api/admin")` (TASK-019). Не переписывай файл целиком.
- `backend/requirements.txt` / `requirements-dev.txt` — добавляй зависимости, если действительно понадобятся (`python-jose[cryptography]`, `bcrypt`, `slowapi`, `email-validator` — точно понадобятся).

**НЕ трогай:**

- `nlp_service/` — другая команда.
- `src/` (frontend) — другая команда.
- `backend/app/core/config.py` — Settings уже стоит. Если нужно новое поле — спроси, не добавляй в одиночку.
- `backend/app/db/session.py` — engine уже работает, твои репозитории просто получают `AsyncSession` через DI.
- `backend/app/tasks/celery_app.py` — Celery, не auth.
- `backend/migrations/env.py`, `backend/alembic.ini`, `backend/pyproject.toml` — настройки уже стоят.
- `docker-compose.yml`, `Dockerfile`, `.github/workflows/ci.yml`, `scripts/check-no-text-storage.sh`, `.pre-commit-config.yaml` — инфраструктура. Если точно нужно править — спроси.

---

## 6. Правила и конвенции

### Без комментариев в коде

Не пиши комментарии, docstring, inline-notes. Понятные имена + короткие функции + типы делают код читаемым без комментариев. Если кажется, что комментарий действительно нужен (workaround под баг, скрытый инвариант, неочевидный edge-case) — спроси разрешения, не добавляй молча.

### Кастомные исключения вместо HTTPException

В сервисах **никогда не используй** `raise HTTPException(...)` напрямую. Вместо этого кидай свои исключения из `app/core/exceptions.py` (TASK-013):

```python
# плохо
raise HTTPException(status_code=404, detail="Пользователь не найден")

# хорошо
raise NotFoundError("Пользователь не найден")
```

FastAPI-handler из `main.py` превратит исключение в правильный JSONResponse. Это позволяет менять формат ошибок централизованно и не плодить magic numbers по коду.

### Сообщения для пользователя — на русском

`detail` в ответах API, тексты в email, в audit-логе человекочитаемая часть — на русском. Идентификаторы, имена функций, ключи enum-ов, технические термины — на английском.

```python
raise NotFoundError("Пользователь не найден")
raise AuthenticationError("Неверный email или пароль")
raise ConflictError("Email уже используется")
```

### Async везде

- Сервисы, репозитории, эндпоинты — всё `async def`.
- БД — через `AsyncSession`, не sync.
- HTTP-клиент к NLP — через `httpx.AsyncClient` (когда дойдёт до Celery-таска).

### Никаких текстов ответов в БД

Запрещены поля с именами `answer_text`, `response_text`, `user_text`, `raw_answer`, `raw_response`, `message_body`, `chat_message`. CI это проверяет автоматически (`scripts/check-no-text-storage.sh`). Если PR содержит миграцию или модель с таким именем — workflow упадёт.

В auth-цепочке таких полей не должно быть в принципе, но если случайно заведёшь, например `password_text` — переименуй (`password_hash` уже корректно).

### Naming convention

- Python: `snake_case` для функций/переменных, `PascalCase` для классов, `UPPER_SNAKE_CASE` для констант.
- Файлы: `lowercase_with_underscores.py`.
- Имена эндпоинтов: `/api/auth/login`, `/api/admin/invitations` — kebab-case в URL, slash-separated.
- Поля БД: `snake_case`, FK: `<entity>_id` (например, `user_id`, `session_id`).
- Pydantic-схемы: `RegisterRequest`, `TokenResponse` — Request/Response суффиксы.

### Pydantic-модели — `BaseModel`, не `dataclass`

```python
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str
    last_name: str
    invite_token: str | None = None
```

### Без backwards-compatibility shims

Не добавляй `# deprecated`, не оставляй старые поля «на всякий случай». Меняешь — меняешь полностью. Если случайно что-то сломалось — фикси сразу, не оставляй TODO.

---

## 7. Окружение и команды

### Установка

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

### Запуск всего стека (через docker)

```bash
# Postgres / Redis / MinIO / NLP / frontend / celery / backend
docker compose up -d

# Опц. mailhog для проверки email-флоу
docker compose --profile dev-email up -d mailhog
```

Хост-порты на этой машине сдвинуты (стандартные 5432/8000/5173 заняты соседними проектами):

| Сервис | Хост → Контейнер |
|---|---|
| postgres | 5434 → 5432 |
| redis | 6379 → 6379 |
| minio | 9000+9001 |
| backend | 8010 → 8000 |
| nlp_service | 8001 |
| frontend | 3000 → 5173 |
| mailhog | 1025 (SMTP) + 8025 (UI) |

В контейнерной сети — стандартные порты (`postgres:5432`, `backend:8000`).

### Запуск backend локально (без docker)

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Backend подключится к Postgres на `localhost:5434` (URL уже в `backend/.env`).

### Postgres / Redis

```bash
# psql внутри контейнера
docker exec -it psychograph_postgres psql -U postgres -d psychograph

# psql с хоста
psql -h localhost -p 5434 -U postgres -d psychograph

# redis
docker exec -it psychograph_redis redis-cli
```

### Тесты + lint + типы

```bash
cd backend
.venv/bin/ruff check .                  # линт
.venv/bin/ruff check --fix .            # авто-фикс простых проблем
.venv/bin/mypy app/                     # типы
.venv/bin/pytest                        # тесты
.venv/bin/pytest tests/services/test_auth_service.py -v  # точечно
```

### Миграции (alembic)

```bash
cd backend
# после правки моделей — сгенерируй миграцию
.venv/bin/alembic revision --autogenerate -m "add user session audit"

# проверь содержимое migrations/versions/<rev>_add_user_session_audit.py
# — должны быть op.create_table('users', ...), op.create_table('sessions', ...), и т.д.
# — если что-то лишнее или неверное — поправь файл руками

# применить
.venv/bin/alembic upgrade head

# откатить последнюю
.venv/bin/alembic downgrade -1

# проверить текущую версию
.venv/bin/alembic current
```

### No-text-storage check

```bash
# из корня репо
bash scripts/check-no-text-storage.sh
```

### Полная локальная CI-симуляция (запусти перед коммитом)

```bash
bash scripts/check-no-text-storage.sh && \
  cd backend && \
  .venv/bin/ruff check . && \
  .venv/bin/mypy app/ && \
  .venv/bin/pytest && \
  cd ..
```

---

## 8. Архитектурный контекст для auth

### 8.1. ER-схема (твои таблицы)

```
User
  id (PK)
  email (UQ)
  password_hash
  first_name, last_name
  role: UserRole enum (pending / respondent / researcher / admin)
  status: UserStatus enum (active / blocked)
  email_verified: bool, default false
  email_verification_token: str | None
  password_reset_token: str | None
  failed_login_attempts: int, default 0
  locked_until: datetime | None
  created_at, updated_at: timezone-aware datetime, server_default=func.now()

Session
  id (PK)
  user_id (FK → User.id, nullable=False)
  refresh_token_hash: str (хеш, не plaintext)
  csrf_token: str
  device_info: str | None
  ip_address: str | None
  expires_at: datetime
  is_active: bool, default true
  created_at: timezone-aware datetime

AuditLog
  id (PK)
  user_id (FK → User.id, nullable=True — для анонимных действий)
  action: str
  entity_type: str | None
  entity_id: int | None
  ip_address: str | None
  created_at: timezone-aware datetime
```

### 8.2. Enum-ы (Python)

```python
from enum import Enum

class UserRole(str, Enum):
    PENDING = "pending"
    RESPONDENT = "respondent"
    RESEARCHER = "researcher"
    ADMIN = "admin"

class UserStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
```

(Другие enum-ы для методик/сессий-опросов — не для auth, ими займутся другие задачи.)

### 8.3. JWT и сессии

- **Access-token**: JWT (HS256, секрет `settings.JWT_SECRET`), claim `sub=user_id`, `exp = now + 15 минут`. В body ответа `/login` и `/refresh`.
- **Refresh-token**: JWT, claim `sub=user_id`, `session_id`, `exp = now + 7 дней`. В **httpOnly Secure SameSite=Strict cookie**, не в body. Хеш сохранён в `Session.refresh_token_hash`.
- **Access-token хранится клиентом в памяти JS** (через React Context во фронте, не в localStorage — XSS-риск).
- **CSRF**: double-submit pattern. На `/login` сервер генерит `csrf_token = secrets.token_urlsafe(32)`, кладёт в `Session.csrf_token` и возвращает в header `X-CSRF-Token`. Фронт хранит этот токен в памяти. На `/refresh` фронт шлёт его в header `X-CSRF-Token`, бэк сверяет с тем, что в `Session`. На остальных эндпоинтах CSRF не нужен — там Bearer Authorization, и Strict-cookie не уйдёт с cross-origin.

### 8.4. Lockout

- 5 неуспешных попыток login подряд → `locked_until = now + 15 минут`.
- При успешном login — `failed_login_attempts = 0`, `locked_until = NULL`.
- При попытке login до `locked_until` — `LockedError` (HTTP 423).

### 8.5. Rate limits (через slowapi на Redis)

| Эндпоинт | Лимит |
|---|---|
| `POST /api/auth/register` | 5/min на IP |
| `POST /api/auth/verify-email` | без лимита (короткое одноразовое действие) |
| `POST /api/auth/login` | 10/min на IP |
| `POST /api/auth/refresh` | 30/min на IP |
| `POST /api/auth/logout` | 30/min на пользователя |
| `GET /api/auth/me` | 100/min на пользователя |
| `POST /api/auth/password-reset-request` | 3/min на IP |
| `POST /api/auth/change-password` | 5/min на IP |
| `POST /api/admin/invitations` | 30/min на пользователя (admin) |

Превышение лимита → 429.

### 8.6. Audit actions (имена для записей в `audit_log.action`)

```
auth.register
auth.login_success
auth.login_failed
auth.logout
auth.email_verified
auth.password_change
auth.password_reset_request
auth.role_change
auth.account_blocked
auth.account_unblocked
```

В audit_log пишутся только **метаданные** (action, user_id, entity_type, entity_id, ip, timestamp). Никаких body, никаких текстов.

### 8.7. Валидация пароля

Регистрация и change-password проверяют:
- длина 8–128 символов
- минимум 1 заглавная буква
- минимум 1 цифра
- минимум 1 спецсимвол (`! @ # $ % ^ & * ( ) _ - + = [ ] { } ; : , . < > ? / | \``)

Реализуй в `RegisterRequest` через `field_validator` Pydantic 2.

### 8.8. Email-verify в MVP (без SMTP)

В прод будет SMTP. На MVP — email с verification ссылкой просто логируется через `logger.info(f"Email verification link for {email}: /api/auth/verify-email?token={token}")`. Опционально — поднимаем mailhog и шлём через него; пока достаточно лог-вывода.

### 8.9. Invite-flow (TASK-019)

- Админ POST `/api/admin/invitations` → бэкенд создаёт JWT с claim `intended_role: "researcher"`, `issued_by: admin_id`, `exp = now + 7 дней`. Подписывает тем же `settings.JWT_SECRET`. Возвращает токен (его HR копирует в реги-ссылку).
- При POST `/api/auth/register` с `invite_token=<jwt>`:
  - валидный → User создаётся с `role=researcher`
  - истёкший / невалидный → `role=pending`

### 8.10. Bcrypt

Rounds=12 (по решению из спеки). Используй `bcrypt` напрямую (не passlib — лишняя зависимость).

```python
import bcrypt

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

---

## 9. Десять задач — порядок и описания

Делай в указанном порядке. Зависимости в скобках — на что опирается задача.

### Задача 1 — TASK-013: `core/exceptions.py` (8 кастомных исключений + handlers)

**Что нужно:**

1. Создай `backend/app/core/exceptions.py` с восемью классами:

| Класс | HTTP | Когда кидать |
|---|---|---|
| `NotFoundError` | 404 | объект не найден |
| `AlreadyExistsError` | 400 | конфликт уникальности на bad-request уровне |
| `AuthenticationError` | 401 | нет/невалидный токен, неверный пароль |
| `ForbiddenError` | 403 | нет прав |
| `ConflictError` | 409 | конфликт состояний (например, email уже занят) |
| `GoneError` | 410 | ресурс удалён/просрочен |
| `UnprocessableError` | 422 | валидация бизнес-правил (за пределами Pydantic) |
| `LockedError` | 423 | аккаунт заблокирован lockout-ом |

Каждый класс — наследник `Exception`, имеет `status_code: int` и `default_message: str` (на русском). Конструктор принимает опциональное сообщение.

```python
class NotFoundError(Exception):
    status_code = 404
    default_message = "Объект не найден"

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)
```

2. В `backend/app/main.py` зарегистрируй FastAPI exception handler для каждого. Один универсальный handler через базовый класс, или 8 отдельных — на твой вкус. Каждый возвращает `JSONResponse({"detail": exc.message}, status_code=exc.status_code)`.

**Acceptance:**
- 8 классов, каждый с `status_code` и сообщением на русском.
- В `app/main.py` зарегистрированы handlers, возвращающие `{"detail": "..."}`.

**Тесты (создай `backend/tests/test_exceptions.py`):**
- Тестовый эндпоинт `@app.get("/_test/notfound")` бросает `NotFoundError("X не найден")` → клиент получает 404 `{"detail": "X не найден"}`.
- Аналогично для каждого из 8.

---

### Задача 2 — TASK-011: модели `User`, `Session`, `AuditLog` + миграция

**Что нужно:**

1. В `backend/app/db/models.py` (там уже есть `class Base(DeclarativeBase)` — оставь его):
   - Добавь enum-ы `UserRole`, `UserStatus` (см. §8.2).
   - Создай классы `User`, `Session`, `AuditLog` по схеме §8.1.
   - SQLAlchemy 2.0 декларативный синтаксис: `id: Mapped[int] = mapped_column(primary_key=True)`.
   - Все datetime — timezone-aware: `Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())`.
   - Для enum'ов: `Mapped[UserRole] = mapped_column(SQLAlchemyEnum(UserRole), default=UserRole.PENDING, nullable=False)`.

2. Сгенерируй миграцию:
   ```bash
   cd backend
   .venv/bin/alembic revision --autogenerate -m "auth_models"
   ```
   Открой получившийся файл в `migrations/versions/` — должны быть `op.create_table('users', ...)`, `op.create_table('sessions', ...)`, `op.create_table('audit_log', ...)`. Если что-то лишнее — поправь руками.

3. Прогон:
   ```bash
   .venv/bin/alembic upgrade head
   docker exec psychograph_postgres psql -U postgres -d psychograph -c '\dt'
   # — должны быть видны users, sessions, audit_log, alembic_version
   ```

4. Проверь, что `bash scripts/check-no-text-storage.sh` из корня репо проходит (exit 0).

**Acceptance:**
- `models.py` содержит `Base`, `User`, `Session`, `AuditLog` со всеми полями из §8.1.
- Enum-ы как в §8.2.
- Миграция создана и применена.

**Тесты:**
- `bash scripts/check-no-text-storage.sh` → exit 0.
- `psql ... -c '\d users'` показывает все колонки.
- `pytest` (существующие smoke-тесты `/health`) — всё ещё зелёные.

---

### Задача 3 — TASK-012: `core/security.py` (bcrypt + JWT + CSRF)

**Что нужно:**

В `backend/app/core/security.py` реализуй функции:

```python
def hash_password(plain: str) -> str: ...                # bcrypt rounds=12
def verify_password(plain: str, hashed: str) -> bool: ...
def create_access_token(user_id: int) -> str: ...         # JWT, exp=now+15min, sub=user_id
def create_refresh_token(user_id: int, session_id: int) -> str: ...  # JWT, exp=now+7d
def decode_token(token: str) -> dict: ...                 # → claims; AuthenticationError если невалиден/истёк
def create_csrf_token() -> str: ...                       # secrets.token_urlsafe(32)
```

JWT через `python-jose` (HS256, секрет из `settings.JWT_SECRET`). Сроки через `settings.ACCESS_TOKEN_EXPIRE_MINUTES` и `settings.REFRESH_TOKEN_EXPIRE_DAYS`.

Добавь зависимости в `backend/requirements.txt`: `python-jose[cryptography]==3.3.0`, `bcrypt==4.2.0`. Установи в venv:
```bash
.venv/bin/pip install -r requirements.txt
```

**Acceptance:**
- 6 функций, типизированы.
- `decode_token` истёкшего/неподписанного токена → `AuthenticationError`.

**Тесты (`backend/tests/test_security.py`):**
- `hash_password("Test123!") + verify_password(...)` → True; неправильный пароль — False.
- `create_access_token(1) + decode_token(...)` → claims содержат `sub=1` и `exp`.
- `decode_token` с подделанным секретом → `AuthenticationError`.
- `create_csrf_token` возвращает строку 32+ символов и две вызовы дают разные токены.

---

### Задача 4 — TASK-014: BaseRepository + UserRepo / SessionRepo / AuditLogRepo

**Что нужно:**

1. `backend/app/db/repository.py`:

```python
from typing import Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Base

ModelT = TypeVar("ModelT", bound=Base)

class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, obj_id: int) -> ModelT | None: ...
    async def get_all(self) -> list[ModelT]: ...
    async def create(self, **kwargs) -> ModelT: ...
    async def update(self, obj: ModelT, **fields) -> ModelT: ...
    async def delete(self, obj: ModelT) -> None: ...
```

2. `backend/app/db/repositories.py`:

```python
class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_verification_token(self, token: str) -> User | None: ...
    async def get_by_reset_token(self, token: str) -> User | None: ...
    async def get_list(
        self,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[User], int]: ...  # (items, total)

class SessionRepository(BaseRepository[Session]):
    model = Session

    async def get_by_refresh_token_hash(self, hash_: str) -> Session | None: ...
    async def get_active_by_user(self, user_id: int) -> list[Session]: ...
    async def deactivate(self, session: Session) -> None: ...
    async def deactivate_all_by_user(self, user_id: int) -> None: ...

class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def log(
        self,
        action: str,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        ip_address: str | None = None,
    ) -> AuditLog: ...

    async def get_paginated(
        self,
        action: str | None = None,
        user_id: int | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]: ...
```

**Acceptance:**
- `BaseRepository[T]` generic с CRUD-методами (async).
- Конкретные репозитории наследуют + добавляют свои методы.

**Тесты (`backend/tests/test_repositories.py`):**
- `pytest tests/test_repositories.py` зелёный.
- Интеграционный тест с тестовой БД (используй `pytest-asyncio` + `asyncpg`; чтобы не плодить инфру, можно гонять против локального docker-postgres). Поднимаешь сессию через `AsyncSessionLocal()`, создаёшь User, читаешь, обновляешь, удаляешь.

Добавь зависимости (если нужны): `pytest-asyncio==0.24.0` в `requirements-dev.txt`.

---

### Задача 5 — TASK-015: Pydantic-схемы для auth

**Что нужно:**

`backend/app/schemas/auth_schemas.py`:

```python
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

PASSWORD_REGEX = re.compile(r"...")  # см. §8.7

def _validate_password(v: str) -> str:
    if len(v) < 8 or len(v) > 128:
        raise ValueError("Пароль должен быть от 8 до 128 символов")
    if not re.search(r"[A-ZА-ЯЁ]", v):
        raise ValueError("Пароль должен содержать минимум одну заглавную букву")
    if not re.search(r"\d", v):
        raise ValueError("Пароль должен содержать минимум одну цифру")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", v):
        raise ValueError("Пароль должен содержать минимум один спецсимвол")
    return v

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    invite_token: str | None = None

    @field_validator("password")
    @classmethod
    def password_must_match(cls, v: str) -> str:
        return _validate_password(v)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    status: str
    email_verified: bool

    class Config:
        from_attributes = True

class PasswordResetRequest(BaseModel):
    email: EmailStr

class ChangePasswordRequest(BaseModel):
    old_password: str | None = None       # для авторизованной смены
    reset_token: str | None = None        # для смены через email
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_must_match(cls, v: str) -> str:
        return _validate_password(v)

class EmailChangeRequest(BaseModel):
    new_email: EmailStr
```

Email-validator зависимость: добавь `email-validator==2.2.0` в `requirements.txt`.

**Acceptance:**
- Все 7 классов выше + любые вспомогательные.
- Валидатор пароля по правилам §8.7.

**Тесты (`backend/tests/test_auth_schemas.py`):**
- `RegisterRequest(...)` с паролем `"short"` → ValidationError.
- `RegisterRequest(...)` с правильным паролем — OK, поля заполнены.
- `RegisterRequest(...)` без `first_name` — ValidationError.

---

### Задача 6 — TASK-016: AuthService (вся бизнес-логика auth)

**Что нужно:**

`backend/app/services/auth_service.py`:

```python
class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        audit_repo: AuditLogRepository,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.audit_repo = audit_repo

    async def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        invite_token: str | None = None,
    ) -> User: ...

    async def verify_email(self, token: str) -> User: ...

    async def login(
        self,
        email: str,
        password: str,
        ip: str | None = None,
        device_info: str | None = None,
    ) -> tuple[str, str, str]:  # (access_token, refresh_token, csrf_token)
        ...

    async def refresh(
        self,
        refresh_token: str,
        csrf_from_header: str,
    ) -> tuple[str, str, str]: ...

    async def logout(self, session_id: int) -> None: ...

    async def password_reset_request(self, email: str) -> None: ...

    async def change_password(
        self,
        user_id: int | None = None,
        old_password: str | None = None,
        reset_token: str | None = None,
        new_password: str = ...,
    ) -> None: ...
```

**Логика по методам:**

- `register`: проверь, что email не занят (`AlreadyExistsError` если занят). Хешируй пароль. Если `invite_token` валидный — `role=researcher`, иначе `role=pending`. Сгенерируй `email_verification_token = secrets.token_urlsafe(32)`, сохрани в User. Запиши в audit_log `auth.register`. Залогируй `logger.info(f"Email verification link for {email}: /api/auth/verify-email?token={token}")` (на MVP — без SMTP). Верни User.
- `verify_email`: найди User по `email_verification_token`. Если нет — `NotFoundError`. Если истёк (нужно хранить `email_verification_sent_at`? — пока пропусти, добавь поле в модель если нужно) — `GoneError`. Установи `email_verified=true`, `email_verification_token=None`. Audit `auth.email_verified`.
- `login`: найди User по email. Если нет — `AuthenticationError("Неверный email или пароль")`. Если `locked_until > now` — `LockedError(...)`. Сверь `verify_password`. Если неверно — `failed_login_attempts += 1`; если стало 5 — `locked_until = now + 15 min`. Audit `auth.login_failed`. Кинь `AuthenticationError`. Если верно — `failed_login_attempts = 0`, `locked_until = None`. Создай Session с `refresh_token_hash` (хеш через bcrypt или sha256), `csrf_token = create_csrf_token()`, `expires_at = now + 7 дней`. Audit `auth.login_success`. Верни tuple (access, refresh, csrf).
- `refresh`: декодируй `refresh_token` → claims. Найди Session по хешу токена. Сверь `csrf_from_header == session.csrf_token` — иначе `ForbiddenError("CSRF проверка не пройдена")`. Если session.is_active=False или expires_at < now — `GoneError`. Деактивируй старую сессию, создай новую (rotation). Верни (access, refresh, csrf).
- `logout`: найди session, `is_active=False`. Audit `auth.logout`.
- `password_reset_request`: найди User по email. Сгенерируй reset_token (24ч). Залогируй `logger.info(...)` со ссылкой. Audit `auth.password_reset_request`. Если email не зарегистрирован — **не кидай ошибку** (security: не раскрываем, существует ли email).
- `change_password`: если `reset_token` — найди User по токену, сверь не истёк. Если `old_password` — нужен `user_id`, сверь `verify_password`. Иначе — `UnprocessableError`. Установи новый `password_hash`, обнули `password_reset_token`. Деактивируй все сессии (`session_repo.deactivate_all_by_user`). Audit `auth.password_change`.

**Acceptance:**
- Все 7 методов реализованы, не используют raw `HTTPException`.
- Lockout работает: 5 неуспехов → `locked_until` установлен.
- Сессии ротируются на refresh.
- Audit-записи создаются на каждое значимое действие.

**Тесты (`backend/tests/test_auth_service.py`):**
- `register` создаёт User в pending, audit-запись есть.
- `register` с занятым email → `AlreadyExistsError`.
- 5 подряд `login` с неверным паролем → 5-й кидает `AuthenticationError`, 6-й кидает `LockedError`.
- `refresh` без правильного CSRF → `ForbiddenError`.

---

### Задача 7 — TASK-017: `api/deps.py`

**Что нужно:**

`backend/app/api/deps.py`:

```python
from collections.abc import AsyncIterator, Callable

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.db.models import User, UserRole
from app.db.repositories import UserRepository, SessionRepository, AuditLogRepository
from app.services.auth_service import AuthService


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Требуется авторизация")
    token = authorization[7:]
    claims = decode_token(token)  # бросит AuthenticationError если невалиден
    user_id = int(claims["sub"])
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None or user.status != "active":
        raise AuthenticationError("Пользователь не найден или заблокирован")
    return user


async def get_optional_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not authorization:
        return None
    try:
        return await get_current_user(authorization, db)
    except AuthenticationError:
        return None


def require_role(*roles: UserRole) -> Callable:
    async def dependency(current: User = Depends(get_current_user)) -> User:
        if current.role not in roles:
            raise ForbiddenError("Недостаточно прав")
        return current
    return dependency


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(
        user_repo=UserRepository(db),
        session_repo=SessionRepository(db),
        audit_repo=AuditLogRepository(db),
    )
```

**Acceptance:** все 5 функций работают, `require_role('admin')` пускает админа и блокирует respondent.

**Тесты:** в TASK-018 проверишь end-to-end.

---

### Задача 8 — TASK-018: роутер `/api/auth/*` с rate-limit'ами

**Что нужно:**

1. `backend/app/core/limiter.py`:
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   from app.core.config import settings

   limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
   ```
   Добавь `slowapi==0.1.9` в `requirements.txt`.

2. `backend/app/api/routers/auth.py`:
   ```python
   from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status

   from app.api.deps import get_auth_service, get_current_user
   from app.core.limiter import limiter
   from app.schemas.auth_schemas import (
       RegisterRequest, LoginRequest, TokenResponse, UserResponse,
       PasswordResetRequest, ChangePasswordRequest,
   )
   from app.services.auth_service import AuthService

   router = APIRouter()

   @router.post("/register", response_model=UserResponse, status_code=201)
   @limiter.limit("5/minute")
   async def register(
       request: Request,  # нужен slowapi
       payload: RegisterRequest,
       service: AuthService = Depends(get_auth_service),
   ):
       user = await service.register(...)
       return user

   @router.post("/verify-email", status_code=200)
   async def verify_email(token: str, service: AuthService = Depends(get_auth_service)):
       await service.verify_email(token)
       return {"detail": "Email подтверждён"}

   @router.post("/login", response_model=TokenResponse)
   @limiter.limit("10/minute")
   async def login(
       request: Request,
       response: Response,
       payload: LoginRequest,
       service: AuthService = Depends(get_auth_service),
   ):
       access, refresh, csrf = await service.login(
           payload.email, payload.password, ip=request.client.host
       )
       response.set_cookie(
           key="refresh_token",
           value=refresh,
           httponly=True,
           secure=True,
           samesite="strict",
           max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
       )
       response.headers["X-CSRF-Token"] = csrf
       return TokenResponse(access_token=access)

   @router.post("/refresh", response_model=TokenResponse)
   @limiter.limit("30/minute")
   async def refresh(
       request: Request,
       response: Response,
       refresh_token: str | None = Cookie(None),
       x_csrf_token: str | None = Header(None),
       service: AuthService = Depends(get_auth_service),
   ):
       # service сам кидает AuthenticationError/ForbiddenError при ошибках
       access, new_refresh, csrf = await service.refresh(refresh_token, x_csrf_token)
       response.set_cookie("refresh_token", new_refresh, httponly=True, secure=True, samesite="strict",
                           max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
       response.headers["X-CSRF-Token"] = csrf
       return TokenResponse(access_token=access)

   @router.post("/logout", status_code=204)
   async def logout(
       current: User = Depends(get_current_user),
       service: AuthService = Depends(get_auth_service),
   ):
       # session_id придётся прокинуть либо через токен, либо через декодирование refresh-cookie
       ...

   @router.get("/me", response_model=UserResponse)
   async def me(current: User = Depends(get_current_user)):
       return current

   @router.post("/password-reset-request", status_code=204)
   @limiter.limit("3/minute")
   async def password_reset_request(
       request: Request,
       payload: PasswordResetRequest,
       service: AuthService = Depends(get_auth_service),
   ):
       await service.password_reset_request(payload.email)

   @router.post("/change-password", status_code=204)
   @limiter.limit("5/minute")
   async def change_password(
       request: Request,
       payload: ChangePasswordRequest,
       service: AuthService = Depends(get_auth_service),
       current: User | None = Depends(get_optional_current_user),
   ):
       await service.change_password(
           user_id=current.id if current else None,
           old_password=payload.old_password,
           reset_token=payload.reset_token,
           new_password=payload.new_password,
       )
   ```

3. В `backend/app/main.py`:
   ```python
   from slowapi import _rate_limit_exceeded_handler
   from slowapi.errors import RateLimitExceeded

   from app.api.routers.auth import router as auth_router
   from app.core.limiter import limiter

   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
   ```

**Acceptance:**
- Все 8 эндпоинтов работают, статусы и rate-limits корректные.
- `/login` ставит refresh-cookie с `httpOnly Secure SameSite=Strict`.
- `/refresh` без правильного `X-CSRF-Token` → 403.
- 11-й логин за минуту → 429.

**Тесты (`backend/tests/test_auth_endpoints.py`):**
- Полный E2E: register → verify-email → login → refresh → logout.
- Через `httpx.AsyncClient` с `app=app` (без поднятия сервера).
- Проверь cookie-атрибуты в ответе на login.

---

### Задача 9 — TASK-019: invitation-flow

**Что нужно:**

1. `backend/app/api/routers/admin/__init__.py` — пусто.
2. `backend/app/api/routers/admin/invitations.py`:

```python
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Request
from jose import jwt

from app.api.deps import require_role
from app.core.config import settings
from app.core.limiter import limiter
from app.db.models import User, UserRole

router = APIRouter()

@router.post("/invitations", status_code=201)
@limiter.limit("30/minute")
async def create_invitation(
    request: Request,
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=7)
    payload = {
        "intended_role": "researcher",
        "issued_by": admin.id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"token": token, "expires_at": exp.isoformat()}
```

3. В `app/main.py`:
   ```python
   from app.api.routers.admin.invitations import router as invitations_router
   app.include_router(invitations_router, prefix="/api/admin", tags=["admin"])
   ```

4. В `AuthService.register` (TASK-016) если был передан `invite_token` — декодируй (`jwt.decode(invite_token, settings.JWT_SECRET, algorithms=["HS256"])`), если `intended_role == "researcher"` и не истёк — `role = UserRole.RESEARCHER`. Иначе игнорируй invite, role остаётся `UserRole.PENDING`. Не падай — невалидный invite просто означает, что регистрация будет под pending.

**Acceptance:**
- POST `/api/admin/invitations` (admin) → токен.
- POST `/api/auth/register` с этим токеном → user.role = `researcher`.
- Без токена / просроченный → user.role = `pending`.

**Тесты:** добавь к `test_auth_endpoints.py` сценарий с invitation-flow.

---

### Задача 10 — TASK-020: AuditService + middleware

**Что нужно:**

1. `backend/app/services/audit_service.py`:

```python
class AuditService:
    def __init__(self, audit_repo: AuditLogRepository):
        self.audit_repo = audit_repo

    async def log(
        self,
        action: str,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        ip_address: str | None = None,
    ) -> None:
        await self.audit_repo.log(action, user_id, entity_type, entity_id, ip_address)
```

В сервисах раньше ты вызывал `audit_repo.log(...)` напрямую — теперь можно прокинуть `AuditService` через DI и вызывать его. Это слой полезен, когда добавится логика типа «не логировать дубли в течение 1 секунды» — пока такой логики нет, но слой готов.

2. (Опц.) Middleware в `backend/app/main.py`:

```python
from starlette.middleware.base import BaseHTTPMiddleware

class AuditRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # просто проксирует, никаких body-dump'ов
        response = await call_next(request)
        # тут можно записать в metric-store, но не в audit_log (слишком много шума)
        return response

# app.add_middleware(AuditRequestMiddleware)
```

Реальная польза от middleware в auth-цепочке маленькая — все значимые действия уже логируются из `AuthService`. Если middleware усложняет — оставь без него.

**Acceptance:**
- `AuditService.log(...)` записывает в `audit_log` и не трогает body запроса.
- Из `AuthService` идут вызовы `audit_service.log(action, ...)` на register/login_*/logout/password_change/etc.
- В `audit_log` нет ни одной записи с текстом ответа пользователя.

**Тесты:**
- После register — `SELECT * FROM audit_log WHERE action='auth.register'` → 1 запись с правильным user_id.
- После 5 неуспешных login — 5 записей `auth.login_failed` + 1 `auth.account_blocked`.
- `SELECT COUNT(*) FROM audit_log WHERE action LIKE '%text%' OR action LIKE '%body%'` → 0.

---

## 10. Workflow и закрытие задач

### По каждой задаче

1. Прочитай раздел задачи в этом документе. Открой релевантный раздел архитектурного контекста (§8.X). Сверься с правилами (§6).
2. Реализуй. Без комментариев.
3. Если правил модели — `alembic revision --autogenerate -m "<краткое описание>"`. Проверь, что `upgrade head && downgrade -1 && upgrade head` все три зелёные.
4. Прогоняй локально (см. §7):
   ```bash
   bash scripts/check-no-text-storage.sh && \
     cd backend && \
     .venv/bin/ruff check . && \
     .venv/bin/mypy app/ && \
     .venv/bin/pytest && \
     cd ..
   ```
   Если что-то красное — фикси.
5. Коммит. Один коммит на одну задачу (если получается). Стиль:
   ```
   [feat] TASK-013: добавлены кастомные исключения и FastAPI handlers
   ```
   или
   ```
   [fix] TASK-018: refresh теперь правильно ротирует CSRF-токен
   ```
   Без двоеточия после `[feat]/[fix]`. Описание на русском.

### После завершения задачи — отчёт

Пришли в чат короткий отчёт:

```
TASK-XXX done

Что сделал:
- ...
- ...

Файлы:
- backend/app/...
- backend/tests/...
- migrations/versions/...

Тесты:
- pytest: 12 passed
- ruff/mypy: clean
- no-text-storage: ok
- (для миграций) alembic upgrade head + downgrade -1 + upgrade head — все три ОК

Проблемы / решения, которые принял:
- ...

Что не сделал и почему:
- ... (если есть)
```

Я возьму этот отчёт, обновлю `tasks.json` (status → done) и `progress.md` со своей стороны.

### Если задача неоднозначна

Если что-то непонятно или есть несколько разумных подходов — **спроси, не угадывай**. Лучше потерять 5 минут на уточнение, чем переделывать.

Особенно про:
- Формат ответа API, если этот документ умалчивает.
- Куда деть какое-то поле (модель vs schema vs Redis).
- Как обработать edge-case (пустые данные, конкурентный доступ, частичная ошибка).

---

## 11. FAQ / типичные ошибки

**Pydantic / Settings падает на старте**
Проверь, что `backend/.env` существует и все обязательные поля заполнены. Сверь с `backend/.env.example`. Все поля строкового типа должны быть непустыми.

**Alembic не видит модель**
Убедись, что модель импортируется в `app/db/models.py` (или модуль, который импортируется при импорте `Base.metadata`). `migrations/env.py` импортирует `from app.db.models import Base` — всё, что навешано на этот `Base`, alembic подхватит. Если модель в отдельном файле, добавь импорт в `app/db/models.py`.

**`grep`-проверка no-text-storage упала**
Сообщение покажет файл и строку с запрещённым именем поля. Запрещены: `answer_text`, `response_text`, `user_text`, `raw_answer`, `raw_response`, `message_body`, `chat_message`. Это политика приватности. В auth-моделях таких полей не должно быть; если случайно завёл — переименуй.

**`ruff` ругается на двойную пустую строку после импорт-блока**
Один пустой ряд между импорт-блоком и кодом, не два. `ruff check --fix .` поправит автоматически. Это стилистика, не баг.

**`mypy` ругается на `Field(..., min_length=1)`**
В нашем `pyproject.toml` подключён `pydantic.mypy` plugin — он умеет обрабатывать `Field(...)`. Если ругается — проверь, что плагин активен и mypy запускается из `backend/`.

**`pytest` ругается на отсутствие env-vars**
В `backend/tests/conftest.py` уже есть `os.environ.setdefault(...)` для всех обязательных полей Settings. Если добавляешь свои env-зависимые тесты — следуй тому же паттерну.

**`alembic_version` уже есть в БД, и мне нужна чистая БД для теста**
```bash
docker exec psychograph_postgres psql -U postgres -d psychograph -c 'DROP TABLE IF EXISTS alembic_version, users, sessions, audit_log CASCADE;'
.venv/bin/alembic upgrade head
```

**Конфликтов с другой командой быть не должно**
Если случайно зацепил `nlp_service/` или `src/` — откати правку.

---

## 12. Контакт

После каждой задачи — отчёт в чат. По вопросам, неясностям, edge-кейсам — пиши не откладывая.

Удачи. Без героизма, по одному шагу за раз.
