# app/core/prompts.py
"""
Centralized prompt templates for HealthBot.

This module:
 - Keeps tone and style consistent
 - Avoids duplicating prompt text across services
 - Makes prompts easy to update and A/B test
"""

import textwrap
from langchain_core.messages import SystemMessage, HumanMessage


# ---------- Helpers ----------
def _shorten(text: str, max_chars: int = 4000) -> str:
    """Truncate very long text to avoid token overflow."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 50] + "\n\n[...truncated...]"


# ---------- Summarization ----------
def build_summary_messages(text_to_summarize: str):
    text = _shorten(text_to_summarize)
    system = SystemMessage(
        content=(
            "You are an empathetic, patient-facing medical educator. "
            "Keep explanations simple, friendly, and non-technical."
        )
    )

    user = HumanMessage(
        content=textwrap.dedent(
            f"""
            Summarize the information below into simple, patient-friendly language.

            Requirements:
            - Short sentences (one idea per sentence)
            - Use simple words; define any medical term briefly
            - Add a 'Key takeaways' list with exactly 3 bullet points
            - Add one sentence reminding the patient to consult their clinician if unsure
            - No medical advice, no dosages

            TEXT:
            {text}
            """
        ).strip()
    )

    return [system, user]


# ---------- Quiz Generation ----------
def build_quiz_messages(summary_text: str, prefer_short_answer: bool = True):
    text = _shorten(summary_text, max_chars=2500)
    mode = "short-answer" if prefer_short_answer else "multiple-choice (4 options)"

    system = SystemMessage(
        content="You create clear, simple patient comprehension questions."
    )

    user = HumanMessage(
        content=textwrap.dedent(
            f"""
            Based only on the summary below, create exactly ONE comprehension question.

            Requirements:
            - Prefer {mode}
            - Keep the question very simple
            - Provide a canonical correct answer (1–2 sentences)
            - Provide one short hint
            - Output ONLY a JSON object with keys: question, options, answer, hint

            SUMMARY:
            {text}
            """
        ).strip()
    )

    return [system, user]


# ---------- Answer Grading ----------
def build_grader_messages(summary_text: str, canonical_answer: str, user_answer: str):
    summary = _shorten(summary_text)
    canonical_answer = canonical_answer.strip()
    user_answer = user_answer.strip()

    system = SystemMessage(
        content="You are a fair grader. Be concise and explain clearly."
    )

    user = HumanMessage(
        content=textwrap.dedent(
            f"""
            Grade the USER_ANSWER against the CANONICAL_ANSWER using only the SUMMARY.

            Return JSON with:
              - score: float from 0.0 to 1.0
              - verdict: "correct", "partial", or "incorrect"
              - explanation: short plain-language explanation
              - citations: 1–2 short snippets from the SUMMARY (10–40 words each)

            SUMMARY:
            {summary}

            CANONICAL_ANSWER:
            {canonical_answer}

            USER_ANSWER:
            {user_answer}
            """
        ).strip()
    )

    return [system, user]
