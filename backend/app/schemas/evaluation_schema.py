
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AnswerEvaluationRequest(BaseModel):
    """Input for evaluating a candidate's answer."""

    question: str = Field(min_length=5)
    category: Literal["technical", "scenario", "coding"]
    expected_answer_points: list[str] = Field(min_length=1)
    evaluation_criteria: list[str] = Field(min_length=1)
    candidate_answer: str = Field(min_length=1)


class ExpectedPointEvaluation(BaseModel):
    """Evaluation of one expected answer concept."""

    expected_point: str

    status: Literal[
        "covered",
        "partially_covered",
        "missing",
        "incorrect",
        "not_assessed",
    ]

    evidence: list[str] = Field(default_factory=list)
    explanation: str


class EvaluationDimension(BaseModel):
    """Score for an individual evaluation dimension."""

    score: int = Field(ge=0, le=5)

    justification: str

    evidence: list[str] = Field(default_factory=list)


class AnswerEvaluation(BaseModel):
    """Structured evaluation of a candidate's answer."""
    category_score: EvaluationDimension
    technical_correctness: EvaluationDimension

    conceptual_understanding: EvaluationDimension

    completeness: EvaluationDimension

    expected_point_evaluations: list[ExpectedPointEvaluation]

    strengths: list[str] = Field(default_factory=list)

    weaknesses: list[str] = Field(default_factory=list)

    missing_concepts: list[str] = Field(default_factory=list)

    incorrect_claims: list[str] = Field(default_factory=list)

    suggested_improvements: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_expected_points(self):

        evaluated_points = self.expected_point_evaluations

        if not evaluated_points:
            raise ValueError(
                "Expected point evaluations cannot be empty."
            )

        return self


class AnswerEvaluationResponse(BaseModel):
    """Complete validated answer evaluation."""

    evaluation: AnswerEvaluation

    overall_score: float = Field(ge=0, le=5)
