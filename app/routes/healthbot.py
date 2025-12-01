# app/routes/healthbot.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import os
import functools
import heapq

router = APIRouter()

# ---------------------------
# Request models
# ---------------------------
class StartTopicRequest(BaseModel):
    topic: str
    session_id: Optional[str] = None

class QuizAnswerRequest(BaseModel):
    session_id: str
    answer: str

# ---------------------------
# Suggestion engine (safe)
# ---------------------------
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "medical_topics.txt")

@functools.lru_cache(maxsize=1)
def _load_medical_topics() -> List[str]:
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip()]
    except Exception:
        # On any read error, return empty list — don't crash import
        return []

def _score_topic(term: str, q: str) -> int:
    term_l = term.lower()
    q_l = q.lower()
    if term_l == q_l:
        return 100
    if term_l.startswith(q_l):
        return 80
    # word prefix match
    for w in term_l.split():
        if w.startswith(q_l):
            return 60
    if q_l in term_l:
        return 40
    return 0

@router.get("/suggest", summary="Suggest medical topics for autocomplete")
async def suggest_topics(q: str = Query(..., min_length=1), limit: int = 10):
    q = q.strip()
    if not q:
        return {"suggestions": []}
    topics = _load_medical_topics()
    if not topics:
        return {"suggestions": []}
    heap = []
    for term in topics:
        s = _score_topic(term, q)
        if s > 0:
            heapq.heappush(heap, (-s, term))
    suggestions = []
    seen = set()
    while heap and len(suggestions) < limit:
        _, t = heapq.heappop(heap)
        if t not in seen:
            suggestions.append(t)
            seen.add(t)
    if len(suggestions) < limit:
        ql = q.lower()
        for term in topics:
            if term in suggestions:
                continue
            if ql in term.lower():
                suggestions.append(term)
            if len(suggestions) >= limit:
                break
    return {"suggestions": suggestions[:limit]}

# ---------------------------
# Primary endpoints (lazy import workflow to avoid cycles)
# ---------------------------
@router.post("/start", summary="Start topic flow: search + summarize")
async def start_topic(req: StartTopicRequest):
    try:
        from app.core import workflow
        result = await workflow.start_topic_flow(req.topic, req.session_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        # return a 500 with the error string
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quiz", summary="Generate a quiz for the active session")
async def get_quiz(session_id: str):
    try:
        from app.core import workflow
        return await workflow.request_quiz(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer", summary="Submit answer and get evaluation")
async def submit_answer(body: QuizAnswerRequest):
    try:
        from app.core import workflow
        return await workflow.submit_answer(body.session_id, body.answer)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset", summary="Reset session state")
async def reset(session_id: str):
    try:
        from app.core import workflow
        return await workflow.reset_session(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
