# app/services/summary_service.py
import os
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

load_dotenv()
logger = logging.getLogger("healthbot.summary_service")

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Create the LangChain Chat model instance (async)
# You can explicitly pass api_key or rely on env var OPENAI_API_KEY
llm = ChatOpenAI(temperature=0.2, model="gpt-4o-mini")  # adjust model name as needed


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def summarize_text_for_patient(text: str, max_tokens: int = 500) -> str:
    """
    Uses LangChain ChatOpenAI to generate a patient-friendly summary.
    """
    system = SystemMessage(content="You are an empathetic medical educator who writes in simple, non-technical language.")
    user_prompt = (
        "Summarize the following medical information into short simple sentences for a patient. "
        "Include a short 'Key takeaways' list with 3 bullets, and a one-line suggestion to consult their clinician if unsure. "
        "Do not provide medical advice.\n\n"
        f"TEXT:\n{text}"
    )
    human = HumanMessage(content=user_prompt)

    # LangChain `achat` or `agenerate` usage may vary by version.
    # We'll try `achat`/`apredict` style; if not available, fall back to running in threadpool.
    try:
        # many langchain versions provide an async `achat` method
        response = await llm.agenerate(messages=[system, human])
        # apredict returns the generated text directly
        return response.strip()
    except Exception as ex:
        # Fallback: try `agenerate` which returns Generation objects
        try:
            gen = await llm.agenerate([[system, human]])
            text_out = gen.generations[0][0].text
            return text_out.strip()
        except Exception as ex2:
            logger.exception("LangChain LLM summary failed: %s ; fallback error: %s", ex, ex2)
            raise RuntimeError(f"LLM summarization failed: {ex2}")
