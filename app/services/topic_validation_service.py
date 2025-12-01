from langchain_core.messages import SystemMessage, HumanMessage
from app.services.summary_service import llm  # same model you use
import json


async def validate_topic(raw_topic: str) -> dict:
    """
    Validates if the user topic is a real, medically meaningful topic.
    Returns JSON: {valid: bool, cleaned_topic: str, reason: str}
    """
    system = SystemMessage(
        content="You are a medical topic validator. Decide if the user input refers to a real health-related topic."
    )

    user = HumanMessage(
        content=f"""
        USER INPUT: "{raw_topic}"

        Return ONLY JSON with:
        - valid: true/false
        - cleaned_topic: string (only if valid)
        - reason: string

        Rules:
        - valid ONLY if topic refers to a health condition, disease, symptom, treatment, medication, or human biology.
        - Examples of INVALID: gibberish, random characters, technology terms, names, brands, places, or unrelated text.
        """
    )

    res = await llm.agenerate(messages=[[system, user]])
    text = res.generations[0][0].text  # safe extraction
    try:
        return json.loads(text)
    except:
        return {"valid": False, "cleaned_topic": "", "reason": "Validator failed"}
