# Публичная схема API (GitHub Pages)

Статический Swagger UI + `openapi.json`. Не требует запущенного бекенда.

## Обновить схему после изменений API

Бекенд поднимать не обязательно — экспорт идёт из кода FastAPI:

```bash
make openapi
git add docs/api/openapi.json
git commit -m "docs: refresh OpenAPI snapshot"
git push
```

На GitHub это делает CI (`.github/workflows/openapi.yml`):

- **pull_request** — падает, если `docs/api/openapi.json` устарел (нужен `make openapi`)
- **push в main/master** при изменениях `backend/app/**` — сам пересобирает снимок и коммитит

## Что настроить в GitHub

1. **Actions** включены: Settings → Actions → General → Allow all actions  
2. Workflow permissions: Settings → Actions → General → Workflow permissions → **Read and write**  
   (чтобы бот мог запушить обновлённый `openapi.json`)  
3. **Pages**: Settings → Pages → Deploy from a branch → `main` + folder **/docs**  
4. URL схемы:  
   `https://<user>.github.io/<repo>/api/`  
   JSON: `https://<user>.github.io/<repo>/api/openapi.json`

Фронт читает `openapi.json` с Pages даже когда твой ноут выключен.
