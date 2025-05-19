import io
import json
import re
import csv
import pickle
import numpy as np
import pandas as pd
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import unicodedata
import html
from typing import List, Dict, Any
from .logger import setup_logger

# Set up logger for this module
logger = setup_logger("bank_llm.ingest", "ingest.log")

# Model & Vector-store paths
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_PATH = Path("vector_store/faiss.index")
META_PATH = Path("vector_store/meta.pkl")

# Enhanced PII detection patterns
PII_PATTERNS = {
    'credit_card': r'(?:\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b)',
    'ssn': r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
    'phone': r'\b(?:\+\d{1,3}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'account_number': r'\b\d{10,17}\b',
    'date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    'address': r'\b\d+\s+[A-Za-z\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way)\b',
}

# Compile all patterns
PII_REGEX = re.compile('|'.join(f'(?P<{k}>{v})' for k, v in PII_PATTERNS.items()), flags=re.I)

def normalize_text(text: str) -> str:
    """Normalize text by handling unicode, HTML entities, and whitespace."""
    # Decode HTML entities
    text = html.unescape(text)
    # Normalize unicode characters
    text = unicodedata.normalize('NFKC', text)
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def detect_and_redact_pii(text: str) -> str:
    """Detect and redact PII from text."""
    def replace_match(match):
        pii_type = match.lastgroup
        return f"[REDACTED_{pii_type.upper()}]"
    
    return PII_REGEX.sub(replace_match, text)

def clean_text(text: str) -> str:
    """Apply comprehensive text cleaning."""
    if not isinstance(text, str):
        return ""
    
    # Basic cleaning
    text = normalize_text(text)
    text = text.lower()
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', ' ', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Redact PII
    text = detect_and_redact_pii(text)
    
    return text.strip()

def validate_chunk(chunk: str) -> bool:
    """Validate if a text chunk is worth processing."""
    if not chunk or not isinstance(chunk, str):
        return False
    
    # Check minimum length (e.g., 10 characters)
    if len(chunk.strip()) < 10:
        return False
    
    # Check if it's not just whitespace or special characters
    if not re.search(r'[a-zA-Z]', chunk):
        return False
    
    return True

def process_chunk(chunk: str) -> str:
    """Process a single text chunk with all preprocessing steps."""
    if not validate_chunk(chunk):
        return ""
    
    return clean_text(chunk)

def open_utf8(p: Path):
    try:
        return open(p, mode="r", encoding="utf-8")
    except UnicodeDecodeError:
        return io.StringIO(p.read_bytes().decode("utf-8", errors="replace"))

def flatten_json(obj, parent_key=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            yield from flatten_json(v, new_key)
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_json(v, parent_key)
    else:
        yield f"{parent_key}: {obj}"

def _read_generic(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".json":
        with open_utf8(path) as f:
            data = json.load(f)
        for chunk in flatten_json(data):
            processed = process_chunk(chunk)
            if processed:
                yield processed
    elif suffix == ".csv":
        with open_utf8(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed = process_chunk(row.get("text", ""))
                if processed:
                    yield processed
    else:
        # for .txt and other files
        text = path.read_text(encoding="utf-8", errors="replace")
        processed = process_chunk(text)
        if processed:
            yield processed

def build_or_update_index(dataset_dir: str):
    dataset_dir = Path(dataset_dir)
    
    # Track processing statistics
    stats = {
        "total_files": 0,
        "processed_files": 0,
        "total_chunks": 0,
        "valid_chunks": 0,
        "redacted_pii": 0
    }

    # Convert all Excel files to txt per sheet
    for excel_path in dataset_dir.glob("**/*.xls*"):
        try:
            sheets = pd.read_excel(excel_path, sheet_name=None, engine="openpyxl")
            for sheet_name, df in sheets.items():
                txt_path = excel_path.parent / f"{excel_path.stem}_{sheet_name}.txt"
                df.to_csv(txt_path, index=False, sep="\t")
        except Exception as e:
            logger.warning(f"Failed to convert {excel_path}: {e}")

    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    index = faiss.IndexFlatIP(dim)
    meta = []

    # Ingest all non-Excel files (including generated txt)
    files = [p for p in dataset_dir.glob("**/*") if p.is_file() and p.suffix.lower() not in (".xlsx", ".xls")]
    stats["total_files"] = len(files)
    
    with tqdm(files, desc="Building index", unit="file") as pbar:
        for file in pbar:
            try:
                chunks = list(_read_generic(file))
                stats["total_chunks"] += len(chunks)
                stats["valid_chunks"] += len([c for c in chunks if c])
                stats["processed_files"] += 1
                
                for chunk in chunks:
                    if chunk:
                        emb = model.encode(chunk, convert_to_numpy=True)
                        index.add(emb.reshape(1, -1))
                        meta.append(chunk)
            except Exception as e:
                logger.error(f"Error processing {file}: {e}")

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "wb") as f:
        pickle.dump(meta, f)
    
    logger.info(f"Vector store built with {len(meta)} chunks")
    logger.info("Processing stats:")
    logger.info(f"   - Total files: {stats['total_files']}")
    logger.info(f"   - Processed files: {stats['processed_files']}")
    logger.info(f"   - Total chunks: {stats['total_chunks']}")
    logger.info(f"   - Valid chunks: {stats['valid_chunks']}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        logger.error("Usage: python -m app.ingest <dataset_dir>")
        sys.exit(1)
    build_or_update_index(sys.argv[1])
