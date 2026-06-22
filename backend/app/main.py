import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .document_loader import DocumentLoader
from .vector_store import VectorStore
from .chat import ChatService
from .concurrency import ConcurrencyManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    生命周期管理：
    - 启动时加载重型资源（Embedding模型、向量库、LLM连接）
    - 初始化并发管理器
    - 关闭时清理线程池
    """
    concurrency = ConcurrencyManager.create(
        max_workers=settings.RAG_MAX_WORKERS,
        max_concurrent_chat=settings.RAG_MAX_CONCURRENT_CHAT,
        chat_timeout=settings.RAG_CHAT_TIMEOUT,
        index_timeout=settings.RAG_INDEX_TIMEOUT,
    )

    loop = asyncio.get_running_loop()

    document_loader = DocumentLoader()
    vector_store = await loop.run_in_executor(
        None, lambda: VectorStore(
            persist_dir=settings.CHROMA_PERSIST_DIR,
            embedding_model_name=settings.EMBEDDING_MODEL_NAME,
        )
    )
    chat_service = ChatService(vector_store, llm_model_name=settings.LLM_MODEL_NAME)

    app.state.document_loader = document_loader
    app.state.vector_store = vector_store
    app.state.chat_service = chat_service
    app.state.concurrency = concurrency

    yield

    concurrency.shutdown()


app = FastAPI(
    title="Local RAG Q&A API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, str]]


class IndexResponse(BaseModel):
    message: str
    files_processed: List[str]
    chunks_count: int


@app.get("/healthz", tags=["meta"])
async def health_check():
    """
    轻量级健康检查端点。
    完全不依赖任何可能阻塞的资源，
    即使线程池被占满也能在纳秒级返回。
    建议 K8s / 反向代理 / 状态轮询 使用此端点。
    """
    return {"status": "ok", "service": "local-rag"}


@app.get("/readyz", tags=["meta"])
async def readiness_check():
    """
    就绪检查：确认重型资源已加载且索引存在。
    此端点会触碰向量库，在线程池占满时可能延迟。
    """
    concurrency: ConcurrencyManager = app.state.concurrency
    if concurrency.is_indexing():
        raise HTTPException(status_code=503, detail="Indexing in progress")

    loop = asyncio.get_running_loop()
    try:
        count = await asyncio.wait_for(
            loop.run_in_executor(None, app.state.vector_store.count_documents),
            timeout=3.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Vector store not responding")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ready", "indexed_chunks": count}


@app.get("/api/health", tags=["meta"])
async def health_check_legacy():
    """兼容旧版路径"""
    return {"status": "healthy"}


@app.get("/api/stats", tags=["meta"])
async def get_stats():
    """查看并发和系统状态"""
    concurrency: ConcurrencyManager = app.state.concurrency
    stats = concurrency.get_stats()
    return stats


@app.get("/api/documents")
async def list_documents():
    """
    获取文档列表和索引状态。
    耗时操作（chroma count）丢到默认 executor，并加短超时，
    防止向量库卡住时把此接口也拖死。
    """
    document_loader: DocumentLoader = app.state.document_loader
    vector_store: VectorStore = app.state.vector_store

    loop = asyncio.get_running_loop()
    files = document_loader.get_file_list()

    try:
        indexed_count = await asyncio.wait_for(
            loop.run_in_executor(None, vector_store.count_documents),
            timeout=3.0,
        )
    except asyncio.TimeoutError:
        indexed_count = -1

    return {
        "files": files,
        "indexed_chunks": indexed_count,
        "is_indexing": app.state.concurrency.is_indexing(),
    }


@app.post("/api/index", response_model=IndexResponse)
async def index_documents():
    """
    索引文档。
    - 互斥锁：同时只允许一个索引任务
    - 专用线程池隔离：不影响健康检查
    - 长超时（默认 10 分钟）
    """
    concurrency: ConcurrencyManager = app.state.concurrency
    document_loader: DocumentLoader = app.state.document_loader
    vector_store: VectorStore = app.state.vector_store

    files = document_loader.get_file_list()
    if not files:
        raise HTTPException(
            status_code=404,
            detail=f"No docx files found in {settings.DOCX_DIR}",
        )

    def _do_index():
        chunks = document_loader.load_and_split()
        vector_store.delete_collection()
        vector_store.add_documents(chunks)
        return len(chunks)

    chunks_count = await concurrency.run_index(_do_index)

    return IndexResponse(
        message="Documents indexed successfully",
        files_processed=files,
        chunks_count=chunks_count,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG 问答接口。
    - 信号量：超过最大并发立即返回 503，不堆积请求
    - 专用线程池隔离：不影响 /healthz
    - 超时控制（默认 120 秒），超时返回 504
    """
    concurrency: ConcurrencyManager = app.state.concurrency
    vector_store: VectorStore = app.state.vector_store
    chat_service: ChatService = app.state.chat_service

    loop = asyncio.get_running_loop()
    try:
        indexed_count = await asyncio.wait_for(
            loop.run_in_executor(None, vector_store.count_documents),
            timeout=3.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Vector store not responding, please try again later",
        )

    if indexed_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents indexed. Please call /api/index first.",
        )

    def _do_chat():
        return chat_service.chat(
            question=request.question,
            chat_history=request.chat_history,
        )

    result = await concurrency.run_chat(_do_chat)
    return ChatResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
    )
