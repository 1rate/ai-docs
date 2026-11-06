# Подготовка среды разработки

Этот файл — чеклист. Ничего из этого агент за тебя не выполнял: пройди шаги сам.

## 1. Python

1. Установи Python **3.11+** (для macOS удобно `brew install python@3.12` или pyenv).
2. Проверь: `python3 --version`.
3. В корне `backend/` создай виртуальное окружение:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Обновление pip: `pip install -U pip`.
5. Зависимости позже появятся в `requirements.txt` / `pyproject.toml`; пока достаточно понимать, что пакеты ставятся **только внутрь `.venv`**, не в системный Python.

## 2. IDE / Cursor

- Открой репозиторий целиком (`ai-docs`).
- Выбери интерпретатор: `backend/.venv/bin/python`.
- Полезно расширение / поддержка Python + Pylance.

## 3. Docker (инфра)

Для Postgres, Redis, MinIO локально почти всегда используют Docker Compose из `deploy/`.

1. Установи Docker Desktop.
2. Проверь: `docker version` и `docker compose version`.
3. Поднять сервисы:
   ```bash
   cd deploy
   docker compose up -d
   docker compose ps
   ```

## 4. Переменные окружения

- Скопируй `backend/.env.example` → `backend/.env` (когда файл появится).
- В `.env` — секреты и URL (БД, Redis, MinIO, ключ LLM). **Не коммить `.env`.**

## 5. Что ещё пригодится позже

- `alembic` — миграции схемы PostgreSQL
- `httpx` / клиент OpenAI-совместимого API — вызовы LLM
- `pytest` — тесты в `backend/tests/`

## Порядок освоения (рекомендация)

1. Поднять FastAPI «hello world» и один health-эндпоинт.
2. Подключить PostgreSQL и одну таблицу документов.
3. Загрузка файла в MinIO + запись метаданных.
4. Чанкинг + эмбеддинги + pgvector.
5. Чат: история + RAG + LLM.
6. Redis-кеш поверх ответов.
