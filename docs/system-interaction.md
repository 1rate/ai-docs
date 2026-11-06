# Схема взаимодействия системы

Проектные документы (не правовые). Ниже — как клиент связан с бекендом и инфраструктурой, с учётом ролей.

## Роли

| Роль | Возможности |
|------|-------------|
| `user` | Чаты: создавать, читать свои, писать сообщения, получать ответы бота. Просмотр списка документов **только для справки** (без загрузки/удаления) — по желанию продукта; по умолчанию **чатится**. |
| `admin` | Всё, что `user`, плюс: загрузка документов, удаление документов, просмотр статусов индексации. |

Авторизация (черновик): клиент логинится → получает токен (JWT) с `role` → каждый защищённый эндпоинт проверяет роль.

Минимальные правила доступа:

- Чат-эндпоинты → `user` или `admin`
- `POST/DELETE /documents` → только `admin`
- `GET /documents` → `admin` (управление); для `user` можно закрыть или дать read-only список названий — решить на продукте

---

## Общая картина (контекст)

![Обзор взаимодействия системы](./system-interaction-overview.jpg)

```mermaid
flowchart LR
  subgraph Clients
    U[User — чат]
    A[Admin — чат + документы]
  end

  FE[Frontend / HTTP-клиент]
  API[Backend FastAPI]

  subgraph Infra
    PG[(PostgreSQL + pgvector)]
    S3[(MinIO)]
    RD[(Redis)]
    W[Worker индексации]
    LLM[LLM / Embedding API]
  end

  U --> FE
  A --> FE
  FE -->|HTTPS + JWT| API

  API --> PG
  API --> S3
  API --> RD
  API --> LLM

  API -->|enqueue job| RD
  W -->|dequeue job| RD
  W --> PG
  W --> S3
  W --> LLM
```

Кратко:

- **Клиент** говорит только с API (через фронт или напрямую).
- **Postgres** — пользователи, роли, чаты, сообщения, метаданные документов, вектора чанков.
- **MinIO** — исходные файлы.
- **Redis** — очередь задач индексации (+ позже кеш).
- **Worker** — отдельный процесс: забирает job из Redis, строит RAG-вектора.
- **LLM API** — эмбеддинги и генерация ответа.

---

## Поток: аутентификация

```mermaid
sequenceDiagram
  actor C as Клиент
  participant API as FastAPI
  participant PG as PostgreSQL

  C->>API: POST /auth/login (email, password)
  API->>PG: проверить пользователя
  PG-->>API: user + role
  API-->>C: access token (JWT: sub, role)

  Note over C,API: Дальше заголовок Authorization Bearer JWT
```

---

## Поток: чат (user и admin)

```mermaid
sequenceDiagram
  actor C as Клиент (user/admin)
  participant API as FastAPI
  participant PG as PostgreSQL
  participant LLM as Embedding + LLM API

  C->>API: POST /chats
  API->>PG: создать chat (owner=user_id)
  API-->>C: chat_id

  C->>API: POST /chats/{id}/messages {text}
  API->>PG: сохранить message role=user
  API->>PG: загрузить историю чата (последние N)
  API->>LLM: embedding(вопроса)
  API->>PG: similarity search top-k чанков (pgvector)
  API->>LLM: chat completion (system + контекст + история)
  LLM-->>API: ответ
  API->>PG: сохранить message role=assistant (+ источники)
  API-->>C: ответ + sources
```

Клиент **не** ходит в Postgres/Redis/LLM напрямую — только в API.

---

## Поток: загрузка документа (только admin)

```mermaid
sequenceDiagram
  actor A as Admin
  participant API as FastAPI
  participant S3 as MinIO
  participant PG as PostgreSQL
  participant RD as Redis queue
  participant W as Worker
  participant LLM as Embedding API

  A->>API: POST /documents (file) + JWT role=admin
  API->>API: проверить role == admin
  API->>S3: положить файл
  API->>PG: document status=pending
  API->>RD: enqueue index_document(doc_id)
  API-->>A: 202 {document_id, status: pending}

  W->>RD: взять job
  W->>PG: status=processing
  W->>S3: скачать файл
  W->>W: парсинг → чанки
  W->>LLM: embeddings(чанки)
  W->>PG: записать вектора + status=ready
  Note over A,PG: Admin может GET /documents/{id} и видеть статус
```

---

## Поток: удаление документа (только admin)

```mermaid
sequenceDiagram
  actor A as Admin
  participant API as FastAPI
  participant S3 as MinIO
  participant PG as PostgreSQL
  participant RD as Redis queue

  A->>API: DELETE /documents/{id} + JWT role=admin
  API->>API: проверить role == admin
  API->>PG: удалить/пометить чанки и метаданные
  API->>S3: удалить файл
  opt если индекс ещё в очереди
    API->>RD: отменить/игнорировать job для doc_id
  end
  API-->>A: 204 No Content
```

Удаление должно убирать и файл, и вектора — иначе бот продолжит опираться на «удалённый» документ.

---

## Матрица API ↔ роли (черновик)

| Эндпоинт | user | admin |
|----------|:----:|:-----:|
| `POST /auth/login` | ✓ | ✓ |
| `POST /chats`, сообщения, история своих чатов | ✓ | ✓ |
| `GET /documents` (список / статусы) | — | ✓ |
| `POST /documents` | — | ✓ |
| `DELETE /documents/{id}` | — | ✓ |
| `GET /health` | публично | публично |

`user`, вызвавший admin-эндпоинт → `403 Forbidden`.

---

## Границы ответственности клиента

Клиент (фронт):

- логин, хранение токена;
- UI чата и (для admin) UI документов;
- опрос статуса документа после загрузки (`pending` → `ready` / `failed`), либо позже — websocket/SSE.

Клиент **не** реализует RAG, не пишет в MinIO/Postgres и не зовёт LLM — это всё за API и worker.
