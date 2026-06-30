# Веха — AI-платформа управления задачами и проектами

Корпоративный таск-трекер с AI-ассистентом: ставит задачи, оценивает их выполнение и собирает аналитику по сотрудникам. Бэкенд — **FastAPI** (async), SPA-фронт — **Vue 3**, фоновые задачи — **Celery**, AI — **GigaChat**.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Vue.js](https://img.shields.io/badge/Vue%203-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D)
![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)
![GigaChat](https://img.shields.io/badge/GigaChat-1E9E5A?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

---

## Возможности

- Проекты, задачи, **Kanban-доска**, команды, отделы и роли
- **JWT-аутентификация** (access/refresh) и ролевой доступ: `admin` / `manager` / `worker`
- **AI-ассистент на GigaChat** — генерация плана задач, оценка выполнения, авто-отчёты и статистика сотрудников
- Уведомления, комментарии, аналитика (графики на ApexCharts)
- Фоновые задачи на **Celery** (брокер Redis): контроль дедлайнов, ежедневные отчёты

## AI-возможности (GigaChat)

Интеграция — в `api/ai_service.py`, эндпоинты — в `api/routers/ai.py`:

| Эндпоинт | Что делает |
|---|---|
| `POST /ai/projects/{id}/plan` | сгенерировать план задач по описанию проекта |
| `POST /ai/projects/{id}/plan/apply` | создать задачи из сгенерированного плана |
| `POST /ai/tasks/{id}/complete` | AI-оценка выполнения задачи (балл + фидбэк) |
| `POST /ai/reports/generate/{project_id}` | сгенерировать отчёт по проекту |
| `GET /ai/reports`, `/ai/reports/{project_id}` | полученные AI-отчёты |
| `GET /ai/stats/employees` | агрегированная статистика по сотрудникам |

Вызовы к GigaChat обёрнуты в async (`asyncio.to_thread`), есть автообновление OAuth-токена и обработка лимитов (`QuotaExceededError`).

## Архитектура

```
            ┌───────────────┐
            │   Vue 3 SPA   │  Vite · Pinia · Vue Router · Axios · Tailwind · ApexCharts
            │  (frontend/)  │  :5173 (dev)
            └───────┬───────┘
                    │ REST + JWT
            ┌───────▼───────┐        ┌──────────────┐
            │  FastAPI API  │ ─────► │   GigaChat    │  план · оценка · отчёты
            │    (api/)     │        └──────────────┘
            │     :8001     │
            └───┬───────┬───┘
       asyncpg │       │ Celery (broker/result)
            ┌──▼──┐  ┌──▼──────┐
            │ PG  │  │  Redis  │
            └─────┘  └─────────┘

            ┌──────────────────┐
            │  Django (web/)   │  server-rendered dashboard / login / admin · :8081
            └──────────────────┘
```

- **api/** — FastAPI: auth (JWT), проекты/задачи, AI, аналитика, комментарии, уведомления; Celery-воркеры (`tasks/`).
- **frontend/** — Vue 3 SPA: Kanban, дашборд, аналитика, проекты, команды, профили.
- **web/** — вспомогательный Django-сервис (server-rendered dashboard + login + админка).
- **PostgreSQL** — данные, **Redis** — кэш и брокер Celery.

Схема БД (`init_db.sql`): `departments`, `users`, `projects`, `project_members`, `tasks`, `task_logs`, `role_upgrade_requests`, `ai_reports`, `employee_stats`, `notifications`.

## Стек

- **Backend:** Python · FastAPI · asyncpg · Pydantic · Celery · python-jose (JWT) · passlib (bcrypt)
- **Frontend:** Vue 3 · Vite · Pinia · Vue Router · Axios · Tailwind CSS · ApexCharts
- **AI:** GigaChat API
- **Данные:** PostgreSQL 15 · Redis 7
- **Прочее:** Django 5 (web-сервис) · Docker · docker-compose

## Структура

```
bizapp/
├── api/                 # FastAPI: бэкенд + AI + Celery
│   ├── main.py
│   ├── models.py
│   ├── auth_utils.py
│   ├── ai_service.py    # интеграция с GigaChat
│   ├── routers/         # ai, analytics, comments, notifications
│   └── tasks/           # Celery: check_deadlines, daily_report
├── frontend/            # Vue 3 SPA (Vite)
├── web/                 # Django (dashboard / login / admin)
├── init_db.sql          # схема БД
├── docker-compose.yml
└── .env.example
```

## Быстрый старт

### 1. Бэкенд, БД и Redis (Docker)

```bash
cp .env.example .env        # заполните переменные (см. ниже)
docker compose up -d
```

Поднимутся: PostgreSQL (`:5432`), Redis (`:6379`), FastAPI (`:8001`), Django (`:8081`), pgAdmin (`:5050`).
Swagger FastAPI — http://localhost:8001/docs

Celery-воркер запускается отдельно (из каталога `api/`):

```bash
celery -A celery_app worker -l info
```

### 2. Фронтенд (Vue 3, через Vite)

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

## Переменные окружения (`.env`)

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | строка подключения PostgreSQL |
| `REDIS_URL` | Redis (кэш + брокер Celery) |
| `JWT_SECRET_KEY` | секрет для подписи JWT (FastAPI) |
| `ALLOWED_ORIGINS` | разрешённые CORS-origin (включая `:5173` для Vite) |
| `DJANGO_SECRET_KEY` | секрет Django-сервиса |
| `GIGACHAT_AUTH_KEY` | **обязателен для AI** — авторизационный ключ GigaChat (Basic) |

> Реальные ключи не коммитьте: `.env` в `.gitignore`, в репозитории — только `.env.example`.

## Роли и доступ

RBAC реализован через зависимости FastAPI (`dependencies.py`): `admin`, `manager`, `worker`.
Повышение роли — через запросы (`role_upgrade_requests`); доступ к проекту проверяется по членству (`project_members`).
