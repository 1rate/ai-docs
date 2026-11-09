# Схема взаимодействия системы

Проектные документы (не правовые). Клиент ↔ бекенд ↔ инфраструктура, роли и потоки.

Архитектура и дорожная карта инструментов: [architecture.md](./architecture.md).

## Роли

| Роль | Возможности |
|------|-------------|
| `user` | Свои чаты и сообщения (когда чат будет). |
| `admin` | Всё, что `user`, плюс загрузка / список / удаление документов и статусы индексации. |

Auth (как сделано):

- login → access JWT (короткий) + refresh (hash в Postgres);
- httpOnly cookies + опционально JSON/Bearer;
- refresh с ротацией; logout → revoke refresh + blacklist access `jti` в Redis.

Правила:

- чат → `user` или `admin`;
- `POST/GET/DELETE /documents` → только `admin`;
- `GET /health` → публично.

---

## Общая картина

![Обзор взаимодействия системы](./system-interaction-overview.jpg)

> Картинка выше историческая (ещё с pgvector). Актуальная схема — mermaid ниже и [architecture.md](./architecture.md).

```mermaid
flowchart LR
  subgraph Clients
    U[User — чат]
    A[Admin — чат + документы]
  end

  FE[Frontend / HTTP-клиент]
  API[Backend FastAPI]

  subgraph Infra
    PG[(PostgreSQL)]
    QD[(Qdrant)]
    S3[(MinIO)]
    RD[(Redis)]
    W[Worker индексации]
    LLM[Embeddings + Chat LLM]
  end

  U --> FE
  A --> FE
  FE -->|HTTPS + cookies / Bearer| API

  API --> PG
  API --> QD
  API --> S3
  API --> RD
  API --> LLM

  API -->|enqueue| RD
  W -->|dequeue| RD
  W --> PG
  W --> QD
  W --> S3
  W --> LLM
```

Кратко:

- клиент говорит **только** с API;
- **Postgres** — пользователи, сессии refresh, документы, текст чанков, чаты;
- **Qdrant** — вектора и поиск;
- **MinIO** — файлы;
- **Redis** — очередь индексации + blacklist access;
- **Worker** — парсинг → чанки → embed → PG + Qdrant;
- **LLM** — сейчас HTTP API; позже через LiteLLM (OpenAI/Ollama/…).

---

## Поток: аутентификация

```mermaid
sequenceDiagram
  actor C as Клиент
  participant API as FastAPI
  participant PG as PostgreSQL
  participant RD as Redis

  C->>API: POST /auth/login
  API->>PG: проверить user + password hash
  API->>PG: сохранить refresh token hash
  API-->>C: access + refresh (cookies + JSON)

  C->>API: запрос с access cookie / Bearer
  API->>API: проверить JWT + jti не в blacklist
  API->>PG: загрузить user

  C->>API: POST /auth/refresh
  API->>PG: ротация refresh
  API-->>C: новая пара токенов

  C->>API: POST /auth/logout
  API->>RD: blacklist access jti
  API->>PG: revoke refresh
  API-->>C: clear cookies
```

---

## Поток: загрузка документа (admin) — реализовано

```mermaid
sequenceDiagram
  actor A as Admin
  participant API as FastAPI
  participant S3 as MinIO
  participant PG as PostgreSQL
  participant RD as Redis
  participant W as Worker
  participant EMB as Embedding API
  participant QD as Qdrant

  A->>API: POST /documents
  API->>S3: put file
  API->>PG: document pending
  API->>RD: enqueue document_id
  API-->>A: 202 pending

  W->>RD: brpop job
  W->>PG: status=processing
  W->>S3: get file
  W->>W: extract → chunk
  Note over W: позже Presidio на тексте
  W->>EMB: embeddings
  Note over EMB: позже LiteLLM
  W->>PG: сохранить текст чанков
  W->>QD: upsert vectors + payload
  W->>PG: status=ready
```

---

## Поток: удаление документа (admin) — реализовано

```mermaid
sequenceDiagram
  actor A as Admin
  participant API as FastAPI
  participant QD as Qdrant
  participant PG as PostgreSQL
  participant S3 as MinIO

  A->>API: DELETE /documents/{id}
  API->>QD: delete points by document_id
  API->>PG: delete document cascade chunks
  API->>S3: delete file
  API-->>A: 204
```

---

## Поток: чат + RAG (план)

```mermaid
sequenceDiagram
  actor C as Клиент
  participant API as FastAPI
  participant PG as PostgreSQL
  participant QD as Qdrant
  participant EMB as Embedding
  participant LLM as Chat LLM
  participant LF as Langfuse

  C->>API: POST /chats/{id}/messages
  API->>PG: save user message
  API->>PG: load last N messages
  API->>EMB: embed question
  API->>QD: top-k similar chunks
  Note over API: позже Presidio / LangGraph
  API->>LLM: system + context + history
  LLM-->>LF: trace generation
  LLM-->>API: answer
  API->>PG: save assistant + sources
  API-->>C: answer + sources
```

---

## Матрица API ↔ роли

| Эндпоинт | user | admin | Статус |
|----------|:----:|:-----:|--------|
| `POST /auth/register\|login\|refresh\|logout` | ✓ | ✓ | есть |
| `GET /auth/me` | ✓ | ✓ | есть |
| `POST/GET/DELETE /documents` | — | ✓ | есть |
| чаты / сообщения | ✓ | ✓ | план |
| `GET /health` | публично | публично | есть |

---

## Границы клиента

Фронт:

- login/refresh/logout с `credentials: 'include'` (cookies);
- UI чата и (admin) документов;
- опрос статуса индексации или SSE позже;
- OpenAPI: живой `/openapi.json` или снимок на Pages [`api/`](./api/).

Фронт не ходит в Postgres / Qdrant / MinIO / Redis / LLM напрямую.
