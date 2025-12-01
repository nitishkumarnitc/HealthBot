# app/api/suggest.py
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List
import os
import functools
import heapq

router = APIRouter(prefix="/healthbot")

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "medical_topics.txt")

# Simple result model
class SuggestResponse(BaseModel):
    suggestions: List[str]

@functools.lru_cache(maxsize=1)
def _load_topics() -> List[str]:
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        topics = [line.strip() for line in fh if line.strip()]
    return topics

def _prefix_score(term: str, q: str) -> int:
    """Higher score for better prefix match (simple)."""
    t = term.lower()
    q = q.lower()
    if t == q:
        return 100
    if t.startswith(q):
        return 80
    if q in t:
        return 40
    # partial word match
    twords = t.split()
    for w in twords:
        if w.startswith(q):
            return 60
    return 0

@router.get("/suggest", response_model=SuggestResponse)
async def suggest(q: str = Query(..., min_length=1), limit: int = 10):
    """
    Suggest medical topics for query `q`.
    Uses a simple scored prefix/substring matching for speed and determinism.
    Returns top `limit` suggestions sorted by score.
    """
    q = q.strip()
    if not q:
        return {"suggestions": []}

    topics = _load_topics()
    if not topics:
        return {"suggestions": []}

    # small heap to keep top results
    heap = []
    for term in topics:
        score = _prefix_score(term, q)
        if score > 0:
            # use negative for max-heap via heapq
            heapq.heappush(heap, (-score, term))
    # if no scored hits, do a fuzzy fallback: include any term whose levenshtein distance small
    suggestions = []
    seen = set()
    while heap and len(suggestions) < limit:
        _, term = heapq.heappop(heap)
        if term not in seen:
            suggestions.append(term)
            seen.add(term)

    # fallback: substring matches even with score 0 (helps for long lists)
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
