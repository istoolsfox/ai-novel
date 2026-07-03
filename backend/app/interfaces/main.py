"""接口层 · FastAPI 应用入口。

仅负责应用装配 + 路由注册 + 健康检查。所有业务逻辑在各 routes 模块中。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..infrastructure.database import init_db
from .routes import (
    auth,
    blueprints,
    chapters,
    emotion,
    exports,
    jobs,
    projects,
    resources,
    wiki,
    workflows,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI 小说创作平台", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# 注册路由（顺序重要：具体路由在前，通用 resources 路由在后，避免路径冲突）
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(chapters.router)
app.include_router(wiki.router)
app.include_router(workflows.router)
app.include_router(exports.router)
app.include_router(emotion.router)
app.include_router(blueprints.router)
app.include_router(jobs.router)
app.include_router(resources.router)  # 通用资源路由最后注册（catch-all /{resource}）
