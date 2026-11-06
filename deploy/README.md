# Deploy / локальная инфра

## Сервисы

| Сервис | Порт | Назначение |
|--------|------|------------|
| Postgres (+ pgvector) | `5432` | БД, метаданные, вектора |
| Redis | `6379` | Очередь задач (+ позже кеш) |
| MinIO API | `9000` | Файлы документов |
| MinIO Console | `9001` | Веб-UI MinIO |

Логин/пароль MinIO Console: `minioadmin` / `minioadmin`.  
Postgres: user/db/password = `ai_docs` / `ai_docs` / `ai_docs`.

## Запуск

Нужен Docker Desktop. Из корня репозитория или из `deploy/`:

```bash
cd deploy
docker compose up -d
```

Статус:

```bash
docker compose ps
docker compose logs -f
```

Остановка (данные в volumes сохраняются):

```bash
docker compose down
```

Полный сброс данных:

```bash
docker compose down -v
```

## Связка с бекендом

В `backend/` скопируй `.env.example` → `.env` (URL уже заточены под эти порты).  
Бекенд пока запускается отдельно через uvicorn, не в Docker.
