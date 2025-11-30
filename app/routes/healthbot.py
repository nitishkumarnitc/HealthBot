from fastapi import APIRouter
from app.core.workflow import run_healthbot_workflow

router = APIRouter()

@router.post("/chat")
async def chat_with_bot(user_message: str):
    """Basic endpoint to run HealthBot workflow."""
    result = await run_healthbot_workflow(user_message)
    return {"response": result}
