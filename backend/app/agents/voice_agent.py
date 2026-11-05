import logging
import json
import ollama

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession
from livekit.plugins import silero, openai

from app.agents.local_stt import LocalWhisperSTT
from app.agents.local_tts import LocalKokoroTTS
from app.agents.interview_bridge import InterviewBridge
from app.agents.conversation_controller import ConversationIntent

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")


class InterviewAgent(Agent):

    def __init__(self, bridge, interview_context):
        self.bridge = bridge
        self.interview_context = interview_context

        self.phase = "introduction"
        self.awaiting_choice = False
        self.interview_ended = False

        self.max_followups_per_question = 2
        self.followup_count = 0
        self.pending_answer = ""
        self.active_followup_question = ""

        self.ollama_client = ollama.AsyncClient(
            host="http://localhost:11434"
        )

        system_prompt = f"""
You are a professional, intelligent, warm, and natural AI technical interviewer.

CANDIDATE PROFILE / RESUME:
{interview_context.get("candidate_profile", "")}

JOB DESCRIPTION:
{interview_context.get("job_description", "")}

CANDIDATE SKILLS:
{", ".join(interview_context.get("skills", []))}

INTERVIEW CONFIGURATION:
Difficulty: {interview_context.get("difficulty", "medium")}
Maximum questions: {interview_context.get("max_questions", 10)}

GUIDELINES:
1. Conduct a personalized technical interview.
2. Ask one question at a time.
3. Focus on skills, projects, experience, and the job description.
4. Adapt to candidate responses.
5. Never invent candidate experience.
6. Never reveal expected answers, hints, or solutions.
7. Keep spoken responses concise and natural.
8. Do not behave as a general-purpose assistant.
"""
        super().__init__(instructions=system_prompt)

    async def on_enter(self):
        try:
            interview = await self.bridge.get_current_question()
            candidate_name = interview.get("candidate_name") or "Candidate"

            await self.session.generate_reply(
                instructions=(
                    f"Greet {candidate_name} warmly and professionally. "
                    "Introduce yourself as their AI technical interviewer. "
                    "Briefly explain the interview format, then ask them "
                    "to introduce themselves and describe their background. "
                    "Do not ask a technical question yet."
                )
            )
        except Exception:
            logger.exception("Failed to start interview conversation")
            await self.session.generate_reply(
                instructions=(
                    "Greet the candidate professionally and ask "
                "them to introduce themselves."
            )
        )

    async def _get_active_question_text(self) -> str:
        interview = await self.bridge.get_current_question()
        question = interview.get("current_question")
        if question:
            return question.get("question", "")
        return ""

    async def _ask_current_question(self, acknowledge: str = ""):
        interview = await self.bridge.get_current_question()
        question = interview.get("current_question")

        if not question:
            await self._finish_interview()
            return

        instructions = (
            "Ask this interview question exactly as written: "
            f"{question['question']}"
        )
        if acknowledge:
            instructions = f"{acknowledge} {instructions}"

        await self.session.generate_reply(instructions=instructions)

    async def _ask_followup_question(self, question: str):
        self.active_followup_question = question
        self.phase = "followup"

        logger.info(
            "Asking follow-up %s/%s",
            self.followup_count,
            self.max_followups_per_question,
        )

        await self.session.generate_reply(
            instructions=(
                "Ask the following follow-up question exactly as written. "
                "Do not add hints, explanations, or another question. "
                f"Follow-up question: {question}"
            )
        )

    async def _decide_followup(self, question: str, answer: str) -> dict:
        prompt = f"""
You are an experienced technical interviewer.

MAIN INTERVIEW QUESTION:
{question}

CANDIDATE'S COMPLETE ANSWER SO FAR:
{answer}

CANDIDATE RESUME:
{self.interview_context.get("candidate_profile", "")}

JOB DESCRIPTION:
{self.interview_context.get("job_description", "")}

Decide whether a meaningful technical follow-up question is necessary.

Ask a follow-up when the answer is vague/incomplete, a technical claim
needs verification, or reasoning/implementation/trade-offs need clarification.

Do not ask one when the answer is sufficient, irrelevant, or a follow-up
would be repetitive.

Return ONLY valid JSON:
{{"action": "followup", "question": "One specific question"}}
or
{{"action": "continue", "question": ""}}

Never provide hints, expected answers, or solutions.
Do not generate a new main interview question.
"""
        response = await self.ollama_client.chat(
            model="gemma3:4b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a technical interview evaluator. "
                        "Return only valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0.2},
        )

        result = json.loads(response["message"]["content"])
        action = result.get("action")
        followup_question = result.get("question", "").strip()

        if action not in {"followup", "continue"}:
            raise ValueError(f"Invalid follow-up action: {action}")

        if action == "followup" and not followup_question:
            raise ValueError("Empty follow-up question")

        return {"action": action, "question": followup_question}

    async def _process_candidate_answer(self, message: str):
        main_question = await self._get_active_question_text()

        if not main_question:
            logger.warning("No active backend question")
            await self._finish_interview()
            return

        if self.phase == "technical":
            self.pending_answer = (
                f"Main question: {main_question}\n"
                f"Candidate answer: {message}"
            )
            self.followup_count = 0

        elif self.phase == "followup":
            self.pending_answer += (
                f"\n\nFollow-up question: {self.active_followup_question}\n"
                f"Candidate response: {message}"
            )

        if self.followup_count < self.max_followups_per_question:
            try:
                decision = await self._decide_followup(
                    question=main_question,
                    answer=self.pending_answer,
                )

                if (
                    decision["action"] == "followup"
                    and self.followup_count < self.max_followups_per_question
                ):
                    self.followup_count += 1
                    await self._ask_followup_question(
                        decision["question"]
                    )
                    return

            except Exception:
                logger.exception(
                    "Follow-up decision failed; submitting accumulated answer"
                )

        await self._submit_answer_and_advance()

    async def _submit_answer_and_advance(self):
        if not self.pending_answer.strip():
            logger.warning("Refusing to submit an empty answer")
            await self._advance_interview()
            return

        answer_to_submit = self.pending_answer

        try:
            logger.info(
                "Submitting combined answer after %d follow-up(s)",
                self.followup_count,
            )
            await self.bridge.submit_candidate_answer(
                answer=answer_to_submit
            )
        except Exception:
            logger.exception("Failed to submit candidate answer")
            await self.session.generate_reply(
                instructions=(
                    "Apologize briefly for a technical issue. "
                    "Tell the candidate that the response could not be "
                    "saved and that the interview cannot proceed right now."
                )
            )
            return

        self.pending_answer = ""
        self.active_followup_question = ""
        self.followup_count = 0
        self.awaiting_choice = False
        self.phase = "technical"

        await self._advance_interview()

    async def _advance_interview(self):
        result = await self.bridge.get_next_question()
        question_data = result.get("current_question")

        if not question_data:
            await self._finish_interview()
            return

        await self.session.generate_reply(
            instructions=(
                "Acknowledge the candidate's previous response briefly "
                "and neutrally. Then ask the next interview question "
                "exactly as written: "
                f"{question_data['question']}"
            )
        )

    async def _skip_current_question(self):
        try:
            self.pending_answer = ""
            self.active_followup_question = ""
            self.followup_count = 0
            self.awaiting_choice = False
            self.phase = "technical"

            result = await self.bridge.skip_current_question()
            question_data = result.get("current_question")

            if not question_data:
                await self._finish_interview()
                return

            await self.session.generate_reply(
                instructions=(
                    "Acknowledge that the candidate chose to skip. "
                    "Then ask the next interview question exactly as written: "
                    f"{question_data['question']}"
                )
            )
        except Exception:
            logger.exception("Failed to skip interview question")
            await self.session.generate_reply(
                instructions=(
                    "Apologize briefly and explain that you could not "
                    "move to the next question."
                )
            )

    async def _repeat_active_question(self):
        if self.phase == "followup":
            await self.session.generate_reply(
                instructions=(
                    "Repeat the active follow-up question exactly as "
                    "previously asked: "
                    f"{self.active_followup_question}"
                )
            )
        else:
            await self._ask_current_question(acknowledge="Of course.")

    async def _clarify_active_question(self):
        if self.phase == "followup":
            question = self.active_followup_question
        else:
            question = await self._get_active_question_text()

        await self.session.generate_reply(
            instructions=(
                "Rephrase this interview question in simpler language. "
                "Do not provide an answer or technical hints. "
                f"Question: {question}"
            )
        )

    async def _finish_interview(self):
        if self.interview_ended:
            return

        self.interview_ended = True
        self.phase = "completed"
        self.awaiting_choice = False

        await self.session.generate_reply(
            instructions=(
                "Thank the candidate for their time and participation. "
                "Conclude the interview warmly and professionally. "
                "Do not invent or announce assessment scores."
            )
        )

    async def on_user_turn_completed(self, turn_ctx, new_message):
        try:
            if self.interview_ended:
                logger.info("Ignoring message after interview termination")
                return

            message = (new_message.text_content or "").strip()
            if not message:
                logger.warning("Empty candidate utterance")
                return

            intent = self.bridge.classify_candidate_message(message)
            normalized = message.lower()

            logger.info(
                "Candidate intent=%s phase=%s awaiting_choice=%s",
                getattr(intent, "value", str(intent)),
                self.phase,
                self.awaiting_choice,
            )

            if intent == ConversationIntent.REPEAT:
                await self._repeat_active_question()
                return

            if intent == ConversationIntent.END_INTERVIEW:
                await self._finish_interview()
                return

            if intent == ConversationIntent.CLARIFY:
                await self._clarify_active_question()
                return

            if intent == ConversationIntent.DONT_KNOW:
                self.awaiting_choice = True
                await self.session.generate_reply(
                    instructions=(
                        "Respond empathetically. Tell the candidate it is okay "
                        "not to know every answer. Ask whether they would "
                        "like to try answering or skip this question. "
                        "Do not reveal the answer."
                    )
                )
                return

            if self.awaiting_choice:
                skip_phrases = (
                    "skip", "pass", "next question", "move on",
                    "let's move on", "lets move on",
                )
                try_phrases = (
                    "try", "attempt", "give it a try",
                    "let me think", "i will try", "i'll try",
                )

                if any(phrase in normalized for phrase in skip_phrases):
                    await self._skip_current_question()
                    return

                if any(phrase in normalized for phrase in try_phrases):
                    self.awaiting_choice = False

                    if self.phase == "followup":
                        await self.session.generate_reply(
                            instructions=(
                                "Encourage the candidate to try. Repeat the "
                                "active follow-up question exactly: "
                                f"{self.active_followup_question}"
                            )
                        )
                    else:
                        await self._ask_current_question(
                            acknowledge="Certainly. Take your time."
                        )
                    return

                if len(message.split()) > 3:
                    self.awaiting_choice = False
                    await self._process_candidate_answer(message)
                    return

                await self.session.generate_reply(
                    instructions=(
                        "Ask the candidate whether they would like "
                        "to attempt the question or skip it."
            )
                )
                return

            if intent == ConversationIntent.SKIP:
                await self._skip_current_question()
                return

            if intent == ConversationIntent.OFF_TOPIC:
                await self.session.generate_reply(
                    instructions=(
                        "Respond briefly and politely, then redirect "
                        "the conversation toward the current interview question."
                    )
                )
                return

            if self.phase == "introduction":
                self.phase = "technical"
                await self._ask_current_question(
                    acknowledge=(
                        "Thank the candidate for the introduction. "
                        "Transition naturally into the technical interview."
                    )
                )
                return

            if self.phase in {"technical", "followup"}:
                await self._process_candidate_answer(message)
                return

        except Exception:
            logger.exception("Failed to process candidate turn")
            await self.session.generate_reply(
                instructions=(
                    "Apologize briefly for the technical interruption. "
                    "Ask the candidate to repeat their last response."
                )
            )


async def entrypoint(ctx: agents.JobContext):
    logger.info("Connecting to LiveKit room: %s", ctx.room.name)

    session_id = ctx.room.name
    bridge = InterviewBridge(session_id=session_id)
    interview_context = await bridge.get_interview_context()

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=LocalWhisperSTT(model_size="base"),
        llm=openai.LLM(
            model="gemma3:4b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        tts=LocalKokoroTTS(),
    )

    await ctx.connect()

    await session.start(
        room=ctx.room,
        agent=InterviewAgent(
            bridge=bridge,
            interview_context=interview_context,
        ),
    )

    logger.info("Interview voice agent started.")


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="interview-agent",
        )
    )
