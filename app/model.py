from app.ollama_client import generate

class BankAssistant:
    _system = (
        "You are BankGPT, a polite, professional CSR for a local bank. "
        "Use the context below. If you do not know the answer, apologise briefly."
    )

    def chat(self, question: str, context_docs: list[str]) -> str:
        context = "\n\n".join(context_docs[:4])
        prompt = (
            f"<|system|>\n{self._system}\n"
            f"<|context|>\n{context}\n"
            f"<|user|>\n{question}\n<|assistant|>"
        )
        return generate(prompt, stream=False, temperature=0.2, top_p=0.95)
