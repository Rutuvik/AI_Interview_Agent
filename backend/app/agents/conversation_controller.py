
import re
from enum import Enum


class ConversationIntent(str, Enum):
    ANSWER = "answer"
    REPEAT = "repeat"
    DONT_KNOW = "dont_know"
    CLARIFY = "clarify"
    SKIP = "skip"
    OFF_TOPIC = "off_topic"
    END_INTERVIEW = "end_interview"


class ConversationController:
    """Deterministic intent classifier for interview conversations."""

    REPEAT_PATTERNS = [
        r"\brepeat\b",
        r"\say that again\b",
        r"\bcome again\b",
        r"\bone more time\b",
        r"\bdidn't hear\b",
        r"\bdid not hear\b",
        r"\brephrase\b",
    ]

    DONT_KNOW_PATTERNS = [
        r"\bi don't know\b",
        r"\bi do not know\b",
        r"\bnot sure\b",
        r"\bno idea\b",
        r"\bcan't answer\b",
        r"\bcannot answer\b",
        r"\bi'm unable to answer\b",
    ]

    CLARIFY_PATTERNS = [
        r"\bwhat do you mean\b",
        r"\bcan you explain\b",
        r"\bexplain the question\b",
        r"\bclarify\b",
        r"\bmeaning of the question\b",
    ]

    SKIP_PATTERNS = [
        r"\bskip\b",
        r"\bpass this question\b",
        r"\bnext question\b",
        r"\bmove to the next\b",
    ]

    END_PATTERNS = [
        r"\bend the interview\b",
        r"\bstop the interview\b",
        r"\bterminate the interview\b",
        r"\bi want to end\b",
        r"\bi'd like to end\b",
    ]

    OFF_TOPIC_PATTERNS = [
        r"\btell me a joke\b",
        r"\bwho are you\b",
        r"\bwhat is your name\b",
        r"\bhow are you\b",
        r"\bwhat can you do\b",
    ]

    @staticmethod
    def _matches(text: str, patterns: list[str]) -> bool:
        return any(re.search(pattern, text) for pattern in patterns)

    def classify(self, text: str) -> ConversationIntent:
        """Classify candidate speech without an additional LLM call."""

        normalized = text.lower().strip()

        if not normalized:
            return ConversationIntent.ANSWER

        # Explicitly ending the interview takes highest priority.
        if self._matches(normalized, self.END_PATTERNS):
            return ConversationIntent.END_INTERVIEW

        # Handle common interview-control phrases.
        if self._matches(normalized, self.REPEAT_PATTERNS):
            return ConversationIntent.REPEAT

        if self._matches(normalized, self.SKIP_PATTERNS):
            return ConversationIntent.SKIP

        if self._matches(normalized, self.CLARIFY_PATTERNS):
            return ConversationIntent.CLARIFY

        if self._matches(normalized, self.DONT_KNOW_PATTERNS):
            return ConversationIntent.DONT_KNOW

        if self._matches(normalized, self.OFF_TOPIC_PATTERNS):
            return ConversationIntent.OFF_TOPIC

        # Default: treat speech as the candidate's answer.
        return ConversationIntent.ANSWER


conversation_controller = ConversationController()
