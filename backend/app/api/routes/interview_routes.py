
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.report_generator import report_generator
import logging

logger = logging.getLogger(__name__)
from app.schemas.question_schema import QuestionRequest
from app.services.interview_service import interview_service


router = APIRouter(
    prefix="/interviews",
    tags=["AI Interview"],
)


class StartInterviewRequest(BaseModel):
    candidate_name: str = Field(default="Candidate", min_length=1)
    job_description: str = Field(min_length=20)
    candidate_profile: str = Field(min_length=10)
    skills: list[str] = Field(min_length=1)
    difficulty: str = "medium"
    num_questions: int = Field(default=5, ge=1, le=20)


class SubmitAnswerRequest(BaseModel):
    candidate_answer: str = Field(min_length=1, max_length=10000)

@router.post("/start")
async def start_interview(request: StartInterviewRequest):
    try:
        question_request = QuestionRequest(
            job_description=request.job_description,
            candidate_profile=request.candidate_profile,
            skills=request.skills,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
        )

        result = await interview_service.start_interview(
            request=question_request,
            candidate_name=request.candidate_name,
        )

        return result

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Unable to start interview. Please try again.",
        )

@router.post("/{session_id}/answer")
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
):
    try:
        result = await interview_service.submit_answer(
            session_id=session_id,
            candidate_answer=request.candidate_answer,
        )
        return result

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Unable to evaluate the answer. Please try again.",
        )

@router.post("/{session_id}/next")
async def get_next_question(session_id: str):
    try:
        return await interview_service.next_question(session_id)

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception as exc:
        logger.exception("Failed to retrieve next interview question")

        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(exc)}"
        ) from exc

@router.get("/{session_id}")
async def get_interview_session(session_id: str):
    try:
        return await interview_service.get_interview(session_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        logger.exception("Failed to retrieve interview session")

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve interview session."
        ) from exc

@router.post("/{session_id}/end")
async def end_interview(session_id: str):
    try:
        return await interview_service.end_interview(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        logger.exception("Failed to end interview")
        raise HTTPException(
            status_code=500,
            detail="Unable to end interview."
        )

@router.get("/{session_id}/report")
async def get_interview_report(session_id: str):
    try:
        state = await interview_service._get_session(session_id)

        report = report_generator.generate_report(state)

        return report

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc

    except Exception:
        logger.exception("Failed to generate interview report")

        raise HTTPException(
            status_code=500,
            detail="Unable to generate interview report."
        )