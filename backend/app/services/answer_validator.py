
import re
from dataclasses import dataclass
from enum import Enum


class AnswerStatus(str, Enum):
    VALID = "valid"
    EMPTY = "empty"
    UNKNOWN = "unknown"
    INSTRUCTION_LIKE = "instruction_like"
    TOO_SHORT = "too_short"


@dataclass
class ValidationResult:
    status: AnswerStatus
    reason: str
    normalized_answer: str
    should_evaluate: bool


class AnswerValidator:
    """
    Deterministic validation before invoking the LLM evaluator.
    """

    MIN_ANSWER_LENGTH = 15

    UNKNOWN_PATTERNS = [
        r"\bi don'?t know\b",
        r"\bi do not know\b",
        r"\bno idea\b",
        r"\bnot sure\b",
        r"\bpass\b",
        r"\bcannot answer\b",
        r"\bcan'?t answer\b",
    ]

    INSTRUCTION_PATTERNS = [
        r"^\s*design\s+.+",
        r"^\s*explain\s+.+",
        r"^\s*describe\s+.+",
        r"^\s*write\s+.+",
        r"^\s*implement\s+.+",
        r"^\s*build\s+.+",
        r"^\s*what\s+is\s+.+\?\s*$",
    ]

    def validate(self, answer: str) -> ValidationResult:

        if not answer or not answer.strip():
            return ValidationResult(
                status=AnswerStatus.EMPTY,
                reason="Candidate submitted an empty answer.",
                normalized_answer="",
                should_evaluate=False,
            )

        normalized = self._normalize(answer)

        if self._is_unknown(normalized):
            return ValidationResult(
                status=AnswerStatus.UNKNOWN,
                reason="Candidate explicitly indicated they do not know the answer.",
                normalized_answer=normalized,
                should_evaluate=False,
            )

        if len(normalized) < self.MIN_ANSWER_LENGTH:
            return ValidationResult(
                status=AnswerStatus.TOO_SHORT,
                reason="Answer is too short to evaluate meaningfully.",
                normalized_answer=normalized,
                should_evaluate=False,
            )

        if self._looks_like_instruction(normalized):
            return ValidationResult(
                status=AnswerStatus.INSTRUCTION_LIKE,
                reason="Answer appears to contain an instruction or question rather than a response.",
                normalized_answer=normalized,
                should_evaluate=False,
            )

        return ValidationResult(
            status=AnswerStatus.VALID,
            reason="Answer passed deterministic validation.",
            normalized_answer=normalized,
            should_evaluate=True,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _is_unknown(self, answer: str) -> bool:
        return any(
            re.search(pattern, answer)
            for pattern in self.UNKNOWN_PATTERNS
        )

    def _looks_like_instruction(self, answer: str) -> bool:
        return any(
            re.search(pattern, answer)
            for pattern in self.INSTRUCTION_PATTERNS
        )


answer_validator = AnswerValidator()
