# Backend

Python + FastAPI. Учебный RAG-чатбот по правовым документам.

## Структура `app/`

| Папка | Назначение |
|-------|------------|
| `api/v1/` | HTTP-эндпоинты (роутеры): документы, чат, health |
| `core/` | Настройки (`settings`), общие константы, зависимости |
| `db/` | Подключение к PostgreSQL, сессии, миграции-хелперы |
| `models/` | SQLAlchemy-модели (таблицы БД) |
| `schemas/` | Pydantic-схемы запросов/ответов API |
| `services/` | Бизнес-логика: загрузка документов, RAG, LLM, кеш |
| `workers/` | Фоновые задачи (индексация документа → чанки → вектора) |

## Планируемые эндпоинты (минимум)

- `POST /api/v1/documents` — загрузка документа → MinIO + очередь индексации
- `GET /api/v1/documents` — список документов с пагинацией
- `POST /api/v1/chats` / `POST /api/v1/chats/{id}/messages` — чат (см. docs)

## Локальный запуск

Из папки `backend/`:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка:

- Health: http://localhost:8000/api/v1/health  
  (должен вернуть `"checks": {"postgres": "ok"}` если `docker compose up -d` в `deploy/`)
- Swagger: http://localhost:8000/docs

Остановка: `Ctrl+C` в терминале. Выход из venv: `deactivate`.

В Cursor выбери интерпретатор `backend/.venv/bin/python`.

Окружение подробнее — `docs/dev-setup.md`.

## Инфра (Docker)

```bash
cd deploy
docker compose up -d
```

Подробности: `deploy/README.md`. Скопируй `.env.example` → `.env` в `backend/`, если ещё нет.
