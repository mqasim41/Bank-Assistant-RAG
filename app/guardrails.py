from .logger import setup_logger

# Set up logger for this module
logger = setup_logger("bank_llm.guardrails", "guardrails.log")

# Placeholder for future guard‑rail logic (content filtering, policy enforcement, etc.)
def enforce_policies(text: str) -> str:
    """Enforce content filtering and policy rules."""
    if "password" in text.lower():
        logger.warning("Detected potential password in text, redacting")
        return "[REDACTED]"
    return text
