
from fastapi import FastAPI
from app.services.llm_service import llm_service
from app.api.routes.question_routes import router as question_router
from app.api.routes.evaluation_routes import router as evaluation_router
from app.api.routes.interview_routes import router as interview_router
from app.db.database import init_db
from app.db import models
from app.api.routes.livekit_routes import router as livekit_router
from fastapi.middleware.cors import CORSMiddleware
# Initialize the database

app = FastAPI(
    title="AI Interview Platform",
    description="AI-powered real-time interview and assessment system",
    version="1.0.0",
)

app.include_router(interview_router, prefix="/api/v1")

app.include_router(question_router, prefix="/api/v1")
app.include_router(evaluation_router, prefix="/api/v1")
app.include_router(livekit_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/")
async def root():
    return {
        "message": "AI Interview Platform is running!",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-interview-platform",
    }
@app.get("/test-llm")
async def test_llm():
    response = await llm_service.generate_response(
        "You are an AI interviewer. "
        "Ask me one Python interview question for a fresher."
    )

    return {
        "question": response,
        "model": "qwen2.5:3b",
        "status": "success",
    }