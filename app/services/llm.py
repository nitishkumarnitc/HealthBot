# app/services/llm.py
import logging
import os
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger("call llm")

# Create/invoke LLM instance
try:
    from langchain_openai import ChatOpenAI
    MODEL = os.getenv("LC_MODEL", "gpt-4o-mini")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
    llm = ChatOpenAI(model=MODEL, temperature=0.2)
except Exception as e:
    llm = None
    logger.debug("langchain_openai.ChatOpenAI not available at import: %s", e)


async def call_llm(llm, messages):
    """
    Minimal wrapper for newest langchain-openai ChatOpenAI.
    Expects llm.agenerate to be available and messages list of SystemMessage/HumanMessage.
    """
    result = await llm.agenerate([messages])
    return result.generations[0][0].message.content

