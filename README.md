# racy-fastapi

A demonstration of race conditions to look out for when using FastAPI.

## Pre-requisites

Install dependencies and apply database migration:

```shell
poetry install
poetry shell
alembic upgrade head
```

## Run

### Manual

Start the app:

```shell
uvicorn racy:app --workers 1 --reload
```

Load 127.0.0.1:8000 twice

```shell
curl http://127.0.0.1:8000 &
curl http://127.0.0.1:8000 &
```

*Note* If you want to do this in a browser window, use two completely different browsers, such as Chrome and Safari.

### Automatic

```shell
pytest tests/
```
