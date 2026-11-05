
import pytest

from app.services.answer_validator import (
    AnswerValidator,
    AnswerStatus,
)


@pytest.fixture
def validator():
    return AnswerValidator()


@pytest.mark.parametrize(
    "answer, expected_status",
    [
        ("", AnswerStatus.EMPTY),
        ("   ", AnswerStatus.EMPTY),
        ("I don't know", AnswerStatus.UNKNOWN),
        ("No idea", AnswerStatus.UNKNOWN),
        (
            "Design a RAG pipeline in Python. Explain document ingestion.",
            AnswerStatus.INSTRUCTION_LIKE,
        ),
        (
            "RAG uses document chunking, embeddings, "
            "retrieval, and generation to provide grounded answers.",
            AnswerStatus.VALID,
        ),
    ],
)
def test_answer_validation(validator, answer, expected_status):
    result = validator.validate(answer)

    assert result.status == expected_status
