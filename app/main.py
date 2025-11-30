from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes.healthbot import router as healthbot_router
load_dotenv()

app = FastAPI(title="HealthBot API", version="0.1")

app.include_router(healthbot_router, prefix="/healthbot")

@app.get("/")
def root():
    return {"message": "HealthBot API is running!"}
