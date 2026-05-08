import sys
import os
import asyncio
from contextlib import asynccontextmanager

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.editor import router
from backend.session import cleanup_expired


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def _cleanup_loop():
        while True:
            await asyncio.sleep(600)  # 每10分钟清理一次
            cleanup_expired()
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="SCI Editor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
