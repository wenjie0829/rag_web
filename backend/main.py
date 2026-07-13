"""FastAPI entry point for the RAG Web backend."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_engine import RAGEngine
from fastapi.responses import FileResponse

load_dotenv()


app = FastAPI(title="RAG Web API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# 检查前端构建产物是否存在
frontend_dist = Path("/app/frontend/dist")
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

@app.get("/")
async def serve_index():
    # 尝试返回前端 index.html
    index_path = frontend_dist / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "RAG Web API is running, but frontend not built yet."}

engine = RAGEngine()
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class AskRequest(BaseModel):
    question: str = Field(min_length=1, description="用户的问题")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/documents")
def documents() -> dict[str, object]:
    """List indexed document sources so the frontend can restore its file view."""
    return {"documents": engine.list_documents()}


@app.get("/documents/chunk")
def document_chunk(
    source: str = Query(min_length=1),
    chunk_index: int = Query(ge=0),
) -> dict[str, object]:
    """Return a cited paragraph for the source-preview dialog."""
    chunk = engine.get_document_chunk(source, chunk_index)
    if not chunk:
        raise HTTPException(status_code=404, detail="未找到对应的引用片段")
    return {
        "source": chunk.source,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
    }


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, object]:
    """Receive and index one TXT, MD, PDF, or DOCX document."""
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="仅支持 txt、md、pdf 和 docx 文件")

    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(await file.read())
        chunk_count = engine.ingest_file(temporary_path, source=filename)
        return {"message": "文档已添加", "filename": filename, "chunks": chunk_count}
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文档处理失败：{exc}") from exc
    finally:
        await file.close()
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)

@app.get("/documents/content")
async def get_document_content(source: str):
    """从 ChromaDB 读取文件内容用于预览"""
    # 从 RAG 引擎获取该文件的所有分块
    chunks = engine.get_document_chunks(source)
    if not chunks:
        raise HTTPException(status_code=404, detail="文件不存在或未被索引")
    # 拼接所有分块
    content = "\n\n".join(chunks)
    return content  # 直接返回文本内容，前端显示

@app.post("/ask")
def ask(payload: AskRequest) -> dict[str, object]:
    """Retrieve relevant chunks and generate a DeepSeek-backed answer."""
    try:
        answer, documents = engine.answer(payload.question)
        return {
            "answer": answer,
            "sources": [
                {"source": document.source, "chunk_index": document.chunk_index}
                for document in documents
            ],
        }
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"问答服务调用失败：{exc}") from exc
