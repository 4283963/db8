from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from .config import settings


class VectorStore:
    def __init__(
        self,
        persist_dir: Path = settings.CHROMA_PERSIST_DIR,
        embedding_model_name: str = settings.EMBEDDING_MODEL_NAME,
    ):
        self.persist_dir = persist_dir
        self.embedding_model_name = embedding_model_name
        self.embeddings: Optional[Embeddings] = None
        self.vector_store: Optional[Chroma] = None
        self._initialize()

    def _initialize(self) -> None:
        model_kwargs = {"device": "cpu"}
        encode_kwargs = {"normalize_embeddings": True}
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
        )

        self.vector_store = Chroma(
            persist_directory=str(self.persist_dir),
            embedding_function=self.embeddings,
        )

    def add_documents(self, documents: List[Document]) -> None:
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        self.vector_store.add_documents(documents)

    def get_retriever(self, top_k: int = settings.TOP_K):
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        return self.vector_store.as_retriever(search_kwargs={"k": top_k})

    def similarity_search(self, query: str, top_k: int = settings.TOP_K) -> List[Document]:
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        return self.vector_store.similarity_search(query, k=top_k)

    def delete_collection(self) -> None:
        if self.vector_store:
            self.vector_store.delete_collection()
            self._initialize()

    def count_documents(self) -> int:
        if not self.vector_store:
            return 0
        return len(self.vector_store.get()["ids"])
