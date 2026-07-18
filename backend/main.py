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
frontend_dist = Path("/app/dist")
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

@app.get("/documents/content")
async def get_document_content(source: str):
    # 1. 直接匹配
    chunks = engine.get_document_chunks(source)
    if chunks:
        content = "\n\n".join(chunks[:5])
        return content
    # 2. 去掉扩展名匹配
    source_without_ext = source.rsplit(".", 1)[0]
    chunks = engine.get_document_chunks(source_without_ext)
    if chunks:
        content = "\n\n".join(chunks[:5])
        return content
    # 3. 模糊匹配（包含关系）
    all_docs = engine.list_documents()
    for doc in all_docs:
        if source in doc["source"] or doc["source"] in source:
            chunks = engine.get_document_chunks(doc["source"])
            if chunks:
                content = "\n\n".join(chunks[:5])
                return content
    raise HTTPException(status_code=404, detail="文件不存在或未被索引")
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
        print(f"开始处理文件: {filename}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(await file.read())
            print(f"文件已保存到: {temporary_path}")
            
            # 使用完整文件名（含扩展名）作为 source
            chunk_count = engine.ingest_file(temporary_path, source=filename)
            print(f"索引完成，分块数: {chunk_count}")
            
            return {"message": "文档已添加", "filename": filename, "chunks": chunk_count}
            
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"处理错误: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"未知错误: {exc}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {exc}") from exc
    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.unlink(temporary_path)
            except Exception:
                pass
@app.get("/documents/content")
async def get_document_content(source: str):
    """从 ChromaDB 读取文件内容用于预览"""
    chunks = engine.get_document_chunks(source)
    if not chunks:
        # 兼容旧数据：如果查不到，尝试去掉扩展名再查一次
        source_without_ext = source.rsplit(".", 1)[0]
        chunks = engine.get_document_chunks(source_without_ext)
    if not chunks:
        all_docs = engine.list_documents()
        for doc in all_docs:
            if source in doc["source"] or doc["source"] in source:
                chunks = engine.get_document_chunks(doc["source"])
                if chunks:
                    break
    if not chunks:
        raise HTTPException(status_code=404, detail="文件不存在或未被索引")
    # 拼接所有分块
    preview_chunks = chunks[:5]
    content = "\n\n".join(preview_chunks)
    return content

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
