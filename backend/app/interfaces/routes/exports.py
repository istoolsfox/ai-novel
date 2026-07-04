"""接口层 · 导出路由。"""
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from ...application.export_service import (
    build_export_manifest,
    export_docx_file,
    export_epub_file,
    export_markdown_file,
    export_pdf_file,
    export_txt_file,
)

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["exports"])


@router.get("/manifest")
def export_manifest(project_id: str) -> dict[str, Any]:
    return build_export_manifest(project_id)


@router.get("/markdown", response_class=PlainTextResponse)
def export_markdown(project_id: str) -> str:
    return export_markdown_file(project_id)


@router.get("/txt", response_class=PlainTextResponse)
def export_txt(project_id: str) -> str:
    return export_txt_file(project_id)


@router.get("/docx")
def export_docx(project_id: str) -> Response:
    data = export_docx_file(project_id)
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/pdf")
def export_pdf(project_id: str) -> Response:
    data = export_pdf_file(project_id)
    return Response(data, media_type="application/pdf")


@router.get("/epub")
def export_epub(project_id: str) -> Response:
    data = export_epub_file(project_id)
    return Response(data, media_type="application/epub+zip")
