from langgraph.graph import StateGraph
from typing import TypedDict
from app.services.search_service import search_medical_info
from app.services.summary_service import summarize_text
from app.services.quiz_service import generate_quiz_question, evaluate_answer


class BotState(TypedDict):
    topic: str
    search_results: str
    summary: str


async def ask_topic(state: BotState):
    return {"topic": state["topic"]}


async def search_node(state: BotState):
    results = await search_medical_info(state["topic"])
    return {"search_results": results}


async def summarize_node(state: BotState):
    summary = await summarize_text(state["search_results"])
    return {"summary": summary}


# Create the graph
graph = StateGraph(BotState)

graph.add_node("ask_topic", ask_topic)
graph.add_node("search", search_node)
graph.add_node("summarize", summarize_node)

graph.set_entry_point("ask_topic")
graph.add_edge("ask_topic", "search")
graph.add_edge("search", "summarize")

healthbot_graph = graph.compile()


async def run_healthbot_workflow(topic: str):
    """Runs the 3-step mini workflow: Ask -> Search -> Summarize."""
    result = await healthbot_graph.ainvoke({"topic": topic})
    return result["summary"]
