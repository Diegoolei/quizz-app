# quizz-app

Asynchronous Django API (ASGI + uvicorn), managed with [uv](https://docs.astral.sh/uv/).

The committed `.env` is intentional for local evaluation only. Copy `.env.example` when you need a clean template; never reuse these secrets outside local/dev.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker + Docker Compose (for Postgres and/or full stack)
- Python 3.13+ (project pins via `uv`; local may use 3.14)

## Run with uv (native)

1. Install dependencies:

```bash
uv sync
```

2. Start Postgres (Docker DB only is enough):

```bash
docker compose up db -d
```

3. Apply migrations and run the ASGI server:

```bash
uv run python manage.py migrate
uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload
```

Useful commands:

```bash
uv run python manage.py createsuperuser
uv run pytest
uv run ruff check .
```

Default settings module: `config.settings.local` (see `.env`).

## Run with Docker

Full stack (`db` + `web`):

```bash
docker compose up --build
```

- API: http://localhost:8000
- `web` runs `uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload`
- `entrypoint.sh` runs `migrate` and `collectstatic` before the server starts
- Compose overrides `POSTGRES_HOST=db` for the `web` service

Stop:

```bash
docker compose down
```

## Settings layout

| Module | Use |
|---|---|
| `config.settings.base` | Shared config, django-environ, JSON structlog |
| `config.settings.local` | Local/dev (`DEBUG`, static files) |
| `config.settings.staging` | Staging |
| `config.settings.prod` | Production |
