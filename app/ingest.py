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

# Model & Vector-store paths
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_PATH = Path("vector_store/faiss.index")
META_PATH = Path("vector_store/meta.pkl")

# Redaction and parsing constants
_clean_re = re.compile(
    r"(?:\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b)|(?:\b\d{11,14}\b)",
    flags=re.I
)
QUESTION_MARK = "?"


def open_utf8(p: Path):
    try:
        return open(p, mode="r", encoding="utf-8")
    except UnicodeDecodeError:
        return io.StringIO(p.read_bytes().decode("utf-8", errors="replace"))


def sanitize(text: str) -> str:
    text = text.lower()
    return _clean_re.sub("[REDACTED]", text).strip()


def _rows_to_qa(series: pd.Series):
    q, buffer = None, []
    for cell in series.astype(str).str.strip():
        if not cell:
            continue
        if cell.endswith(QUESTION_MARK):
            if q and buffer:
                yield q, "\n".join(buffer).strip()
            q, buffer = cell, []
        else:
            buffer.append(cell)
    if q and buffer:
        yield q, "\n".join(buffer).strip()


def _read_generic(path: Path):
    suffix = path.suffix.lower()

    if suffix == ".json":
        with open_utf8(path) as f:
            data = json.load(f)
        for cat in data.get("categories", []):
            cname = cat.get("category", "")
            for qa in cat.get("questions", []):
                q, a = qa.get("question", ""), qa.get("answer", "")
                yield f"Category: {cname}\nQ: {q}\nA: {a}"

    elif suffix in (".xlsx", ".xls"):
        sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
        for sheet_name, df in sheets.items():
            # skip sheets with no columns
            if df is None or df.columns.size == 0:
                continue
            cols = {c.lower(): c for c in df.columns}
            # two-column Q/A detection
            if any("question" in k for k in cols) and any("answer" in k for k in cols):
                q_col = next(cols[k] for k in cols if "question" in k)
                a_col = next(cols[k] for k in cols if "answer" in k)
                for q, a in df[[q_col, a_col]].fillna("").itertuples(index=False):
                    if str(q).strip():
                        yield f"Sheet: {sheet_name}\nQ: {q}\nA: {a}"
                continue
            # single-column vertical layout fallback
            first_col = df.iloc[:, 0].replace(np.nan, "")
            for q, a in _rows_to_qa(first_col):
                yield f"Sheet: {sheet_name}\nQ: {q}\nA: {a}"

    elif suffix == ".csv":
        with open_utf8(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row.get("text", "")

    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        yield text


def build_or_update_index(dataset_dir: str):
    dataset_dir = Path(dataset_dir)
    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    index = faiss.IndexFlatIP(dim)
    meta = []

    files = [p for p in dataset_dir.glob("**/*") if p.is_file()]
    with tqdm(files, desc="Building index", unit="file") as pbar:
        for file in pbar:
            for chunk in _read_generic(file):
                clean = sanitize(chunk)
                emb = model.encode(clean, convert_to_numpy=True)
                index.add(emb.reshape(1, -1))
                meta.append(clean)

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "wb") as f:
        pickle.dump(meta, f)
    print(f"✅  Vector store built with {len(meta)} chunks")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python -m app.ingest <dataset_dir>")
        sys.exit(1)
    build_or_update_index(sys.argv[1])