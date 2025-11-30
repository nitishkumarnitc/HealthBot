from tavily import TavilyClient
import os
from dotenv import load_dotenv
load_dotenv()
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

async def search_medical_info(topic: str) -> str:
    result = client.search(query=f"medical explanation for {topic}")
    return result["results"][0]["content"]
