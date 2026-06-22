from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import settings


class DocumentLoader:
    def __init__(self, docx_dir: Path = settings.DOCX_DIR):
        self.docx_dir = docx_dir

    def load_docx_files(self) -> List[Document]:
        documents: List[Document] = []
        docx_files = list(self.docx_dir.glob("*.docx"))

        for docx_file in docx_files:
            loader = Docx2txtLoader(str(docx_file))
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = str(docx_file.name)
            documents.extend(docs)

        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )
        return text_splitter.split_documents(documents)

    def load_and_split(self) -> List[Document]:
        documents = self.load_docx_files()
        return self.split_documents(documents)

    def get_file_list(self) -> List[str]:
        return [f.name for f in self.docx_dir.glob("*.docx")]
