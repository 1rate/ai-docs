# Deploy / локальная инфра

## Сервисы

| Сервис | Порт | Назначение |
|--------|------|------------|
| Postgres | `5432` | Метаданные, чаты, текст чанков |
| Redis | `6379` | Очередь задач (+ позже кеш) |
| MinIO API | `9000` | Файлы документов |
| MinIO Console | `9001` | Веб-UI MinIO |
| Qdrant | `6333` | Вектора / similarity search |

Логин/пароль MinIO Console: `minioadmin` / `minioadmin`.  
Postgres: user/db/password = `ai_docs` / `ai_docs` / `ai_docs`.  
Qdrant UI: http://localhost:6333/dashboard

## Запуск

```bash
cd deploy
docker compose up -d
docker compose ps
```

Остановка: `docker compose down`  
Сброс данных: `docker compose down -v`

Бекенд локально через `make run` / `make worker`.
