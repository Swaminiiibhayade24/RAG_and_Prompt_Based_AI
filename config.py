from pathlib import Path
import os

APP_NAME = "IntelliDB AI"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = BASE_DIR / "knowledge_base"
CHROMA_DIR = DATA_DIR / "chroma"
CHAT_STORE = DATA_DIR / "chat_history.json"

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_CHAT_MODEL = "llama3.2"
OLLAMA_EMBED_MODEL = "nomic-embed-text"

CHUNK_SIZE = 850
CHUNK_OVERLAP = 140
TOP_K = 5
TEMPERATURE = 0.25
MAX_HISTORY_MESSAGES = 8

DATA_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
