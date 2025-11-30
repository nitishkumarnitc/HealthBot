# app/services/quiz_service.py
import logging
import json
import re
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.prompts import build_quiz_messages, build_grader_messages
from app.services.llm import llm  # reuse same LLM instance (ChatOpenAI)

logger = logging.getLogger("healthbot.quiz_service")


def _extract_text_from_agenerate_result(result) -> str:
    """
    Safely extract generated text from langchain_core agenerate result.
    Handles different possible shapes:
      - result.generations -> list[list[Generation]]
      - Generation may have .text or .message (with .content) attributes
      - result may already be a plain string (fallback)
    """
    try:
        gens = getattr(result, "generations", None)
        if gens and len(gens) > 0 and len(gens[0]) > 0:
            gen = gens[0][0]
            if hasattr(gen, "text") and gen.text is not None:
                return gen.text
            if hasattr(gen, "message") and getattr(gen.message, "content", None) is not None:
                return gen.message.content
            return str(gen)
        if isinstance(result, str):
            return result
        return str(result)
    except Exception:
        try:
            return str(result)
        except Exception:
            return ""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def generate_quiz_question(summary: str) -> dict:
    """
    Generate exactly one quiz question using centralized prompts.
    Returns a dict with keys: question, options (or None), answer (canonical), hint.
    """
    # build messages using prompts.py (returns [SystemMessage, HumanMessage])
    messages = build_quiz_messages(summary, prefer_short_answer=True)

    try:
        # agenerate expects a batch (list of message-lists)
        result = await llm.agenerate([messages])

        out_text = _extract_text_from_agenerate_result(result)
        logger.debug("LLM raw output (generate_quiz_question): %s", out_text[:1000])

        # try parse JSON blob from model output
        m = re.search(r"(\{[\s\S]*\})", out_text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                logger.debug("Found JSON-like blob but failed to decode; blob: %s", m.group(1)[:500])

        # fallback: return raw text as question
        return {"question": out_text.strip(), "options": None, "answer": "", "hint": ""}
    except Exception as e:
        logger.exception("Quiz generation failed: %s", e)
        raise RuntimeError("Quiz generation failed") from e


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def evaluate_answer(summary: str, canonical_answer: str, user_answer: str) -> dict:
    """
    Grade the user's answer using centralized grader prompts.
    Returns JSON: { score: float, verdict: str, explanation: str, citations: [str] }
    """
    messages = build_grader_messages(summary, canonical_answer, user_answer)

    try:
        result = await llm.agenerate([messages])
        out_text = _extract_text_from_agenerate_result(result)
        logger.debug("LLM raw output (evaluate_answer): %s", out_text[:1000])

        m = re.search(r"(\{[\s\S]*\})", out_text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                logger.debug("Found JSON-like blob but failed to decode; blob: %s", m.group(1)[:500])

        # fallback heuristic
        verdict = "correct" if canonical_answer.strip().lower() in user_answer.strip().lower() else "incorrect"
        score = 1.0 if verdict == "correct" else 0.0
        explanation = "Matches the canonical answer." if verdict == "correct" else "Does not match the canonical answer."
        return {"score": score, "verdict": verdict, "explanation": explanation, "citations": [canonical_answer[:120]]}
    except Exception as e:
        logger.exception("Evaluation failed: %s", e)
        raise RuntimeError("Evaluation failed") from e
