from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from jod_gateway import __version__
from jod_gateway.api.health import router as health_router
from jod_gateway.api.openai_compat import router as openai_router
from jod_gateway.api.sessions import router as sessions_router
from jod_gateway.config import settings
from jod_gateway.core.crypto import load_or_create_master_key
from jod_gateway.core.store import SessionStore
from jod_gateway.logging import setup_logging
from jod_gateway.providers import load_builtin_adapters


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    load_builtin_adapters()

    key = load_or_create_master_key(settings.master_key_path)
    store = SessionStore(settings.db_path, key)
    await store.init()
    app.state.store = store
    yield
    await store.close()


app = FastAPI(title="JOD Gateway", version=__version__, lifespan=lifespan)
app.include_router(health_router)
app.include_router(openai_router)
app.include_router(sessions_router)


if __name__ == "__main__":
    uvicorn.run("jod_gateway.main:app", host=settings.host, port=settings.port, reload=True)