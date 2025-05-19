import requests
import os
from .logger import setup_logger

# Set up logger for this module
logger = setup_logger("bank_llm.ollama", "ollama.log")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME  = os.getenv("OLLAMA_MODEL", "llama3.2")  # pulled with `ollama run llama3.2`

def generate(prompt: str, stream: bool = False, **gen_kwargs) -> str:
    """
    Call the local Ollama server and return the full response text.
    """
    body = {
        "model": f"{MODEL_NAME}:latest",
        "prompt": prompt,
        "stream": stream,
        **gen_kwargs,          # e.g. temperature, top_p…
    }
    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=body, timeout=180)
    r.raise_for_status()
    data = r.json()
    return data["response"]

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        logger.info(f"Initialized Ollama client with base URL: {base_url}")

    def generate(self, prompt: str, model: str = "llama2") -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt}
            )
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Generated response for prompt: {prompt[:100]}...")
            return result["response"]
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble generating a response at the moment."
