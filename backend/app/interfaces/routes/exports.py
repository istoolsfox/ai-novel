"""接口层 · 导出路由。

支持 markdown / txt / docx / pdf / epub 五种格式。
"""
from io import BytesIO
import re
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from ...infrastructure.database import connect, rows_to_dicts
from ...infrastructure.storage import project_root, require_project
from ...workflows.generation import clean_chapter_title

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["exports"])


def _project_chapters_for_export(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        )


def _render_markdown(project_id: str) -> str:
    project = require_project(project_id)
    chapters = _project_chapters_for_export(project_id)
    lines = [f"# {project['title']}", ""]
    if project.get("synopsis"):
        lines.extend(["## 简介", "", project["synopsis"], ""])
    for chapter in chapters:
        lines.extend([
            f"## 第 {chapter['chapter_number']} 章 {clean_chapter_title(chapter)}",
            "",
            _strip_embedded_chapter_heading(chapter),
            "",
        ])
    return "\n".join(lines)


def _strip_embedded_chapter_heading(chapter: dict[str, Any]) -> str:
    draft = (chapter.get("draft") or "").lstrip()
    if not draft:
        return ""
    title = clean_chapter_title(chapter)
    chapter_number = int(chapter.get("chapter_number") or 0)
    heading_pattern = rf"^(?:第\s*{chapter_number}\s*章(?:\s*[·:：-]\s*{re.escape(title)})?|{re.escape(title)})\s*\n+"
    return re.sub(heading_pattern, "", draft, count=1).lstrip()


@router.get("/markdown", response_class=PlainTextResponse)
def export_markdown(project_id: str) -> str:
    content = _render_markdown(project_id)
    export_path = project_root(project_id) / "exports" / "novel.md"
    export_path.write_text(content, encoding="utf-8")
    return content


@router.get("/txt", response_class=PlainTextResponse)
def export_txt(project_id: str) -> str:
    content = _render_markdown(project_id).replace("#", "")
    export_path = project_root(project_id) / "exports" / "novel.txt"
    export_path.write_text(content, encoding="utf-8")
    return content


@router.get("/docx")
def export_docx(project_id: str) -> Response:
    content = _render_markdown(project_id)
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


@router.get("/pdf")
def export_pdf(project_id: str) -> Response:
    content = _render_markdown(project_id)
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


@router.get("/epub")
def export_epub(project_id: str) -> Response:
    content = _render_markdown(project_id)
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
