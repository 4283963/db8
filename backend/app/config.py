import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DOCX_DIR: Path = Path("./data/docx")
    CHROMA_PERSIST_DIR: Path = Path("./chroma_db")
    EMBEDDING_MODEL_NAME: str = "shibing624/text2vec-base-chinese"
    LLM_MODEL_NAME: str = "qwen2:7b"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

BASE_DIR = Path(__file__).resolve().parent.parent
if not settings.DOCX_DIR.is_absolute():
    settings.DOCX_DIR = BASE_DIR / settings.DOCX_DIR
if not settings.CHROMA_PERSIST_DIR.is_absolute():
    settings.CHROMA_PERSIST_DIR = BASE_DIR / settings.CHROMA_PERSIST_DIR

settings.DOCX_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
