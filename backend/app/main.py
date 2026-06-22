from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .config import settings
from .document_loader import DocumentLoader
from .vector_store import VectorStore
from .chat import ChatService

app = FastAPI(title="Local RAG Q&A API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

document_loader = DocumentLoader()
vector_store = VectorStore()
chat_service = ChatService(vector_store)


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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/documents")
async def list_documents():
    files = document_loader.get_file_list()
    indexed_count = vector_store.count_documents()
    return {"files": files, "indexed_chunks": indexed_count}


@app.post("/api/index", response_model=IndexResponse)
async def index_documents():
    try:
        files = document_loader.get_file_list()
        if not files:
            raise HTTPException(
                status_code=404,
                detail=f"No docx files found in {settings.DOCX_DIR}",
            )

        chunks = document_loader.load_and_split()
        vector_store.delete_collection()
        vector_store.add_documents(chunks)

        return IndexResponse(
            message="Documents indexed successfully",
            files_processed=files,
            chunks_count=len(chunks),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if vector_store.count_documents() == 0:
            raise HTTPException(
                status_code=400,
                detail="No documents indexed. Please call /api/index first.",
            )

        result = chat_service.chat(
            question=request.question,
            chat_history=request.chat_history,
        )
        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
