"""FastAPI entry point for the RAG Web backend."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from rag_engine import RAGEngine

load_dotenv()

app = FastAPI(title="RAG Web API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = RAGEngine()
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
frontend_dist = Path("/app/dist")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, description="用户的问题")


# ===================== API 路由（必须都在静态文件挂载之前）=====================

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


@app.get("/documents/content")
async def get_document_content(source: str):
    """从 ChromaDB 读取文件内容用于预览"""
    chunks = engine.get_document_chunks(source)
    if not chunks:
        # 兼容旧数据：如果查不到，尝试去掉扩展名再查一次
        source_without_ext = source.rsplit(".", 1)[0]
        chunks = engine.get_document_chunks(source_without_ext)
    if not chunks:
        # 模糊匹配（包含关系）
        all_docs = engine.list_documents()
        for doc in all_docs:
            if source in doc["source"] or doc["source"] in source:
                chunks = engine.get_document_chunks(doc["source"])
                if chunks:
                    break
    if not chunks:
        raise HTTPException(status_code=404, detail="文件不存在或未被索引")
    preview_chunks = chunks[:5]
    content = "\n\n".join(preview_chunks)
    return content


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
            # ⚠️ 用 run_in_threadpool 把这个耗时的同步操作（读文件 + 调用 embedding API）
            # 挪到独立线程执行，避免阻塞事件循环、影响其他并发请求和健康检查
            chunk_count = await run_in_threadpool(engine.ingest_file, temporary_path, source=filename)
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


# ===================== 静态文件挂载（必须放在所有 API 路由的最后）=====================
# html=True 会让访问 "/" 时自动返回 dist/index.html，
# 同时 /assets/xxx.js、/assets/xxx.css 等静态资源也会一并被这个挂载覆盖。
# 一定要放在文件最后，否则会拦截掉上面所有 /health、/documents、/ask 等接口。
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")