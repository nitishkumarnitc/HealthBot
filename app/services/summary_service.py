# app/services/summary_service.py
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from app.services.llm import call_llm , llm
from app.core.prompts import build_summary_messages

logger = logging.getLogger("healthbot.summary_service")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def summarize_text_for_patient(text: str, max_tokens: int = 500) -> str:
    """
    Build messages from prompts.py and call the LLM via the simple call_llm wrapper.
    Returns a patient-friendly summary string.
    """
    if not llm:
        raise RuntimeError("LLM not initialized. Ensure langchain_openai is installed and configured.")

    # build messages (returns [SystemMessage, HumanMessage] when langchain is available)
    messages = build_summary_messages(text)

    try:
        # call_llm will call llm.agenerate([messages]) internally and return the text content
        out = await call_llm(llm, messages)
        return out.strip()
    except Exception as exc:
        logger.exception("LLM summarization failed: %s", exc)
        raise RuntimeError(f"LLM summarization failed: {exc}")
