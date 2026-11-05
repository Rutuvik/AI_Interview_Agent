
import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas.question_schema import (
    QuestionRequest,
    InterviewQuestion,
    QuestionGenerationResponse,
)

from app.services.llm_service import llm_service


class QuestionGenerator:
    """Generates validated, non-repetitive interview questions."""

    MAX_RETRIES = 3
    SIMILARITY_THRESHOLD = 0.75

    async def generate_questions(
        self,
        request: QuestionRequest,
    ) -> QuestionGenerationResponse:

        prompt = self._build_prompt(request)

        for attempt in range(self.MAX_RETRIES):

            response = await llm_service.generate_response(
                prompt,
                format="json",
            )

            try:
                data = json.loads(response)

                validated_questions = [
                    InterviewQuestion.model_validate(question)
                    for question in data["questions"]
                ]

                if len(validated_questions) != request.num_questions:
                    raise ValueError(
                        f"Expected {request.num_questions} questions, "
                        f"received {len(validated_questions)}."
                    )

                exact_duplicates = self._find_duplicates(
                    validated_questions
                )

                semantic_duplicates = self._find_semantic_duplicates(
                    validated_questions
                )

                duplicates = list(
                    set(exact_duplicates + semantic_duplicates)
                )

                if not duplicates:
                    return QuestionGenerationResponse(
                        questions=validated_questions,
                        total_questions=len(validated_questions),
                    )

                prompt = self._build_retry_prompt(
                    request=request,
                    questions=validated_questions,
                    duplicates=duplicates,
                )

            except (json.JSONDecodeError, KeyError, ValueError) as exc:

                if attempt == self.MAX_RETRIES - 1:
                    raise ValueError(
                        f"LLM returned invalid question data: {exc}"
                    ) from exc

                prompt = self._build_prompt(request)

        raise ValueError(
            "Unable to generate a unique set of interview questions "
            "after multiple attempts."
        )

    @staticmethod
    def _normalize_question(question: str) -> str:
        """Normalize text for exact duplicate comparison."""

        question = question.lower().strip()
        question = re.sub(r"[^\w\s]", "", question)
        question = re.sub(r"\s+", " ", question)

        return question

    def _find_duplicates(
        self,
        questions: list[InterviewQuestion],
    ) -> list[tuple[int, int]]:
        """Detect exact duplicate questions."""

        duplicates = []

        for i in range(len(questions)):
            for j in range(i + 1, len(questions)):

                first = self._normalize_question(
                    questions[i].question
                )

                second = self._normalize_question(
                    questions[j].question
                )

                if first == second:
                    duplicates.append((i, j))

        return duplicates

    def _find_semantic_duplicates(
        self,
        questions: list[InterviewQuestion],
    ) -> list[tuple[int, int]]:
        """Detect highly similar questions using TF-IDF."""

        texts = [
            self._normalize_question(question.question)
            for question in questions
        ]

        if len(texts) < 2:
            return []

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
        )

        vectors = vectorizer.fit_transform(texts)

        similarity_matrix = cosine_similarity(vectors)

        duplicates = []

        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):

                similarity = similarity_matrix[i][j]

                if similarity >= self.SIMILARITY_THRESHOLD:
                    duplicates.append((i, j))

        return duplicates

    def _build_retry_prompt(
        self,
        request: QuestionRequest,
        questions: list[InterviewQuestion],
        duplicates: list[tuple[int, int]],
    ) -> str:
        """Generate a retry prompt that explicitly avoids duplicates."""

        previous_questions = "\n".join(
            f"- {question.question}"
            for question in questions
        )

        duplicate_pairs = "\n".join(
            f"- Question {i + 1} duplicates Question {j + 1}"
            for i, j in duplicates
        )

        return f"""
{self._build_prompt(request)}

PREVIOUS GENERATION CONTAINED DUPLICATE QUESTIONS.

Previously generated questions:
{previous_questions}

Detected duplicate pairs:
{duplicate_pairs}

STRICT REQUIREMENTS:
1. Generate a completely new set of questions.
2. Do not repeat or paraphrase any previously generated question.
3. Do not assess the same underlying concept more than once.
4. Explore different concepts within the requested skills.
5. Maintain the requested difficulty level.
6. Generate exactly {request.num_questions} questions.
7. Include expected answer points and evaluation criteria.
8. Return only valid JSON.
"""

    def _build_prompt(
        self,
        request: QuestionRequest,
    ) -> str:
        """Build the initial question-generation prompt."""

        skills = ", ".join(request.skills)

        return f"""
You are an expert technical interviewer and assessment designer.

Generate exactly {request.num_questions} distinct interview questions.

JOB DESCRIPTION:
{request.job_description}

CANDIDATE PROFILE:
{request.candidate_profile}

SKILLS TO EVALUATE:
{skills}

DIFFICULTY:
{request.difficulty}

RULES:
1. Every question must be relevant to the job description.
2. Every question must assess the specified skills.
3. Questions must test different concepts and competencies.
4. Avoid repeated concepts, not just repeated wording.
5. Adapt questions to the candidate's experience.
6. Each question must have expected answer points.
7. Each question must have evaluation criteria.
8. Do not provide answers to the questions.
9. Return ONLY valid JSON without markdown or explanations.

REQUIRED JSON FORMAT:
{{
    "questions": [
        {{
            "question": "Question text",
            "skill": "Python",
             "category": "technical",
            "difficulty": "{request.difficulty}",
            "expected_answer_points": [
                "Important concept 1",
                "Important concept 2"
            ],
            "evaluation_criteria": [
                "Criterion 1",
                "Criterion 2"
            ]
        }}
    ]
}}
CATEGORY CLASSIFICATION RULES:
Every question MUST have exactly one category from these options:

1. "technical" — Tests technical knowledge, concepts, definitions,
   architecture, algorithms, frameworks, and theoretical understanding.

2. "scenario" — Presents a real-world situation and evaluates
   analytical thinking, decision-making, trade-offs, and problem-solving.

3. "coding" — Requires writing, completing, debugging, or analyzing
   executable code, algorithms, or programming logic.

IMPORTANT:
- The category must be exactly "technical", "scenario", or "coding".
- Do not use any other category name.
- Assign categories based on what the question actually evaluates.
- Include the category field in every question.
- Return only valid JSON.
"""


question_generator = QuestionGenerator()
