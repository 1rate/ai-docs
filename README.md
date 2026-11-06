# ai-docs

Учебный проект: чат-бот по правовым документам с RAG-надстройкой.

## Структура репозитория

```
ai-docs/
├── backend/     # FastAPI: API, RAG, чат, интеграции
├── frontend/    # UI (позже)
├── deploy/      # docker-compose, nginx, init SQL и т.п.
└── docs/        # Архитектура, решения, заметки по обучению
```

## Стек (бекенд)

| Компонент | Роль |
|-----------|------|
| FastAPI | HTTP API |
| PostgreSQL + pgvector | Метаданные документов, чаты, история, эмбеддинги |
| MinIO | Файлы исходных документов (PDF/DOCX/…) |
| Redis | Кеш частых ответов / rate limit |
| LLM API | Генерация ответа по найденному контексту |

Подробности: [docs/architecture.md](docs/architecture.md), схема взаимодействия: [docs/system-interaction.md](docs/system-interaction.md).

## Быстрый старт

```bash
make up                          # Postgres, Redis, MinIO
make migrate                     # применить миграции БД
make admin email=admin@example.com password=admin12345
make run                         # FastAPI на :8000
make health
make down
```

Auth: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me` (Bearer).

Documents (admin JWT): `POST/GET/DELETE /api/v1/documents`. После upload нужен воркер: `make worker`.

Для индексации в `backend/.env` нужен реальный `LLM_API_KEY` (эмбеддинги). Чанки пишутся в `document_chunks` (pgvector).

Swagger: http://localhost:8000/docs
