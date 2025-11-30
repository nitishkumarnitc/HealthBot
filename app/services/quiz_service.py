async def generate_quiz_question(summary: str) -> str:
    return f"What is one key point from this topic: {summary[:50]}?"

async def evaluate_answer(summary: str, answer: str) -> str:
    if answer.lower() in summary.lower():
        return "Correct!"
    return "Not quite — review the summary again."
