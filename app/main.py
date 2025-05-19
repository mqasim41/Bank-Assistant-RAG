from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil, uuid, asyncio

from app.retrieval import Retriever
from app.model import BankAssistant
from app.ingest import build_or_update_index
from fastapi.middleware.cors import CORSMiddleware
from .logger import setup_logger

app = FastAPI(title="Bank‑LLM Prototype")

# Add this before your routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # or list your front-end's exact URL(s)
    allow_credentials=True,
    allow_methods=["*"],            # includes OPTIONS, GET, POST, etc.
    allow_headers=["*"],            # or restrict to specific headers
)

retriever = Retriever()
assistant = BankAssistant()

# Set up logger for this module
logger = setup_logger("bank_llm.api", "api.log")

class Query(BaseModel):
    question: str

@app.post("/query")
async def ask_llm(q: Query):
    docs = retriever.fetch(q.question)
    answer = assistant.chat(q.question, docs)
    return {"answer": answer, "context": docs}

@app.post("/add-document")
async def add_document(doc: UploadFile = File(...)):
    temp_path = f"data/uploads/{uuid.uuid4()}_{doc.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(doc.file, buffer)
        logger.info(f"Successfully uploaded file: {doc.filename}")
    except Exception as e:
        logger.error(f"Failed to upload file {doc.filename}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    asyncio.create_task(asyncio.to_thread(build_or_update_index, "data/uploads"))
    logger.info(f"Queued document for processing: {doc.filename}")
    return {"status": "queued"}
