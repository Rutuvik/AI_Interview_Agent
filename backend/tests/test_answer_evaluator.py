
import json
import pytest

from unittest.mock import AsyncMock

from app.services.answer_evaluator import AnswerEvaluator
from app.schemas.evaluation_schema import AnswerEvaluationRequest


@pytest.fixture
def evaluator():
    return AnswerEvaluator()


@pytest.fixture
def valid_request():
    return AnswerEvaluationRequest(
        question="What is RAG and how does it work?",
        category="technical",
        expected_answer_points=[
            "Retrieval of relevant documents",
            "Augmentation of the prompt with retrieved context",
            "Generation of an answer using an LLM",
        ],
        evaluation_criteria=[
            "Technical correctness",
            "Conceptual understanding",
            "Completeness",
        ],
        candidate_answer=(
            "RAG retrieves relevant documents from a knowledge base "
            "using embeddings. The retrieved context is added to the "
            "prompt, and an LLM generates an answer grounded in that context."
        ),
    )


@pytest.mark.asyncio
async def test_complete_answer_evaluation(
    evaluator,
    valid_request,
    monkeypatch,
):
    mock_response = {
        "technical_correctness_score": 5,
        "conceptual_understanding_score": 5,
        "feedback": {
            "technical_correctness_justification": "Technically accurate.",
            "conceptual_understanding_justification": "Demonstrates understanding.",
            "strengths": ["Clear explanation"],
            "weaknesses": [],
            "suggested_improvements": [],
        },
    }

    monkeypatch.setattr(
        "app.services.answer_evaluator.llm_service.generate_response",
        AsyncMock(return_value=json.dumps(mock_response)),
    )

    result = await evaluator.evaluate_answer(valid_request)

    assert result.overall_score > 0
    assert result.overall_score <= 5

    assert len(
        result.evaluation.expected_point_evaluations
    ) == 3

    assert all(
        point.status != "missing"
        for point in result.evaluation.expected_point_evaluations
    )


@pytest.mark.asyncio
async def test_unknown_answer_receives_zero_score(
    evaluator,
    valid_request,
):
    valid_request.candidate_answer = "I don't know."

    result = await evaluator.evaluate_answer(valid_request)

    assert result.overall_score == 0

    assert all(
        dimension.score == 0
        for dimension in [
            result.evaluation.technical_correctness,
            result.evaluation.conceptual_understanding,
            result.evaluation.completeness,
        ]
    )


@pytest.mark.asyncio
async def test_irrelevant_answer_receives_low_score(
    evaluator,
    valid_request,
    monkeypatch,
):
    valid_request.candidate_answer = (
        "Python is a programming language. "
        "It supports object-oriented programming."
    )

    mock_response = {
        "technical_correctness_score": 4,
        "conceptual_understanding_score": 4,
            "feedback": {
            "technical_correctness_justification": "Unrelated answer.",
            "conceptual_understanding_justification": "No relevant understanding.",
            "strengths": [],
            "weaknesses": ["Answer is unrelated"],
            "suggested_improvements": ["Address the question directly"],
        },
    }

    monkeypatch.setattr(
        "app.services.answer_evaluator.llm_service.generate_response",
        AsyncMock(return_value=json.dumps(mock_response)),
    )

    result = await evaluator.evaluate_answer(valid_request)

    assert result.overall_score <= 1

    assert all(
        point.status == "missing"
        for point in result.evaluation.expected_point_evaluations
    )


@pytest.mark.asyncio
async def test_missing_concepts_are_deterministic(
    evaluator,
    valid_request,
    monkeypatch,
):
    valid_request.candidate_answer = (
        "RAG retrieves relevant documents from a knowledge base "
        "using embeddings."
    )

    mock_response = {
        "technical_correctness_score": 4,
        "conceptual_understanding_score": 4,
        "feedback": {
            "technical_correctness_justification": "Partial explanation.",
            "conceptual_understanding_justification": "Some understanding.",
            "strengths": ["Explained retrieval"],
            "weaknesses": [],
            "suggested_improvements": ["Explain generation"],
        },
    }

    monkeypatch.setattr(
        "app.services.answer_evaluator.llm_service.generate_response",
        AsyncMock(return_value=json.dumps(mock_response)),
    )

    result = await evaluator.evaluate_answer(valid_request)

    missing = result.evaluation.missing_concepts

    assert isinstance(missing, list)

    assert "Generation of an answer using an LLM" in missing

def test_dimension_score_does_not_collapse_when_llm_score_is_zero():
    from app.services.answer_evaluator import answer_evaluator

    result = answer_evaluator._calculate_dimension_score(
        coverage_score=4.0,
        llm_score=0,
        point_evaluations=[],
        incorrect_claims=[],
    )

    assert result == 0
