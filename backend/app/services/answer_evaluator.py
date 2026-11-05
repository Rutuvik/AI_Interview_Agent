
import json
import logging
from typing import Any

from app.services.rubric_matcher import rubric_matcher
from app.schemas.evaluation_schema import (
    AnswerEvaluationRequest,
    AnswerEvaluation,
    AnswerEvaluationResponse,
    EvaluationDimension,
    ExpectedPointEvaluation,
)
from app.services.llm_service import llm_service
from app.services.answer_validator import answer_validator


logger = logging.getLogger(__name__)


class AnswerEvaluator:
    """Evidence-based hybrid interview evaluator."""

    STATUS_WEIGHTS = {
        "covered": 1.0,
        "partially_covered": 0.5,
        "missing": 0.0,
        "incorrect": 0.0,
        "not_assessed": 0.0,
    }

    CATEGORY_SCORE_KEYS = {
        "technical": "technical_knowledge_score",
        "scenario": "scenario_problem_solving_score",
        "coding": "coding_proficiency_score",
    }

    async def evaluate_answer(
        self,
        request: AnswerEvaluationRequest,
    ) -> AnswerEvaluationResponse:

        # 1. Validate candidate answer.
        validation = answer_validator.validate(
            request.candidate_answer
        )

        if not validation.should_evaluate:
            return self._create_zero_evaluation(
                request,
                validation.reason,
            )

        # 2. Deterministic rubric matching.
        rubric_matches = rubric_matcher.match(
            request.expected_answer_points,
            request.candidate_answer,
        )

        rubric_matches = self._verify_evidence(
            request.candidate_answer,
            rubric_matches,
        )

        # 3. Convert results into schema objects.
        point_evaluations = [
            ExpectedPointEvaluation(
                expected_point=result.expected_point,
                status=result.status,
                evidence=result.evidence,
                explanation=(
                    "Deterministic rubric matching identified "
                    f"{result.status.replace('_', ' ')} coverage."
                ),
            )
            for result in rubric_matches
        ]

        self._validate_rubric_alignment(
            request.expected_answer_points,
            point_evaluations,
        )

        # 4. Calculate deterministic coverage.
        coverage_score = self._calculate_coverage(
            point_evaluations
        )

        # 5. Obtain category-specific LLM evaluation.
        prompt = self._build_feedback_prompt(
            request,
            point_evaluations,
        )

        try:
            response = await llm_service.generate_response(
                prompt,
                format="json",
            )

            data = json.loads(response)
            print("\n========== GEMMA RAW EVALUATION ==========")
            print(json.dumps(data, indent=2))
            print("=======================================\n")

            feedback = data.get("feedback", {})

            if not isinstance(feedback, dict):
                feedback = {}

            # 6. Calculate evaluation dimensions.
            technical_score = self._calculate_dimension_score(
                coverage_score,
                data.get("technical_correctness_score", 0),
                point_evaluations,
                feedback.get("incorrect_claims", []),
            )

            conceptual_score = self._calculate_dimension_score(
                coverage_score,
                data.get("conceptual_understanding_score", 0),
                point_evaluations,
                feedback.get("incorrect_claims", []),
            )

            completeness_score = round(coverage_score)

            # 7. Calculate category-specific score.
            category_key = self.CATEGORY_SCORE_KEYS.get(
                request.category
            )

            if not category_key:
                raise ValueError(
                    f"Unsupported category: {request.category}"
                )

            llm_category_score = data.get(category_key, 0)

            category_score = self._calculate_category_score(
                coverage_score=coverage_score,
                llm_score=llm_category_score,
                point_evaluations=point_evaluations,
                category=request.category,
            )

            # 8. Build feedback from deterministic rubric results.
            covered_points = [
                point.expected_point
                for point in point_evaluations
                if point.status == "covered"
            ]

            improvement_points = [
                point.expected_point
                for point in point_evaluations
                if point.status in (
                    "partially_covered",
                    "missing",
                    "incorrect",
                )
            ]

            missing_points = [
                point.expected_point
                for point in point_evaluations
                if point.status in ("missing", "incorrect")
            ]

            strengths = self._deduplicate(covered_points)
            weaknesses = self._deduplicate(improvement_points)
            missing_concepts = self._deduplicate(missing_points)

            suggested_improvements = [
                f"Strengthen your explanation of: {point}"
                for point in improvement_points
            ]

            verified_evidence = self._verified_evidence(
                point_evaluations
            )

            # 9. Construct evaluation response.
            evaluation = AnswerEvaluation(
                category_score=EvaluationDimension(
                    score=category_score,
                    justification=self._build_category_justification(
                        point_evaluations,
                        category_score,
                    ),
                    evidence=verified_evidence,
                ),
                technical_correctness=EvaluationDimension(
                    score=technical_score,
                    justification=(
                        "Score combines deterministic rubric coverage "
                        "with the LLM's technical correctness assessment."
                    ),
                    evidence=verified_evidence,
                ),
                conceptual_understanding=EvaluationDimension(
                    score=conceptual_score,
                    justification=(
                        "Score combines deterministic rubric coverage "
                        "with the LLM's conceptual understanding assessment."
                    ),
                    evidence=verified_evidence,
                ),
                completeness=EvaluationDimension(
                    score=completeness_score,
                    justification=(
                        "Completeness is calculated from deterministic "
                        "expected-point coverage."
                    ),
                    evidence=verified_evidence,
                ),
                expected_point_evaluations=point_evaluations,
                strengths=strengths,
                weaknesses=weaknesses,
                missing_concepts=missing_concepts,
                incorrect_claims=self._deduplicate(
                    feedback.get("incorrect_claims", [])
                ),
                suggested_improvements=suggested_improvements,
            )

            return AnswerEvaluationResponse(
                evaluation=evaluation,
                overall_score=float(category_score),
            )

        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            logger.exception("Evaluation parsing or validation failed")
            raise ValueError(
                f"Invalid LLM evaluation response: {exc}"
            ) from exc

    def _build_feedback_prompt(
        self,
        request: AnswerEvaluationRequest,
        point_evaluations: list[ExpectedPointEvaluation],
    ) -> str:

        deterministic_results = [
            {
                "expected_point": point.expected_point,
                "status": point.status,
                "evidence": point.evidence,
            }
            for point in point_evaluations
        ]

        category_guidance = {
            "technical": """
Evaluate technical knowledge:
- Technical accuracy
- Conceptual understanding
- Depth and clarity
- Correct terminology
- Explanation of mechanisms and processes

Return technical_knowledge_score from 0 to 5.
""",
            "scenario": """
Evaluate scenario-based problem solving:
- Problem identification
- Analytical reasoning
- Practical solution
- Decision-making
- Trade-offs
- Constraints and edge cases
- Justification

Return scenario_problem_solving_score from 0 to 5.
""",
            "coding": """
Evaluate coding proficiency:
- Algorithmic correctness
- Logical implementation
- Appropriate data structures
- Time complexity
- Space complexity
- Edge-case handling
- Code readability and maintainability
- Testing and debugging awareness

CODING RULES:
- Evaluate actual code when provided.
- If code is absent, evaluate the described approach.
- Do not assume an explained approach is implemented correctly.
- Do not penalize missing code automatically with zero.
- Evaluate complexity only when relevant to the question.
- Do not invent code or test results.
- Consider the question's difficulty and requirements.

Return coding_proficiency_score from 0 to 5.
""",
        }

        category_key = self.CATEGORY_SCORE_KEYS.get(
            request.category,
            "technical_knowledge_score",
        )

        return f"""
You are a strict, fair, evidence-based technical interviewer.

QUESTION CATEGORY:
{request.category}

CATEGORY GUIDANCE:
{category_guidance.get(request.category, "")}

QUESTION:
{request.question}

EXPECTED ANSWER POINTS:
{json.dumps(request.expected_answer_points, indent=2)}

EVALUATION CRITERIA:
{json.dumps(request.evaluation_criteria, indent=2)}

CANDIDATE ANSWER:
{request.candidate_answer}

DETERMINISTIC RUBRIC RESULTS:
{json.dumps(deterministic_results, indent=2)}

DIMENSION-SPECIFIC SCORING:

TECHNICAL CORRECTNESS:
- Evaluate whether statements made by the candidate are factually
  and technically correct.
- Missing preprocessing or evaluation metrics do NOT make
  correctly stated ML concepts technically incorrect.
- If no false technical claims are identified, do not assign
  a score of 0 or 1.
- When the candidate's stated technical approaches are correct,
  normally assign 3 or higher.
- Score 0-2 only when actual technical errors or serious
  misunderstandings are demonstrated.

CONCEPTUAL UNDERSTANDING:
- Evaluate understanding of the concepts actually discussed.
- Do not evaluate knowledge of concepts the candidate never
  mentioned under this dimension.
- Correctly explaining TF-IDF, Logistic Regression, model
  selection, and their trade-offs demonstrates understanding.
- Missing pipeline steps should primarily affect completeness.
- If the concepts explained are correct and meaningful,
  normally assign at least 3.
- Score 0-2 only when the demonstrated understanding itself
  is fundamentally weak or incorrect.

COMPLETENESS:
- Evaluate coverage of expected answer points.
- Missing preprocessing and evaluation metrics legitimately
  reduce completeness.
- Do not transfer completeness penalties to correctness.

CALIBRATION EXAMPLE:
A candidate explains TF-IDF, Logistic Regression, BERT,
and model-selection trade-offs correctly, but omits preprocessing
and precision/recall/F1 metrics.

Expected assessment:
- Technical correctness: 4/5
- Conceptual understanding: 3/5
- Completeness: 2/5

These are calibration guidelines, not mandatory fixed scores.
Evaluate the actual answer and evidence.

IMPORTANT SCORING RULES:

1. Evaluate only what the candidate actually stated.
2. Deterministic rubric results are evidence, not unquestionable truth.
3. A covered expected point must not be described as missing.
4. Do not penalize correct alternative explanations.
5. Missing information is not the same as incorrect information.
6. Do not invent mistakes, misconceptions, or weaknesses.
7. Do not penalize concise answers when correct and sufficient.
8. Do not inflate scores because an answer is lengthy.
9. Feedback must be consistent with rubric classifications.
10. Evidence must be copied exactly from the candidate's answer.
11. Never fabricate evidence.
12. Do not evaluate communication skills in this response.
13. Assess the requested category, not unrelated skills.
14. When all expected points are covered and no genuine technical
    error is demonstrated, the answer must receive a strong score.
15. Do not give a low score solely because additional details
    could have been included.
16. Category-specific score must reflect category guidance.
17. Do not claim a covered expected point is absent.
18. Do not report a missing concept unless supported by rubric results.
19. Return empty feedback lists when no genuine weaknesses exist.

SCORING SCALE:

5 = Excellent: Demonstrates strong understanding of nearly all
required concepts, with accurate explanations and no significant gaps.

4 = Strong: Demonstrates good understanding of the core concepts.
Minor omissions exist, but the answer is technically sound.

3 = Competent: Demonstrates reasonable understanding of the topic.
Some important expected concepts are missing, but the core
approach is correct.

2 = Developing: Demonstrates partial understanding.
Several important concepts are missing or insufficiently explained.

1 = Weak: Demonstrates minimal relevant understanding.
Only isolated concepts are correct or relevant.

0 = No understanding: The answer is irrelevant, empty, or
demonstrates no meaningful understanding of the question.

SCORING CALIBRATION:

1. Award credit for technically correct concepts even when
   phrased differently from expected answer points.
2. A correct implementation approach deserves credit even when
   optional alternatives or advanced techniques are omitted.
3. Missing expected points should reduce completeness, but
   must not automatically erase demonstrated technical knowledge.
4. Distinguish technical correctness from completeness.
5. A candidate who correctly explains the core solution should
   generally receive at least 3/5 for technical knowledge.
6. Reserve scores of 0 to 2 for answers demonstrating substantial
   misunderstanding, irrelevant content, or very limited knowledge.
7. Score 4 to 5 when the core approach is correct and the candidate
   demonstrates meaningful technical reasoning.
8. Never assign a score based solely on rubric coverage.
9. Never assign a score based solely on answer length.
10. Evaluate each scoring dimension independently.


OUTPUT REQUIREMENTS:

Return valid JSON only.
All scores must be integers from 0 to 5.
Justifications must be evidence-based.
Strengths must reflect demonstrated knowledge.
Weaknesses must reflect actual gaps.
Incorrect claims must be explicitly incorrect.
Improvements must be actionable.
Do not duplicate weaknesses.
Return empty lists when no genuine weaknesses exist.

RETURN JSON ONLY:

{{
    "technical_knowledge_score": 0,
    "scenario_problem_solving_score": 0,
    "coding_proficiency_score": 0,
    "technical_correctness_score": 0,
    "conceptual_understanding_score": 0,
    "completeness_score": 0,
    "feedback": {{
        "technical_correctness_justification": "",
        "conceptual_understanding_justification": "",
        "completeness_justification": "",
        "{category_key}_justification": "",
        "strengths": [],
        "weaknesses": [],
        "incorrect_claims": [],
        "suggested_improvements": []
    }}
}}
"""

    def _calculate_coverage(
        self,
        points: list[ExpectedPointEvaluation],
    ) -> float:
        """Calculate deterministic expected-point coverage on 0-5."""

        assessed_points = [
            point
            for point in points
            if point.status != "not_assessed"
        ]

        if not assessed_points:
            return 0.0

        total_weight = sum(
            self.STATUS_WEIGHTS[point.status]
            for point in assessed_points
        )

        return round(
            (total_weight / len(assessed_points)) * 5,
            2,
        )

    def _calculate_category_score(
        self,
        coverage_score: float,
        llm_score: int,
        point_evaluations: list[ExpectedPointEvaluation],
        category: str,
    ) -> int:
        """Combine deterministic coverage and category-specific LLM assessment."""

        llm_score = self._normalize_score(llm_score)
        coverage_score = max(0.0, min(5.0, coverage_score))

        calibrated = (
            coverage_score * 0.4
            + llm_score * 0.6
        )

        assessed_points = [
            point
            for point in point_evaluations
            if point.status != "not_assessed"
        ]

        all_covered = (
            bool(assessed_points)
            and all(
                point.status == "covered"
                for point in assessed_points
            )
        )

        has_incorrect = any(
            point.status == "incorrect"
            for point in assessed_points
        )

        if all_covered and not has_incorrect:
            calibrated = max(calibrated, 4.0)

        return max(0, min(5, round(calibrated)))


    def _calculate_dimension_score(
        self,
        coverage_score: float,
        llm_score: int,
        point_evaluations: list[ExpectedPointEvaluation],
        incorrect_claims: list[str],
    ) -> int:
        """
        Score technical correctness or conceptual understanding
        independently from answer completeness.
        """

        llm_score = self._normalize_score(llm_score)

        has_incorrect_rubric_point = any(
            point.status == "incorrect"
            for point in point_evaluations
        )

        has_incorrect_claim = bool(
            self._deduplicate(incorrect_claims)
        )

        # Incorrect technical claims should meaningfully
        # reduce the dimension score.
        if has_incorrect_rubric_point or has_incorrect_claim:
            return min(llm_score, 2)

        # Do not penalize correctness or understanding simply
        # because the candidate omitted expected points.

        return llm_score

    @staticmethod
    def _normalize_score(score: Any) -> int:
        """Safely normalize an LLM score to an integer in 0-5."""

        try:
            normalized = int(float(score))
            return max(0, min(5, normalized))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _deduplicate(items: list[str]) -> list[str]:
        """Remove empty and duplicate strings while preserving order."""

        unique_items = []
        seen = set()

        for item in items:
            if not isinstance(item, str):
                continue

            cleaned = item.strip()

            if not cleaned:
                continue

            key = cleaned.casefold()

            if key not in seen:
                seen.add(key)
                unique_items.append(cleaned)

        return unique_items

    @staticmethod
    def _build_category_justification(
        points: list[ExpectedPointEvaluation],
        score: int,
    ) -> str:
        """Build a rubric-aligned category justification."""

        total = len(points)

        covered = sum(
            point.status == "covered"
            for point in points
        )

        partial = sum(
            point.status == "partially_covered"
            for point in points
        )

        missing = sum(
            point.status == "missing"
            for point in points
        )

        incorrect = sum(
            point.status == "incorrect"
            for point in points
        )

        not_assessed = sum(
            point.status == "not_assessed"
            for point in points
        )

        return (
            f"Category score: {score}/5. "
            f"Rubric results: {covered}/{total} covered, "
            f"{partial} partially covered, {missing} missing, "
            f"{incorrect} incorrect, and {not_assessed} not assessed. "
            "The score combines rubric coverage with category-specific "
            "quality assessment."
        )

    @staticmethod
    def _validate_rubric_alignment(
        expected_points: list[str],
        evaluated_points: list[ExpectedPointEvaluation],
    ) -> None:
        """Ensure evaluated points match the original rubric."""

        expected = {
            point.strip().casefold()
            for point in expected_points
        }

        evaluated = {
            point.expected_point.strip().casefold()
            for point in evaluated_points
        }

        if expected != evaluated:
            raise ValueError(
                "Evaluation does not match all expected answer points."
            )

    def _verify_evidence(
        self,
        answer: str,
        points: list[Any],
    ) -> list[Any]:
        """Remove evidence that does not occur verbatim in the answer."""

        answer_lower = answer.casefold()
        verified = []

        for point in points:
            valid_evidence = self._deduplicate(
                [
                    evidence
                    for evidence in point.evidence
                    if isinstance(evidence, str)
                    and evidence.casefold() in answer_lower
                ]
            )

            if point.status == "covered" and not valid_evidence:
                point.status = "partially_covered"

            point.evidence = valid_evidence
            verified.append(point)

        return verified

    @staticmethod
    def _verified_evidence(
        points: list[ExpectedPointEvaluation],
    ) -> list[str]:
        """Return unique verified quotations only."""

        evidence = [
            quotation
            for point in points
            for quotation in point.evidence
        ]

        return AnswerEvaluator._deduplicate(evidence)

    @staticmethod
    def _verify_claims(answer: str) -> list[str]:
        """Claims are not independently fact-checked yet."""

        return []

    def _create_zero_evaluation(
        self,
        request: AnswerEvaluationRequest,
        reason: str,
    ) -> AnswerEvaluationResponse:
        """Return not_assessed results for an unevaluable answer."""

        not_assessed_points = [
            ExpectedPointEvaluation(
                expected_point=point,
                status="not_assessed",
                evidence=[],
                explanation=reason,
            )
            for point in request.expected_answer_points
        ]

        not_assessed_dimension = EvaluationDimension(
            score=0,
            justification=(
                "Not assessed because the answer was not evaluable."
            ),
            evidence=[],
        )

        evaluation = AnswerEvaluation(
            category_score=not_assessed_dimension,
            technical_correctness=not_assessed_dimension,
            conceptual_understanding=not_assessed_dimension,
            completeness=not_assessed_dimension,
            expected_point_evaluations=not_assessed_points,
            strengths=[],
            weaknesses=[],
            missing_concepts=[],
            incorrect_claims=[],
            suggested_improvements=[],
        )

        return AnswerEvaluationResponse(
            evaluation=evaluation,
            overall_score=0,
        )


answer_evaluator = AnswerEvaluator()
