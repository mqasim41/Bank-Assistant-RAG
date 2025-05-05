import requests
import os

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
