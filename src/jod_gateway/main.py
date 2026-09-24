from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from jod_gateway import __version__
from jod_gateway.api.health import router as health_router
from jod_gateway.config import settings
from jod_gateway.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="JOD Gateway", version=__version__, lifespan=lifespan)
app.include_router(health_router)


if __name__ == "__main__":
    uvicorn.run("jod_gateway.main:app", host=settings.host, port=settings.port, reload=True)