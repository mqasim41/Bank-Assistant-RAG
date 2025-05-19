from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil, uuid, asyncio, os

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

# Initialize components
retriever = Retriever()
assistant = BankAssistant()

# Set up logger for this module
logger = setup_logger("bank_llm.api", "api.log")

# Ensure uploads directory exists
UPLOADS_DIR = "data/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

class Query(BaseModel):
    question: str

def refresh_retriever():
    """Refresh the retriever with the latest documents"""
    global retriever
    retriever = Retriever()

@app.post("/query")
async def ask_llm(q: Query):
    docs = retriever.search(q.question)
    answer = assistant.chat(q.question, docs)
    return {"answer": answer, "context": docs}

@app.post("/add-document")
async def add_document(doc: UploadFile = File(...)):
    if not doc.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    temp_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4()}_{doc.filename}")
    try:
        # Save the file
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(doc.file, buffer)
        logger.info(f"Successfully uploaded file: {doc.filename}")
        
        # Process the document synchronously
        build_or_update_index(UPLOADS_DIR)
        logger.info(f"Processed document: {doc.filename}")
        
        # Refresh the retriever to include the new document
        refresh_retriever()
        logger.info("Retriever refreshed with new document")
        
        return {
            "status": "success", 
            "message": f"File {doc.filename} uploaded and processed successfully"
        }
    except Exception as e:
        logger.error(f"Failed to upload file {doc.filename}: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail=str(e))
