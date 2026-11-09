.PHONY: install up down ps logs run worker health migrate migrate-new admin openapi

install:
	cd backend && .venv/bin/pip install -r requirements.txt

up:
	cd deploy && docker compose up -d

down:
	cd deploy && docker compose down

ps:
	cd deploy && docker compose ps

logs:
	cd deploy && docker compose logs -f

run:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd backend && .venv/bin/python -m app.workers.indexer

health:
	curl -s http://localhost:8000/api/v1/health | python3 -m json.tool

migrate:
	cd backend && .venv/bin/alembic upgrade head

migrate-new:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(m)"

admin:
	cd backend && .venv/bin/python scripts/create_admin.py --email "$(email)" --password "$(password)"

openapi:
	cd backend && .venv/bin/python scripts/export_openapi.py


