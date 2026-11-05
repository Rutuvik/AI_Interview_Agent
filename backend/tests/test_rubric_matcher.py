
import pytest

from app.services.rubric_matcher import rubric_matcher


@pytest.fixture
def rag_expected_points():
    return [
        "Retrieval of relevant documents",
        "Augmentation of the prompt with retrieved context",
        "Generation of an answer using an LLM",
    ]


def test_complete_rag_answer(rag_expected_points):
    answer = (
        "RAG retrieves relevant documents from a knowledge base "
        "using embeddings. The retrieved context is added to the "
        "prompt, and an LLM generates an answer grounded in that context."
    )

    results = rubric_matcher.match(rag_expected_points, answer)

    assert len(results) == 3
    assert all(result.status != "missing" for result in results)


def test_empty_answer(rag_expected_points):
    results = rubric_matcher.match(rag_expected_points, "")

    assert all(result.status == "missing" for result in results)
    assert all(result.evidence == [] for result in results)


def test_irrelevant_answer(rag_expected_points):
    answer = (
        "Python is a programming language. "
        "It supports object-oriented programming. "
        "Developers use it for many applications."
    )

    results = rubric_matcher.match(rag_expected_points, answer)

    assert all(result.status == "missing" for result in results)


def test_partially_correct_answer(rag_expected_points):
    answer = (
        "RAG retrieves relevant documents from a knowledge base. "
        "It uses this information to answer questions."
    )

    results = rubric_matcher.match(rag_expected_points, answer)

    assert results[0].status in ["covered", "partially_covered"]
    assert results[1].status in ["partially_covered", "missing"]
    assert results[2].status in ["partially_covered", "missing"]


def test_evidence_must_exist_in_candidate_answer(rag_expected_points):
    answer = (
        "RAG retrieves relevant documents from a knowledge base."
    )

    results = rubric_matcher.match(rag_expected_points, answer)

    for result in results:
        for evidence in result.evidence:
            assert evidence in answer


def test_expected_point_count_is_preserved():
    points = [
        "Python programming",
        "Machine learning fundamentals",
        "Deep learning architecture",
        "Natural language processing",
    ]

    answer = "I have knowledge of Python programming."

    results = rubric_matcher.match(points, answer)

    assert len(results) == len(points)
