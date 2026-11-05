
from typing import Any


class ReportGenerator:
    """Generates a consolidated assessment report."""

    def generate_report(self, state: dict[str, Any]) -> dict[str, Any]:

        interview_status = state.get("interview_status", "in_progress")

        evaluations = state.get("evaluations", [])
        answers = state.get("answers", [])
        questions = state.get("questions", [])

        if interview_status not in {"completed", "terminated"}:
            raise ValueError(
                "Interview must be completed or terminated before generating report."
            )

        if not evaluations:
            raise ValueError(
                "No evaluated answers available. Unable to generate an assessment report."
            )
        CATEGORY_WEIGHTS = {
            "technical": 0.35,
            "coding": 0.30,
            "scenario": 0.25,
            "communication": 0.10,
        }

        CATEGORY_NAMES = {
            "technical": "Technical Knowledge",
            "coding": "Coding Proficiency",
            "scenario": "Scenario-Based Problem Solving",
            "communication": "Communication Skills",
        }

        category_scores: dict[str, list[float]] = {
            "technical": [],
            "coding": [],
            "scenario": [],
            "communication": [],
        }

        question_reports = []
        skill_scores: dict[str, list[float]] = {}

        for item in evaluations:

            evaluation = item.get("evaluation", {})
            question_index = item.get("question_index", 0)

            answer = next(
                (
                    a for a in answers
                    if a.get("question_index") == question_index
                ),
                {},
            )

            question = (
                questions[question_index]
                if question_index < len(questions)
                else {}
            )

            skill = question.get("skill", "General")
            category = question.get("category", "technical")

            category_dimension = evaluation.get("category_score", {})
            category_score = category_dimension.get("score", 0)

            point_evaluations = evaluation.get(
                "expected_point_evaluations", []
            )

            is_assessed = bool(point_evaluations) and all(
                point.get("status") != "not_assessed"
                for point in point_evaluations
            )
            score_out_of_100 = round(category_score * 20, 2)

            if is_assessed and category in category_scores:
                category_scores[category].append(score_out_of_100)
                skill_scores.setdefault(skill, []).append(
                    score_out_of_100
                )

            question_reports.append({
                "question_index": question_index,
                "skill": skill,
                "category": category,
                "category_name": CATEGORY_NAMES.get(
                    category, category.title()
                ),
                "question": answer.get(
                    "question", question.get("question", "Unknown question")
                ),
                "candidate_answer": answer.get("answer", ""),
                "category_score": category_score,
                "category_score_out_of_100": (
                    score_out_of_100 if is_assessed else None
                ),
                "assessment_status": (
                    "assessed" if is_assessed else "not_assessed"
                ),
                "technical_correctness": evaluation.get(
                    "technical_correctness", {}
                ),
                "conceptual_understanding": evaluation.get(
                    "conceptual_understanding", {}
                ),
                "completeness": evaluation.get("completeness", {}),
                "expected_point_evaluations": point_evaluations,
                "strengths": evaluation.get("strengths", []),
                "weaknesses": evaluation.get("weaknesses", []),
                "missing_concepts": evaluation.get("missing_concepts", []),
                "incorrect_claims": evaluation.get("incorrect_claims", []),
                "suggested_improvements": evaluation.get(
                    "suggested_improvements", []
                ),
            })

        # Calculate average scores for each assessed category.
        category_averages = {}

        for category, values in category_scores.items():
            category_averages[category] = (
                round(sum(values) / len(values), 2)
                if values
                else None
            )

        # Communication will be evaluated across the entire interview
        # in a separate evaluation step.
        communication_evaluation = state.get(
            "communication_evaluation"
        )

        communication_score = (
            communication_evaluation.get("score")
            if communication_evaluation
            else None
        )

        category_averages["communication"] = communication_score

        # Calculate weighted score using only assessed categories.
        weighted_total = 0.0
        available_weight = 0.0

        for category, weight in CATEGORY_WEIGHTS.items():

            score = category_averages.get(category)

            if score is not None:
                weighted_total += score * weight
                available_weight += weight

        overall_score = (
            round(weighted_total / available_weight, 2)
            if available_weight > 0
            else None
        )

        assessment_complete = (
            interview_status == "completed" and
            available_weight == 1.0
        )

        skill_wise_scores = {
            skill: round(sum(values) / len(values), 2)
            for skill, values in skill_scores.items()
        }

        return {
            "session_id": state["session_id"],
            "candidate_name": state["candidate_name"],
            "interview_status": interview_status,
            "total_questions": len(questions),
            "evaluated_questions": len(evaluations),
            "unanswered_questions": max(
                len(questions) - len(answers), 0
            ),
            "score_status": (
                "complete" if assessment_complete else "provisional"
            ),
            "assessment_note": (
                "Assessment completed successfully."
                if assessment_complete
                else "Interview ended early or some assessment "
                    "components were unavailable. Scores reflect "
                    "the evaluations available at the time of termination."
            ),
            "overall_score": overall_score,
            "maximum_score": 100,
            "assessment_complete": assessment_complete,
            "score_status": (
                "complete" if assessment_complete else "provisional"
            ),
            "category_scores": {
                category: {
                    "name": CATEGORY_NAMES[category],
                    "weight": CATEGORY_WEIGHTS[category],
                    "score": category_averages.get(category),
                }
                for category in CATEGORY_WEIGHTS
            },
            "skill_wise_scores": skill_wise_scores,
            "question_reports": question_reports,
        }

report_generator = ReportGenerator()
