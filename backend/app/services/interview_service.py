
import uuid
import json
import logging
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import InterviewSession
from app.graph.interview_graph import interview_graph
from app.schemas.question_schema import QuestionRequest
from app.services.question_generator import question_generator


class InterviewService:
    """Manages AI interview sessions with persistent SQLite storage."""

    async def _save_session(self, session_id: str, state: dict) -> None:
        """Save or update an interview session in SQLite."""

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(InterviewSession).where(
                    InterviewSession.id == session_id
                )
            )

            session = result.scalar_one_or_none()

            if session is None:
                session = InterviewSession(
                    id=session_id,
                    candidate_name=state["candidate_name"],
                    status=state["interview_status"],
                    state_data=json.dumps(state),
                )
                db.add(session)
            else:
                session.status = state["interview_status"]
                session.state_data = json.dumps(state)

            await db.commit()

    async def _get_session(self, session_id: str) -> dict:
        """Retrieve interview state from SQLite."""

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(InterviewSession).where(
                    InterviewSession.id == session_id
                )
            )

            session = result.scalar_one_or_none()

            if session is None:
                raise ValueError("Interview session not found.")

            return json.loads(session.state_data)

    async def start_interview(
        self,
        request: QuestionRequest,
        candidate_name: str = "Candidate",
    ) -> dict:
        """Generate questions and initialize an interview session."""

        question_response = await question_generator.generate_questions(
            request
        )

        session_id = str(uuid.uuid4())

        initial_state = {
            "session_id": session_id,
            "candidate_name": candidate_name,
            "candidate_profile": request.candidate_profile,
            "job_description": request.job_description,
            "skills": request.skills,
            "difficulty": request.difficulty,
            "questions": [
                question.model_dump()
                for question in question_response.questions
            ],
            "current_question_index": 0,
            "max_questions": request.num_questions,
            "current_question": None,
            "candidate_answer": None,
            "current_evaluation": None,
            "conversation_history": [],
            "answers": [],
            "evaluations": [],
            "interview_status": "not_started",
            "next_action": "ask_question",
            "error_message": None,
        }

        # Execute LangGraph to generate the first question
        result = await interview_graph.ainvoke(initial_state)

        # Persist the initial state
        await self._save_session(session_id, result)

        return {
            "session_id": session_id,
            "candidate_name": candidate_name,
            "status": result["interview_status"],
            "current_question": result["current_question"],
            "total_questions": len(result["questions"]),
        }


    async def submit_answer(
        self,
        session_id: str,
        candidate_answer: str,
    ) -> dict:
        """Submit, evaluate, and finalize a candidate's answer."""

        state = await self._get_session(session_id)

        if state["interview_status"] != "in_progress":
            raise ValueError("This interview is not currently active.")

        if not state.get("current_question"):
            raise ValueError("No active question found for this session.")

        if state["next_action"] != "evaluate_answer":
            raise ValueError("The current question has already been answered.")

        state["candidate_answer"] = candidate_answer

        from app.graph.interview_nodes import (
            evaluate_answer,
            evaluate_communication,
        )

        evaluation_result = await evaluate_answer(state)
        state.update(evaluation_result)

        if state.get("error_message"):
            await self._save_session(session_id, state)
            raise ValueError(state["error_message"])

        is_last_question = (
            state["current_question_index"] + 1 >= state["max_questions"]
            or state["current_question_index"] + 1 >= len(state["questions"])
        )

        if is_last_question:
            state["interview_status"] = "completed"
            state["next_action"] = "finish"
            state["current_question"] = None

            try:
                communication_result = await evaluate_communication(state)
                state.update(communication_result)
            except Exception as exc:
                logger.exception("Communication evaluation failed")
                state["communication_evaluation"]={"score":None,"feedback":f"Communication evaluation unavailable:{str(exc)}",}
        await self._save_session(session_id, state)

        return {
        "session_id": session_id,
        "question": (
            state["current_question"]["question"]
            if state.get("current_question")
            else None
        ),
        "candidate_answer": candidate_answer,
        "evaluation": state.get("current_evaluation"),
        "status": state["interview_status"],
        "next_action": state["next_action"],
        "communication_evaluation": state.get(
            "communication_evaluation"
        ),
    }


    async def next_question(self, session_id: str) -> dict:
        """Advance to the next question in the interview."""

        state = await self._get_session(session_id)

        if state["interview_status"] != "in_progress":
            raise ValueError("This interview is not currently active.")

        if state["next_action"] != "next_question":
            raise ValueError("The current answer must be evaluated first.")

        # These graph nodes are synchronous functions
        from app.graph.interview_nodes import next_question, ask_question

        updated_state = next_question(state)
        state.update(updated_state)

        # Check if the interview has finished
        if state["interview_status"] == "completed":
            await self._save_session(session_id, state)

            return {
                "session_id": session_id,
                "status": "completed",
                "message": "Interview completed successfully.",
            }

        # Generate the next question
        question_state = ask_question(state)
        state.update(question_state)

        # Persist updated state
        await self._save_session(session_id, state)

        return {
            "session_id": session_id,
            "status": state["interview_status"],
            "current_question": state["current_question"],
            "question_number": state["current_question_index"] + 1,
            "total_questions": state["max_questions"],
        }

    async def get_interview(self, session_id: str) -> dict:
        """Retrieve interview progress and state for resuming."""

        state = await self._get_session(session_id)

        return {
            "session_id": state["session_id"],
            "candidate_name": state["candidate_name"],
            "status": state["interview_status"],
            "current_question": state["current_question"],
            "question_number": (
                state["current_question_index"] + 1
                if state["current_question"]
                else 0
            ),
            "total_questions": state["max_questions"],
            "answers": state["answers"],
            "evaluations": state["evaluations"],
            "next_action": state["next_action"],
        }
    async def end_interview(self, session_id: str) -> dict:
        """End an interview early while preserving completed evaluations."""

        state = await self._get_session(session_id)

        if state["interview_status"] == "completed":
            return {
                "session_id": session_id,
                "status": "completed",
                "message": "Interview has already finished.",
            }

        if state["interview_status"] == "terminated":
            return {
                "session_id": session_id,
                "status": "terminated",
                "message": "Interview has already been terminated.",
            }

        state["interview_status"] = "terminated"
        state["next_action"] = "finish"
        state["current_question"] = None
        state["candidate_answer"] = None
        state["current_evaluation"] = None

        from app.graph.interview_nodes import evaluate_communication

        try:
            communication_result = await evaluate_communication(state)
            state.update(communication_result)

        except Exception:
            logger.exception("Communication evaluation failed")

            state["communication_evaluation"] = {
                "score": None,
                "justification": "Communication evaluation unavailable.",
                "evidence": [],
            }

        await self._save_session(session_id, state)

        return {
            "session_id": session_id,
            "status": "terminated",
            "message": "Interview ended. Assessment is ready.",
        }
    async def skip_question(self, session_id: str) -> dict:
        """Record a skipped question and advance the interview."""

        state = await self._get_session(session_id)

        if state["interview_status"] != "in_progress":
            raise ValueError("This interview is not currently active.")

        question = state.get("current_question")

        if not question:
            raise ValueError("No active question to skip.")

        skipped_question = {
            "question": question["question"],
            "question_index": state["current_question_index"],
            "skipped": True,
        }

        state.setdefault("answers", []).append(skipped_question)

        state.setdefault("conversation_history", []).append({
            "role": "candidate",
            "content": "[Question skipped]",
            "question_index": state["current_question_index"],
        })

        from app.graph.interview_nodes import next_question, ask_question

        updated_state = next_question(state)
        state.update(updated_state)

        if state["interview_status"] == "completed":
            await self._save_session(session_id, state)

            return {
                "status": "completed",
                "current_question": None,
            }

        question_state = ask_question(state)
        state.update(question_state)

        await self._save_session(session_id, state)

        return {
            "status": state["interview_status"],
            "current_question": state["current_question"],
            "question_number": state["current_question_index"] + 1,
            "total_questions": state["max_questions"],
        }


interview_service = InterviewService()