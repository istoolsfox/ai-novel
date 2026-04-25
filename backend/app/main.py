import json
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from .database import GENERIC_TABLES, connect, init_db, new_id, row_to_dict, rows_to_dicts, utc_now
from .storage import ensure_project_dirs, project_root, require_project, safe_wiki_path


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_app()
    yield


app = FastAPI(title="AI 小说创作平台", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    chapter_id: str = ""
    prompt: str = ""
    content: str = ""
    count: int = 2
    payload: dict[str, Any] = Field(default_factory=dict)


def init_app() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/projects")
def create_project(payload: ProjectIn) -> dict[str, Any]:
    project_id = new_id()
    root = ensure_project_dirs(project_id)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO projects (
                id, title, topic, genre, audience, tone, target_chapter_count,
                target_words_per_chapter, logline, synopsis, global_summary, status,
                privacy_mode, project_root_path, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?)
            """,
            (
                project_id,
                payload.title,
                payload.topic,
                payload.genre,
                payload.audience,
                payload.tone,
                payload.target_chapter_count,
                payload.target_words_per_chapter,
                payload.logline,
                payload.synopsis,
                payload.global_summary,
                int(payload.privacy_mode),
                str(root),
                now,
                now,
            ),
        )
        project = row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    return project


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall())


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    return require_project(project_id)


@app.patch("/api/projects/{project_id}")
def update_project(project_id: str, payload: ProjectIn) -> dict[str, Any]:
    require_project(project_id)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE projects
            SET title = ?, topic = ?, genre = ?, audience = ?, tone = ?,
                target_chapter_count = ?, target_words_per_chapter = ?,
                logline = ?, synopsis = ?, global_summary = ?, privacy_mode = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.title,
                payload.topic,
                payload.genre,
                payload.audience,
                payload.tone,
                payload.target_chapter_count,
                payload.target_words_per_chapter,
                payload.logline,
                payload.synopsis,
                payload.global_summary,
                int(payload.privacy_mode),
                now,
                project_id,
            ),
        )
        return row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> dict[str, bool]:
    require_project(project_id)
    with connect() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return {"ok": True}


def require_chapter(project_id: str, chapter_id: str) -> dict[str, Any]:
    require_project(project_id)
    with connect() as conn:
        chapter = row_to_dict(
            conn.execute(
                "SELECT * FROM chapters WHERE id = ? AND project_id = ?",
                (chapter_id, project_id),
            ).fetchone()
        )
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found in project")
    return chapter


@app.post("/api/projects/{project_id}/chapters")
def create_chapter(project_id: str, payload: ChapterIn) -> dict[str, Any]:
    require_project(project_id)
    chapter_id = new_id()
    now = utc_now()
    word_count = len(payload.draft)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chapters (
                id, project_id, outline_id, chapter_number, title, brief, draft,
                summary, word_count, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chapter_id,
                project_id,
                payload.outline_id,
                payload.chapter_number,
                payload.title,
                payload.brief,
                payload.draft,
                payload.summary,
                word_count,
                payload.status,
                now,
                now,
            ),
        )
        chapter = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
    write_chapter_snapshot(project_id, chapter)
    return chapter


@app.get("/api/projects/{project_id}/chapters")
def list_chapters(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        )


@app.get("/api/projects/{project_id}/chapters/{chapter_id}")
def get_chapter(project_id: str, chapter_id: str) -> dict[str, Any]:
    return require_chapter(project_id, chapter_id)


@app.patch("/api/projects/{project_id}/chapters/{chapter_id}")
def update_chapter(project_id: str, chapter_id: str, payload: ChapterIn) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE chapters
            SET outline_id = ?, chapter_number = ?, title = ?, brief = ?, draft = ?,
                summary = ?, word_count = ?, status = ?, updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (
                payload.outline_id,
                payload.chapter_number,
                payload.title,
                payload.brief,
                payload.draft,
                payload.summary,
                len(payload.draft),
                payload.status,
                now,
                chapter_id,
                project_id,
            ),
        )
        chapter = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
    write_chapter_snapshot(project_id, chapter)
    return chapter


@app.post("/api/projects/{project_id}/chapters/{chapter_id}/versions")
def create_chapter_version(project_id: str, chapter_id: str, payload: VersionIn) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    version_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chapter_versions (id, project_id, chapter_id, label, content, model, context_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (version_id, project_id, chapter_id, payload.label, payload.content, payload.model, payload.context_summary, now),
        )
        return row_to_dict(conn.execute("SELECT * FROM chapter_versions WHERE id = ?", (version_id,)).fetchone())


@app.get("/api/projects/{project_id}/chapters/{chapter_id}/versions")
def list_chapter_versions(project_id: str, chapter_id: str) -> list[dict[str, Any]]:
    require_chapter(project_id, chapter_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapter_versions WHERE project_id = ? AND chapter_id = ? ORDER BY created_at DESC",
                (project_id, chapter_id),
            ).fetchall()
        )


@app.post("/api/projects/{project_id}/chapters/{chapter_id}/versions/{version_id}/select")
def select_chapter_version(project_id: str, chapter_id: str, version_id: str) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    with connect() as conn:
        version = row_to_dict(
            conn.execute(
                "SELECT * FROM chapter_versions WHERE id = ? AND project_id = ? AND chapter_id = ?",
                (version_id, project_id, chapter_id),
            ).fetchone()
        )
        if not version:
            raise HTTPException(status_code=404, detail="Version not found in chapter")
        conn.execute(
            """
            UPDATE chapters
            SET draft = ?, selected_version_id = ?, word_count = ?, updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (version["content"], version_id, len(version["content"]), utc_now(), chapter_id, project_id),
        )
        chapter = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
    write_chapter_snapshot(project_id, chapter)
    return chapter


@app.post("/api/projects/{project_id}/chapters/{chapter_id}/finalize")
def finalize_chapter(project_id: str, chapter_id: str) -> dict[str, Any]:
    chapter = require_chapter(project_id, chapter_id)
    summary = chapter["summary"] or f"第 {chapter['chapter_number']} 章定稿：{chapter['draft'][:80]}"
    now = utc_now()
    with connect() as conn:
        conn.execute(
            "UPDATE chapters SET status = 'final', summary = ?, updated_at = ? WHERE id = ? AND project_id = ?",
            (summary, now, chapter_id, project_id),
        )
        memory_id = new_id()
        conn.execute(
            """
            INSERT INTO memory_items (id, project_id, title, category, content, payload, status, created_at, updated_at)
            VALUES (?, ?, ?, 'chapter_summary', ?, '{}', 'approved', ?, ?)
            """,
            (memory_id, project_id, f"第 {chapter['chapter_number']} 章摘要", summary, now, now),
        )
        updated = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
    append_wiki_page(project_id, "global-summary.md", f"\n\n## 第 {chapter['chapter_number']} 章\n\n{summary}", chapter_id)
    return updated


def write_chapter_snapshot(project_id: str, chapter: dict[str, Any]) -> None:
    root = project_root(project_id)
    path = root / "manuscript" / f"chapter-{int(chapter['chapter_number']):03}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {chapter['title'] or '未命名章节'}\n\n{chapter['draft'] or ''}", encoding="utf-8")


def upsert_wiki_page(project_id: str, relative_path: str, content: str, source_chapter_id: str = "") -> dict[str, Any]:
    target = safe_wiki_path(project_id, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    now = utc_now()
    with connect() as conn:
        existing = row_to_dict(
            conn.execute(
                "SELECT * FROM wiki_pages WHERE project_id = ? AND path = ?",
                (project_id, relative_path),
            ).fetchone()
        )
        if existing:
            conn.execute(
                "UPDATE wiki_pages SET content = ?, updated_at = ? WHERE id = ?",
                (content, now, existing["id"]),
            )
            page_id = existing["id"]
        else:
            page_id = new_id()
            conn.execute(
                """
                INSERT INTO wiki_pages (id, project_id, path, title, content, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (page_id, project_id, relative_path, Path(relative_path).stem, content, now),
            )
        conn.execute(
            """
            INSERT INTO wiki_page_revisions (id, project_id, path, content, source_chapter_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id(), project_id, relative_path, content, source_chapter_id, now),
        )
        return row_to_dict(conn.execute("SELECT * FROM wiki_pages WHERE id = ?", (page_id,)).fetchone())


def append_wiki_page(project_id: str, relative_path: str, content: str, source_chapter_id: str = "") -> dict[str, Any]:
    target = safe_wiki_path(project_id, relative_path)
    previous = target.read_text(encoding="utf-8") if target.exists() else f"# {Path(relative_path).stem}\n"
    return upsert_wiki_page(project_id, relative_path, previous + content, source_chapter_id)


@app.post("/api/projects/{project_id}/wiki/write")
def wiki_write(project_id: str, payload: WikiWriteIn) -> dict[str, Any]:
    require_project(project_id)
    return upsert_wiki_page(project_id, payload.path, payload.content, payload.source_chapter_id)


@app.post("/api/projects/{project_id}/wiki/append")
def wiki_append(project_id: str, payload: WikiWriteIn) -> dict[str, Any]:
    require_project(project_id)
    return append_wiki_page(project_id, payload.path, payload.content, payload.source_chapter_id)


@app.get("/api/projects/{project_id}/wiki/read")
def wiki_read(project_id: str, path: str) -> dict[str, str]:
    require_project(project_id)
    target = safe_wiki_path(project_id, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


@app.get("/api/projects/{project_id}/wiki/search")
def wiki_search(project_id: str, q: str = "") -> list[dict[str, Any]]:
    require_project(project_id)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM wiki_pages
            WHERE project_id = ? AND (path LIKE ? OR content LIKE ?)
            ORDER BY updated_at DESC
            """,
            (project_id, f"%{q}%", f"%{q}%"),
        ).fetchall()
        return rows_to_dicts(rows)


@app.get("/api/projects/{project_id}/wiki/revisions")
def wiki_revisions(project_id: str, path: str) -> list[dict[str, Any]]:
    require_project(project_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM wiki_page_revisions WHERE project_id = ? AND path = ? ORDER BY created_at DESC",
                (project_id, path),
            ).fetchall()
        )


@app.get("/api/projects/{project_id}/wiki/lint")
def wiki_lint(project_id: str) -> dict[str, Any]:
    require_project(project_id)
    with connect() as conn:
        pages = rows_to_dicts(conn.execute("SELECT * FROM wiki_pages WHERE project_id = ?", (project_id,)).fetchall())
    orphan_pages = [page["path"] for page in pages if page["path"] != "index.md" and page["path"] not in " ".join(p["content"] for p in pages)]
    return {"orphan_pages": orphan_pages, "page_count": len(pages), "warnings": []}


@app.get("/api/projects/{project_id}/{resource}")
def list_generic(project_id: str, resource: str) -> list[dict[str, Any]]:
    table = table_for_resource(resource)
    require_project(project_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(f"SELECT * FROM {table} WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
        )


@app.post("/api/projects/{project_id}/{resource}")
def create_generic(project_id: str, resource: str, payload: GenericIn) -> dict[str, Any]:
    table = table_for_resource(resource)
    require_project(project_id)
    record_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {table} (id, project_id, title, category, content, payload, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                project_id,
                payload.title,
                payload.category,
                payload.content,
                json.dumps(payload.payload, ensure_ascii=False),
                payload.status,
                now,
                now,
            ),
        )
        return row_to_dict(conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone())


@app.patch("/api/projects/{project_id}/{resource}/{record_id}")
def update_generic(project_id: str, resource: str, record_id: str, payload: GenericIn) -> dict[str, Any]:
    table = table_for_resource(resource)
    require_project(project_id)
    now = utc_now()
    with connect() as conn:
        existing = conn.execute(f"SELECT * FROM {table} WHERE id = ? AND project_id = ?", (record_id, project_id)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Record not found")
        conn.execute(
            f"""
            UPDATE {table}
            SET title = ?, category = ?, content = ?, payload = ?, status = ?, updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (
                payload.title,
                payload.category,
                payload.content,
                json.dumps(payload.payload, ensure_ascii=False),
                payload.status,
                now,
                record_id,
                project_id,
            ),
        )
        return row_to_dict(conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone())


@app.delete("/api/projects/{project_id}/{resource}/{record_id}")
def delete_generic(project_id: str, resource: str, record_id: str) -> dict[str, bool]:
    table = table_for_resource(resource)
    require_project(project_id)
    with connect() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id = ? AND project_id = ?", (record_id, project_id))
    return {"ok": True}


def table_for_resource(resource: str) -> str:
    table = GENERIC_TABLES.get(resource)
    if not table:
        raise HTTPException(status_code=404, detail="Unknown resource")
    return table


@app.post("/api/projects/{project_id}/ai/{workflow}")
def run_ai_workflow(project_id: str, workflow: str, payload: AiWorkflowIn) -> dict[str, Any]:
    require_project(project_id)
    output = build_stub_ai_output(workflow, payload)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO ai_runs (id, project_id, workflow, input_snapshot, output_text, model, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'success', ?)
            """,
            (
                new_id(),
                project_id,
                workflow,
                json.dumps(payload.model_dump(), ensure_ascii=False),
                output["text"],
                output["model"],
                now,
            ),
        )
    if workflow == "score_chapter" and payload.chapter_id:
        require_chapter(project_id, payload.chapter_id)
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO chapter_scores (id, project_id, chapter_id, total_score, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (new_id(), project_id, payload.chapter_id, output["score"], json.dumps(output, ensure_ascii=False), now),
            )
    if workflow == "generate_chapter_variants" and payload.chapter_id:
        for index in range(max(1, payload.count)):
            create_chapter_version(
                project_id,
                payload.chapter_id,
                VersionIn(label=f"AI 版本 {index + 1}", content=f"{output['text']}\n\n候选版本 {index + 1}。"),
            )
    return output


def build_stub_ai_output(workflow: str, payload: AiWorkflowIn) -> dict[str, Any]:
    titles = {
        "generate_setting": "小说设定",
        "generate_characters": "人物卡",
        "generate_outline": "总纲",
        "generate_chapter_directory": "章节目录",
        "generate_chapter_brief": "本章大纲",
        "generate_chapter_draft": "章节正文",
        "summarize_chapter": "章节摘要",
        "extract_memory": "记忆提取",
        "extract_timeline_events": "时间线提取",
        "extract_relationships": "关系变化",
        "check_consistency": "一致性检查",
        "check_taboo_rules": "雷点检查",
        "analyze_style_sample": "风格分析",
        "revise_selection": "改写结果",
        "score_chapter": "章节评分",
    }
    title = titles.get(workflow, workflow)
    text = f"## {title}\n\n这是本地 MVP 的可编辑 AI 占位结果。输入提示：{payload.prompt or payload.content or '无'}"
    score = 82 if workflow == "score_chapter" else 0
    return {
        "workflow": workflow,
        "model": "local-stub",
        "text": text,
        "score": score,
        "items": [{"title": title, "content": text}],
    }


def project_chapters_for_export(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        )


def render_markdown(project_id: str) -> str:
    project = require_project(project_id)
    chapters = project_chapters_for_export(project_id)
    lines = [f"# {project['title']}", ""]
    if project.get("synopsis"):
        lines.extend(["## 简介", "", project["synopsis"], ""])
    for chapter in chapters:
        lines.extend([f"## 第 {chapter['chapter_number']} 章 {chapter['title']}", "", chapter["draft"] or "", ""])
    return "\n".join(lines)


@app.get("/api/projects/{project_id}/export/markdown", response_class=PlainTextResponse)
def export_markdown(project_id: str) -> str:
    content = render_markdown(project_id)
    export_path = project_root(project_id) / "exports" / "novel.md"
    export_path.write_text(content, encoding="utf-8")
    return content


@app.get("/api/projects/{project_id}/export/txt", response_class=PlainTextResponse)
def export_txt(project_id: str) -> str:
    content = render_markdown(project_id).replace("#", "")
    export_path = project_root(project_id) / "exports" / "novel.txt"
    export_path.write_text(content, encoding="utf-8")
    return content


@app.get("/api/projects/{project_id}/export/docx")
def export_docx(project_id: str) -> Response:
    content = render_markdown(project_id)
    try:
        from docx import Document

        buffer = BytesIO()
        document = Document()
        for line in content.splitlines():
            if line.startswith("# "):
                document.add_heading(line.removeprefix("# "), level=1)
            elif line.startswith("## "):
                document.add_heading(line.removeprefix("## "), level=2)
            else:
                document.add_paragraph(line)
        document.save(buffer)
        data = buffer.getvalue()
    except Exception:
        data = content.encode("utf-8")
    (project_root(project_id) / "exports" / "novel.docx").write_bytes(data)
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/api/projects/{project_id}/export/pdf")
def export_pdf(project_id: str) -> Response:
    content = render_markdown(project_id)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        _width, height = A4
        y = height - 48
        for line in content.splitlines():
            if y < 48:
                pdf.showPage()
                y = height - 48
            pdf.drawString(48, y, line[:92])
            y -= 18
        pdf.save()
        data = buffer.getvalue()
    except Exception:
        data = content.encode("utf-8")
    (project_root(project_id) / "exports" / "novel.pdf").write_bytes(data)
    return Response(data, media_type="application/pdf")


@app.get("/api/projects/{project_id}/export/epub")
def export_epub(project_id: str) -> Response:
    content = render_markdown(project_id)
    try:
        from ebooklib import epub

        project = require_project(project_id)
        book = epub.EpubBook()
        book.set_identifier(project_id)
        book.set_title(project["title"])
        book.set_language("zh-CN")
        chapter = epub.EpubHtml(title=project["title"], file_name="novel.xhtml", lang="zh-CN")
        chapter.content = "<pre>" + content.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"
        book.add_item(chapter)
        book.toc = (chapter,)
        book.spine = ["nav", chapter]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        buffer = BytesIO()
        epub.write_epub(buffer, book)
        data = buffer.getvalue()
    except Exception:
        data = content.encode("utf-8")
    (project_root(project_id) / "exports" / "novel.epub").write_bytes(data)
    return Response(data, media_type="application/epub+zip")
