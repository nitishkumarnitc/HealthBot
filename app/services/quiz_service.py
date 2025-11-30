import logging
import json
import re
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.summary_service import llm  # reuse same LLM instance

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
        # Typical shape: result.generations -> [[Generation(...)]]
        gens = getattr(result, "generations", None)
        if gens and len(gens) > 0 and len(gens[0]) > 0:
            gen = gens[0][0]
            # prefer .text
            if hasattr(gen, "text") and gen.text is not None:
                return gen.text
            # some versions return a message object
            if hasattr(gen, "message") and getattr(gen.message, "content", None) is not None:
                return gen.message.content
            # sometimes generation itself is a tuple-like, try str
            return str(gen)
        # fallback: maybe result is a string already
        if isinstance(result, str):
            return result
        # last resort: stringify the whole object
        return str(result)
    except Exception:
        # don't crash extraction; return stringified result
        try:
            return str(result)
        except Exception:
            return ""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def generate_quiz_question(summary: str) -> dict:
    prompt = (
        "Create exactly one short comprehension question for a patient based on the summary below. "
        "Prefer short-answer format. Return a JSON object only with keys: question, options (null if not multiple-choice), "
        "answer (canonical), hint (one sentence). Example: {\"question\":\"...\",\"options\":null,\"answer\":\"...\",\"hint\":\"...\"}\n\n"
        f"SUMMARY:\n{summary}"
    )
    sys = SystemMessage(content="You are a clear quiz generator for patient education.")
    hum = HumanMessage(content=prompt)
    try:
        # NOTE: agenerate expects a batch (list of message-lists), so pass [[sys, hum]]
        result = await llm.agenerate(messages=[[sys, hum]])

        # extract text safely
        out_text = _extract_text_from_agenerate_result(result)
        logger.debug("LLM raw output (generate_quiz_question): %s", out_text)

        # try parse JSON blob
        m = re.search(r"(\{[\s\S]*\})", out_text)
        if m:
            try:
                j = json.loads(m.group(1))
                return j
            except json.JSONDecodeError:
                logger.debug("Found JSON-like blob but failed to decode; blob: %s", m.group(1))

        # fallback: return as plain question
        return {"question": out_text.strip(), "options": None, "answer": "", "hint": ""}
    except Exception as e:
        logger.exception("Quiz generation failed: %s", e)
        raise RuntimeError("Quiz generation failed") from e


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def evaluate_answer(summary: str, canonical_answer: str, user_answer: str) -> dict:
    """
    Ask the LLM to grade and produce explanation + citation snippets from summary.
    Returns JSON object: { score: float, verdict: str, explanation: str, citations: [str] }
    """
    prompt = (
        "You are a helpful grader. Grade the USER_ANSWER against the CANONICAL_ANSWER and the SUMMARY. "
        "Return JSON only with fields: score (0.0-1.0), verdict ('correct','partial','incorrect'), explanation (short), citations (list of short snippets from SUMMARY that justify the grade).\n\n"
        f"SUMMARY:\n{summary}\n\nCANONICAL_ANSWER:\n{canonical_answer}\n\nUSER_ANSWER:\n{user_answer}"
    )
    sys = SystemMessage(content="You are a fair grader for patient comprehension quizzes.")
    hum = HumanMessage(content=prompt)
    try:
        result = await llm.agenerate(messages=[[sys, hum]])
        out_text = _extract_text_from_agenerate_result(result)
        logger.debug("LLM raw output (evaluate_answer): %s", out_text)

        m = re.search(r"(\{[\s\S]*\})", out_text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                logger.debug("Found JSON-like blob but failed to decode; blob: %s", m.group(1))

        # fallback simple heuristic
        verdict = "correct" if canonical_answer.lower() in user_answer.lower() else "incorrect"
        score = 1.0 if verdict == "correct" else 0.0
        explanation = "Matches the canonical answer." if verdict == "correct" else "Does not match the canonical answer."
        return {"score": score, "verdict": verdict, "explanation": explanation, "citations": [canonical_answer[:120]]}
    except Exception as e:
        logger.exception("Evaluation failed: %s", e)
        raise RuntimeError("Evaluation failed") from e
