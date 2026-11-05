
import logging
import json
from typing import Literal

from app.graph.interview_state import InterviewState
from app.schemas.evaluation_schema import AnswerEvaluationRequest
from app.services.answer_evaluator import answer_evaluator
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


def ask_question(state: InterviewState) -> dict:
    """Select and prepare the current interview question."""

    questions = state["questions"]
    current_index = state["current_question_index"]

    if current_index >= len(questions):
        return {
            "interview_status": "completed",
            "next_action": "finish",
            "current_question": None,
            "error_message": None,
        }

    question = questions[current_index]

    history = state.get("conversation_history", [])
    updated_history = history + [
        {
            "role": "interviewer",
            "content": question["question"],
            "question_index": current_index,
        }
    ]

    return {
        "current_question": question,
        "candidate_answer": None,
        "current_evaluation": None,
        "conversation_history": updated_history,
        "next_action": "evaluate_answer",
        "interview_status": "in_progress",
        "error_message": None,
    }


async def evaluate_answer(state: InterviewState) -> dict:
    """Evaluate the candidate's answer and update interview state."""

    question = state.get("current_question")
    candidate_answer = state.get("candidate_answer")

    if not question:
        return {
            "error_message": "No active interview question found.",
            "next_action": "finish",
            "interview_status": "terminated",
        }

    if not candidate_answer or not candidate_answer.strip():
        return {
            "error_message": "Candidate answer cannot be empty.",
            "next_action": "finish",
            "interview_status": "terminated",
        }

    try:
        evaluation_request = AnswerEvaluationRequest(
            question=question["question"],
            category=question["category"],
            expected_answer_points=question["expected_answer_points"],
            evaluation_criteria=question["evaluation_criteria"],
            candidate_answer=candidate_answer,
        )

        result = await answer_evaluator.evaluate_answer(evaluation_request)
        evaluation_data = result.model_dump()

        question_index = state["current_question_index"]

        updated_answers = state.get("answers", []) + [
            {
                "question": question["question"],
                "answer": candidate_answer,
                "question_index": question_index,
            }
        ]

        updated_evaluations = state.get("evaluations", []) + [
            {
                "question_index": question_index,
                **evaluation_data,
            }
        ]

        updated_history = state.get("conversation_history", []) + [
            {
                "role": "candidate",
                "content": candidate_answer,
                "question_index": question_index,
            },
            {
                "role": "evaluation",
                "content": evaluation_data,
                "question_index": question_index,
            },
        ]

        return {
            "current_evaluation": evaluation_data,
            "answers": updated_answers,
            "evaluations": updated_evaluations,
            "conversation_history": updated_history,
            "next_action": "next_question",
            "error_message": None,
        }

    except Exception as exc:
        logger.exception("Answer evaluation failed")

        return {
            "error_message": f"Answer evaluation failed: {str(exc)}",
            "next_action": "finish",
            "interview_status": "terminated",
        }


def route_after_evaluation(
    state: InterviewState,
) -> Literal["generate_followup", "next_question", "finish"]:
    """Determine the next action after answer evaluation."""

    if state.get("error_message"):
        return "finish"

    if state.get("interview_status") == "terminated":
        return "finish"

    current_index = state["current_question_index"]
    max_questions = state["max_questions"]
    questions = state["questions"]

    # Final question has already been evaluated
    if (
        current_index + 1 >= max_questions
        or current_index + 1 >= len(questions)
    ):
        return "finish"

    return "next_question"


def next_question(state: InterviewState) -> dict:
    """Advance the interview to the next question."""

    next_index = state["current_question_index"] + 1

    if (
        next_index >= len(state["questions"])
        or next_index >= state["max_questions"]
    ):
        return {
            "current_question_index": next_index,
            "current_question": None,
            "candidate_answer": None,
            "current_evaluation": None,
            "interview_status": "completed",
            "next_action": "finish",
            "error_message": None,
        }

    return {
        "current_question_index": next_index,
        "current_question": None,
        "candidate_answer": None,
        "current_evaluation": None,
        "next_action": "ask_question",
        "interview_status": "in_progress",
        "error_message": None,
    }


async def evaluate_communication(state: InterviewState) -> dict:
    """Evaluate communication across the entire interview."""

    history = state.get("conversation_history", [])

    candidate_responses = [
        item["content"]
        for item in history
        if item.get("role") == "candidate"
        and item.get("content", "").strip()
    ]

    if not candidate_responses:
        return {
            "communication_evaluation": {
                "score": None,
                "justification": "No candidate responses available.",
                "evidence": [],
            }
        }

    transcript = "\n".join(candidate_responses)

    prompt = f"""
You are an expert interview communication evaluator.

Evaluate the candidate's communication across the ENTIRE interview.

Assess:
1. Clarity and structure
2. Ability to explain technical concepts
3. Conciseness and relevance
4. Professional language and coherence

Do NOT evaluate technical correctness here.
Do NOT penalize accent or infer personality.
Use only the provided transcript as evidence.

Score from 0 to 5:
0 = Not assessable
1 = Very poor
2 = Below expectations
3 = Meets expectations
4 = Strong
5 = Excellent

Return ONLY valid JSON:
{{
    "score": 0,
    "justification": "Detailed explanation of the score",
    "evidence": ["Exact excerpts from the candidate's responses"]
}}

Candidate transcript:
{transcript}
"""

    try:
        response = await llm_service.generate_response(
            prompt,
            format="json",
        )

        data = json.loads(response)

        score = max(0, min(5, int(data.get("score", 0))))

        return {
            "communication_evaluation": {
                "score": score * 20,
                "justification": data.get(
                    "justification",
                    "Communication evaluated across the interview.",
                ),
                "evidence": data.get("evidence", []),
            }
        }

    except Exception:
        logger.exception("Communication evaluation failed")

        return {
            "communication_evaluation": {
                "score": None,
                "justification": "Communication evaluation failed.",
                "evidence": [],
            }
        }
