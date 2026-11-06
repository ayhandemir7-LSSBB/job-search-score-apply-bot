"""Paths, keys and model names. Everything is overridable from .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
DRIVE_DIR = DATA / "drive"          # local mirror of the Google Drive project folder
POSTINGS_DIR = DATA / "postings"    # sample job postings used by the lab proof
CHROMA_DIR = DATA / "chroma"        # vector database
CHUNKS_PATH = DATA / "chunks.jsonl" # every indexed chunk, for BM25 and inspection
DB_PATH = DATA / "jobs.db"          # SQLite job board
HISTORY_PATH = DATA / "history.json"  # scored jobs exported from the Claude artifact
EXPORTS_DIR = DATA / "exports"      # generated CV and cover letter files

# Google Drive folder "Claude Project for Job2026"
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1YthY14bq3JY_5IA3x4O4tS-7PzBEEHn2")
GOOGLE_CREDENTIALS = ROOT / os.getenv("GOOGLE_CREDENTIALS", "credentials.json")
GOOGLE_TOKEN = ROOT / os.getenv("GOOGLE_TOKEN", "token.json")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.6-luna")       # assessment and materials
LLM_MODEL_FAST = os.getenv("LLM_MODEL_FAST", "gpt-5.4-mini")  # posting decomposition (fast)
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "medium")

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")  # runs locally, documents never leave the machine
EMBED_QUERY_PROMPT = "Represent this sentence for searching relevant passages: "
COHERE_RERANK_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5")
LOCAL_RERANK_MODEL = os.getenv("LOCAL_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER = os.getenv("RERANKER", "auto")  # auto = Cohere when a key is set, else the local cross-encoder

COLLECTION = "portfolio_evidence"
CHUNK_TOKENS = 320      # target chunk size
CHUNK_OVERLAP = 60      # tokens carried into the next chunk
EVIDENCE_BUDGET = 3200  # tokens of evidence sent to the LLM per assessment
EVIDENCE_EXCLUDE_TYPES = ("cover_letter",)  # style examples, not proof: they echo the posting they were written for
PRIMARY_TYPES = ("cv", "case_study", "strategy_map", "career_narrative", "portfolio_data")  # outrank restatements
