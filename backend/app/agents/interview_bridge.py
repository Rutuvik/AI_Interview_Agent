
import logging

from app.services.interview_service import interview_service
from app.agents.conversation_controller import (
    conversation_controller,
    ConversationIntent,
)

logger = logging.getLogger("interview-bridge")


class InterviewBridge:

    def __init__(self, session_id: str):
        self.session_id = session_id
    async def get_interview_context(self) -> dict:
        """Retrieve resume and job description context for the AI interviewer."""

        state = await interview_service._get_session(self.session_id)

        return {
            "candidate_name": state["candidate_name"],
            "candidate_profile": state["candidate_profile"],
            "job_description": state["job_description"],
            "skills": state["skills"],
            "difficulty": state["difficulty"],
            "max_questions": state["max_questions"],
        }
    async def get_interview_status(self) -> dict:
        return await interview_service.get_interview(self.session_id)

    async def get_current_question(self) -> dict:
        interview = await self.get_interview_status()

        return {
            "candidate_name": interview["candidate_name"],
            "status": interview["status"],
            "current_question": interview["current_question"],
            "question_number": interview["question_number"],
            "total_questions": interview["total_questions"],
        }

    def classify_candidate_message(self, message: str) -> ConversationIntent:
        return conversation_controller.classify(message)

    async def submit_candidate_answer(self, answer: str) -> dict:
        result = await interview_service.submit_answer(
            session_id=self.session_id,
            candidate_answer=answer,
        )

        logger.info("Answer evaluated for session %s", self.session_id)

        return result

    async def get_next_question(self) -> dict:
        result = await interview_service.next_question(
            session_id=self.session_id
        )

        logger.info("Interview advanced for session %s", self.session_id)

        return result


    async def skip_current_question(self) -> dict:
        result = await interview_service.skip_question(
            session_id=self.session_id
        )

        logger.info(
            "Question skipped and interview advanced for session %s",
            self.session_id,
        )

        return result
