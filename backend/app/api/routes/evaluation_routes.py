
from fastapi import APIRouter, HTTPException

from app.schemas.evaluation_schema import (
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
)
from app.services.answer_evaluator import answer_evaluator

router = APIRouter(
    prefix="/evaluation",
    tags=["Answer Evaluation"],
)


@router.post(
    "/evaluate",
    response_model=AnswerEvaluationResponse,
)
async def evaluate_answer(request: AnswerEvaluationRequest):
    """Evaluate a candidate's technical interview answer."""

    try:
        result = await answer_evaluator.evaluate_answer(request)
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="The answer evaluation service is temporarily unavailable.",
        )
