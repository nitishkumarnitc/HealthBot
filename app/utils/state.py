# app/utils/state.py
import os
import json
import asyncio
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Use redis.asyncio from the official redis package
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "900"))  # 15 minutes

_redis: Optional[aioredis.Redis] = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        # Redis.from_url returns a Redis async client
        _redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        # (optional) test connection
        try:
            await _redis.ping()
        except Exception as e:
            # If redis isn't ready, you might want to raise or log and continue
            raise RuntimeError(f"Unable to connect to Redis at {REDIS_URL}: {e}")
    return _redis

def session_key(session_id: str) -> str:
    return f"healthbot:session:{session_id}"

async def create_session(session_id: str, initial_state: Optional[Dict[str, Any]] = None):
    r = await get_redis()
    key = session_key(session_id)
    state = initial_state or {}
    await r.set(key, json.dumps(state), ex=SESSION_TTL_SECONDS)
    return state

async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    r = await get_redis()
    raw = await r.get(session_key(session_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

async def update_session(session_id: str, patch: Dict[str, Any]):
    r = await get_redis()
    state = await get_session(session_id) or {}
    state.update(patch)
    await r.set(session_key(session_id), json.dumps(state), ex=SESSION_TTL_SECONDS)
    return state

async def clear_session(session_id: str):
    r = await get_redis()
    await r.delete(session_key(session_id))
