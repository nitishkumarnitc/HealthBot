# app/core/workflow.py
import uuid
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv
from IPython.display import Image, display
load_dotenv()

# Try to import langgraph; if not available, fallback to a minimal orchestrator
try:
    from langgraph.graph import StateGraph
    LANGGRAPH_AVAILABLE = True
except Exception:
    LANGGRAPH_AVAILABLE = False

from app.services.search_service import search_medical_info
from app.services.summary_service import summarize_text_for_patient
from app.services.quiz_service import generate_quiz_question, evaluate_answer
from app.utils.state import create_session, get_session, update_session, clear_session

# State schema keys used in session dict:
# {
#   "session_id": str,
#   "topic": str,
#   "search_results": str,
#   "summary": str,
#   "quiz": { question, options, answer, hint },
#   "last_eval": { score, verdict, explanation, citations }
# }

# Node implementations
async def node_ask_topic(session_id: str, topic: str):
    await create_session(session_id, {"session_id": session_id, "topic": topic})
    return {"topic": topic}

async def node_search(session_id: str):
    state = await get_session(session_id)
    if not state or "topic" not in state:
        raise RuntimeError("Session or topic missing")
    results = await search_medical_info(state["topic"])
    await update_session(session_id, {"search_results": results})
    return {"search_results": results}

async def node_summarize(session_id: str):
    state = await get_session(session_id)
    if not state or "search_results" not in state:
        raise RuntimeError("search_results missing")
    summary = await summarize_text_for_patient(state["search_results"])
    await update_session(session_id, {"summary": summary})
    return {"summary": summary}

async def node_generate_quiz(session_id: str):
    state = await get_session(session_id)
    if not state or "summary" not in state:
        raise RuntimeError("summary missing")
    quiz = await generate_quiz_question(state["summary"])
    # Remove canonical answer from what will be returned to client,
    # but keep it in session for grading (store under _canonical)
    canonical = quiz.get("answer", "")
    public_quiz = {k: quiz.get(k) for k in ("question","options","hint")}
    await update_session(session_id, {"quiz": {"public": public_quiz, "_canonical": canonical}})
    return {"quiz": public_quiz}

async def node_evaluate(session_id: str, user_answer: str):
    state = await get_session(session_id)
    if not state or "quiz" not in state or "_canonical" not in state["quiz"]:
        raise RuntimeError("quiz canonical answer missing")
    canonical = state["quiz"]["_canonical"]
    eval_result = await evaluate_answer(state["summary"], canonical, user_answer)
    await update_session(session_id, {"last_eval": eval_result})
    return {"evaluation": eval_result}

async def node_clear(session_id: str):
    await clear_session(session_id)
    return {"cleared": True}


# If LangGraph is available, create an explicit StateGraph
if LANGGRAPH_AVAILABLE:
    Graph = StateGraph  # alias
    # A compact graph definition; LangGraph usage may differ slightly by version
    g = Graph(dict)  # using dict as schema
    g.add_node("ask_topic", node_ask_topic)
    g.add_node("search", node_search)
    g.add_node("summarize", node_summarize)
    g.add_node("generate_quiz", node_generate_quiz)
    g.add_node("evaluate", node_evaluate)
    g.add_node("clear", node_clear)

    g.set_entry_point("ask_topic")
    g.add_edge("ask_topic", "search")
    g.add_edge("search", "summarize")
    g.add_edge("summarize", "generate_quiz")
    g.add_edge("generate_quiz", "evaluate")

    # NOTE: removed the invalid edge g.add_edge("any", "clear")
    # If you want a common utility path to clear, wire a real node (e.g. "evaluate" -> "clear")
    # g.add_edge("evaluate", "clear")

    COMPILED_GRAPH = g.compile()
    # display(
    #     Image(
    #         COMPILED_GRAPH.get_graph().draw_mermaid_png()
    #     )
    # )
else:
    COMPILED_GRAPH = None


# High-level helpers for FastAPI routes to call

async def start_topic_flow(topic: str, session_id: str = None) -> Dict[str, Any]:
    """
    Creates a session and runs: ask_topic -> search -> summarize.
    Returns summary (public) and session_id.
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    # ask_topic
    await node_ask_topic(session_id, topic)
    # search
    await node_search(session_id)
    # summarize
    await node_summarize(session_id)
    state = await get_session(session_id)
    public = {
        "session_id": session_id,
        "topic": state.get("topic"),
        "summary": state.get("summary"),
    }
    return public

async def request_quiz(session_id: str) -> Dict[str, Any]:
    """
    Generates a quiz question from stored summary.
    """
    await node_generate_quiz(session_id)
    state = await get_session(session_id)
    return {"session_id": session_id, "quiz": state["quiz"]["public"]}

async def submit_answer(session_id: str, user_answer: str) -> Dict[str, Any]:
    """
    Evaluates the user's answer and returns evaluation + updated grade.
    """
    res = await node_evaluate(session_id, user_answer)
    state = await get_session(session_id)
    return {"session_id": session_id, "evaluation": res["evaluation"], "last_eval": state.get("last_eval")}

async def reset_session(session_id: str):
    await node_clear(session_id)
    return {"session_id": session_id, "status": "cleared"}
