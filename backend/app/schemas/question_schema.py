
from typing import Literal

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Input required to generate interview questions."""

    job_description: str = Field(
        min_length=20,
        description="Description of the job role",
    )

    candidate_profile: str = Field(
        min_length=10,
        description="Candidate resume or professional profile",
    )

    skills: list[str] = Field(
        min_length=1,
        description="Skills to evaluate during the interview",
    )

    difficulty: Literal["easy", "medium", "hard"] = "medium"

    num_questions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of questions to generate",
    )


class InterviewQuestion(BaseModel):
    """Structure of a single generated interview question."""

    question: str

    skill: str
    category: Literal["technical", "scenario", "coding"]
    difficulty: Literal["easy", "medium", "hard"]

    expected_answer_points: list[str] = Field(
        min_length=1,
    )

    evaluation_criteria: list[str] = Field(
        min_length=1,
    )


class QuestionGenerationResponse(BaseModel):
    """Validated response containing generated questions."""

    questions: list[InterviewQuestion]

    total_questions: int
