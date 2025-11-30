# app/routes/healthbot.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core import workflow

router = APIRouter()

class StartTopicRequest(BaseModel):
    topic: str
    session_id: str | None = None

class QuizAnswerRequest(BaseModel):
    session_id: str
    answer: str

@router.post("/start", summary="Start topic flow: search + summarize")
async def start_topic(req: StartTopicRequest):
    try:
        result = await workflow.start_topic_flow(req.topic, req.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result

@router.post("/quiz", summary="Generate a quiz for the active session")
async def get_quiz(session_id: str):
    try:
        return await workflow.request_quiz(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer", summary="Submit answer and get evaluation")
async def submit_answer(body: QuizAnswerRequest):
    try:
        return await workflow.submit_answer(body.session_id, body.answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset", summary="Reset session state")
async def reset(session_id: str):
    try:
        return await workflow.reset_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
