
from typing import TypedDict, List, Optional, Literal


class InterviewState(TypedDict):
    """Tracks the complete state of an AI interview session."""

    # Session information
    session_id: str
    candidate_name: str
    candidate_profile: str
    job_description: str
    skills: List[str]
    difficulty: str
    # Interview configuration
    questions: List[dict]
    current_question_index: int
    max_questions: int

    # Current interaction
    current_question: Optional[dict]
    candidate_answer: Optional[str]

    # Evaluation
    current_evaluation: Optional[dict]
    communication_evaluation: Optional[dict]
    # Interview history
    conversation_history: List[dict]
    answers: List[dict]
    evaluations: List[dict]

    # Workflow control
    interview_status: Literal[
        "not_started",
        "in_progress",
        "completed",
        "terminated"
    ]
    next_action: Literal[
        "ask_question",
        "evaluate_answer",
        "generate_followup",
        "next_question",
        "finish"
    ]

    # Error handling
    error_message: Optional[str]
