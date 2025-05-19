
# Bank‑LLM Prototype

Minimal end‑to‑end stack:

1. **Ingest** anonymised bank docs → build FAISS vector store
2. **Retrieve** relevant chunks at query‑time (MiniLM embeddings)
3. **Generate** final answer with DeepSeek‑LLM‑6B‑Chat
4. `/add-document` endpoint triggers background re‑index

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Initial embedding build
python -m app.ingest data/

# Run API
uvicorn app.main:app --reload --port 8000
```

Test:

```bash
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question": "How can I activate mobile banking?"}'
```

The architecture diagram is in `docs/architecture.png`.
