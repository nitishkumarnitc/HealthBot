# app/services/search_service.py
import os
import asyncio
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
logger = logging.getLogger("healthbot.search_service")
logger.setLevel(logging.INFO)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_BASE = os.getenv("TAVILY_BASE_URL", "").rstrip("/")
TAVILY_MOCK = os.getenv("TAVILY_MOCK", "false").lower() in ("1","true","yes")

_executor = ThreadPoolExecutor(max_workers=3)

# Try to import Tavily SDK (best-effort)
try:
    from tavily import TavilyClient  # adapt if SDK package differs
    TAVILY_SDK_AVAILABLE = True
    logger.info("Tavily SDK imported.")
except Exception as e:
    TavilyClient = None
    TAVILY_SDK_AVAILABLE = False
    logger.warning("Tavily SDK not available: %s", e)


def _format_pieces_from_results(results):
    """
    Normalizes various possible result shapes into a single string.
    Accepts:
      - list of dicts [{'title':..,'snippet':..,'content':..}, ...]
      - dict with 'results' key
      - plain string
    """
    if isinstance(results, dict):
        if "results" in results and isinstance(results["results"], list):
            results = results["results"]
        else:
            # maybe it's a single result dict
            results = [results]

    if isinstance(results, list):
        pieces = []
        for r in results:
            if not isinstance(r, dict):
                pieces.append(str(r))
                continue
            title = r.get("title") or r.get("headline") or ""
            snippet = r.get("snippet") or r.get("summary") or r.get("content") or ""
            source = r.get("url") or r.get("source") or ""
            header = f"{title} — {source}" if source else title
            pieces.append(f"{header}\n{snippet}".strip())
        return "\n\n---\n\n".join(p for p in pieces if p)
    # fallback: string or other
    return str(results)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def tavily_search(query: str, max_results: int = 4) -> dict:
    """
    Wrapper that calls Tavily SDK if present, otherwise raises helpful errors.
    It also supports a MOCK mode (TAVILY_MOCK env var).
    """
    if TAVILY_MOCK:
        logger.info("TAVILY_MOCK enabled — returning canned results")
        return {
            "results": [
                {"title": f"Mock result for {query}", "snippet": "This is a mock snippet", "content": f"Mock content for {query}."}
            ]
        }

    if not TAVILY_SDK_AVAILABLE:
        raise RuntimeError("Tavily SDK not installed or failed to import. Set TAVILY_MOCK=true to use mock results for local development.")

    # construct client — adapt to your SDK constructor if needed
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY, base_url=TAVILY_BASE)
    except TypeError:
        # fallback if SDK constructor signature differs
        client = TavilyClient(api_key=TAVILY_API_KEY)

    # Prefer an async SDK method if present
    if hasattr(client, "asearch") and asyncio.iscoroutinefunction(getattr(client, "asearch")):
        try:
            raw = await client.asearch(query=query, top_k=max_results)
            logger.info("Tavily async search returned type: %s", type(raw))
            return raw
        except Exception as e:
            logger.exception("Tavily async search failed: %s", e)
            raise

    # Fallback: run sync search in threadpool (common pattern)
    loop = asyncio.get_running_loop()

    def _sync_search():
        try:
            if hasattr(client, "search"):
                return client.search(query=query, top_k=max_results)
            # other common method names
            if hasattr(client, "query"):
                return client.query(query=query, top_k=max_results)
            raise RuntimeError("Tavily client has no known search method (tried 'asearch','search','query').")
        except Exception as e:
            # bubble up for tenacity to catch
            raise

    try:
        raw = await loop.run_in_executor(_executor, _sync_search)
        logger.info("Tavily sync search returned type: %s", type(raw))
        return raw
    except Exception as e:
        logger.exception("Tavily sync search failed: %s", e)
        raise


async def search_medical_info(topic: str) -> str:
    """
    Public helper used by workflow: returns a safe string summary built from Tavily results.
    """
    query = f"medical explanation for {topic}"
    try:
        raw = await tavily_search(query, max_results=4)
    except Exception as e:
        # raise a clear runtime error upward for API to report
        raise RuntimeError(f"Tavily search failed: {e}")

    # LOG raw for debugging (trim long content)
    try:
        logger.info("Raw tavily response (type=%s): %.500s", type(raw), str(raw)[:500])
    except Exception:
        logger.info("Raw tavily response (could not stringify)")

    # Normalize to a string summary (resilient to input shapes)
    try:
        summary = _format_pieces_from_results(raw)
        if not summary:
            return f"No useful search results found for '{topic}'."
        return summary
    except Exception as e:
        logger.exception("Failed to normalize tavily results: %s", e)
        # fallback: return repr
        return f"Unable to parse search results for '{topic}': {e}"
