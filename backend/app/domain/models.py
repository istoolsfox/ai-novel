"""领域层 · Pydantic 数据模型。

从 main.py 迁出，集中管理所有请求/响应模型。
所有模型不依赖框架，纯数据定义。
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectIn(BaseModel):
    title: str
    topic: str = ""
    genre: str = ""
    audience: str = ""
    tone: str = ""
    target_chapter_count: int = 0
    target_words_per_chapter: int = 0
    logline: str = ""
    synopsis: str = ""
    global_summary: str = ""
    privacy_mode: bool = True


class DeleteProjectIn(BaseModel):
    password: str = ""


class ChapterIn(BaseModel):
    outline_id: str = ""
    chapter_number: int = 1
    title: str = ""
    brief: str = ""
    draft: str = ""
    summary: str = ""
    status: str = "draft"


class VersionIn(BaseModel):
    label: str = ""
    content: str
    model: str = ""
    context_summary: str = ""


class WikiWriteIn(BaseModel):
    path: str
    content: str
    source_chapter_id: str = ""


class GenericIn(BaseModel):
    title: str = ""
    category: str = ""
    content: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class AiWorkflowIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    chapter_id: str = ""
    prompt: str = ""
    content: str = ""
    count: int = 2
    payload: dict[str, Any] = Field(default_factory=dict)


class ModelConnectionTestIn(BaseModel):
    provider: str = "OpenAI"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model_name: str = ""
    temperature: float = 0.1
    max_tokens: int = 16
