# JOD Gateway

A lightweight, self-contained payment gateway service built in Python.

## Setup

```
uv sync   # creates .venv/ inside the project dir
```

## Run

```
make dev
```

## Verify

```
curl localhost:8080/health
```

> All dependencies live in `./.venv` — nothing is installed globally.