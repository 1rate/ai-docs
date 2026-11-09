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

## Включить GitHub Pages

1. GitHub → Settings → Pages  
2. Source: **Deploy from a branch**  
3. Branch: `main` (или ваша), folder: **/docs**  
4. Схема будет здесь:  
   `https://<user>.github.io/<repo>/api/`  
   JSON: `https://<user>.github.io/<repo>/api/openapi.json`

Фронт может всегда читать `openapi.json` с этого URL для просмотра/codegen.
