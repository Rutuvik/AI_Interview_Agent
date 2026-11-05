
from fastapi import APIRouter, HTTPException

from app.schemas.question_schema import (
    QuestionRequest,
    QuestionGenerationResponse,
)
from app.services.question_generator import question_generator

router = APIRouter(
    prefix="/questions",
    tags=["Question Generation"],
)


@router.post(
    "/generate",
    response_model=QuestionGenerationResponse,
)
async def generate_questions(request: QuestionRequest):
    """Generate interview questions based on candidate and job details."""

    try:
        result = await question_generator.generate_questions(request)
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="The question generation service is temporarily unavailable.",
        )
