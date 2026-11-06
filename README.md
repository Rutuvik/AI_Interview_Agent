AI Interview Platform
Real-Time Voice Interview & Assessment Platform
An AI-powered technical interview platform designed to conduct real-time voice interviews, generate role-specific questions, evaluate candidate answers, and produce structured assessment reports.
  Project status: Active development
  Purpose: AI Engineer technical project assignment
Overview
The platform combines a FastAPI, Langgraph, Pydentic backend, and a LiveKit voice agent to provide an interactive technical interview experience.

It accepts a candidate profile, job description, required skills, and interview difficulty. It generates technical questions, conducts a spoken interview, asks contextual follow-up questions when clarification is needed, evaluates candidate responses, and makes the assessment available for review.
Key Features
- Real-time voice interview: Two-way voice interaction through LiveKit.
- Speech pipeline: Local Whisper speech-to-text, Silero voice activity detection, and Kokoro text-to-speech integrations.
- Role-specific question generation: Uses candidate profile, job description, required skills, and difficulty.
- Adaptive conversation: Presents one question at a time and asks contextual follow-ups when useful.
- Conversation controls: Repeat, clarify, skip, attempt, and end interview.
- AI answer evaluation: Scores technical correctness, conceptual understanding, and completeness on a 0–5 scale.
- Evidence-based feedback: Identifies strengths, weaknesses, missing concepts, incorrect claims, answer evidence, and suggested improvements.
- Assessment reports: Provides overall and skill-wise results, knowledge gaps, and learning recommendations.
- | Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend API | Python, FastAPI |
| Real-time voice | LiveKit Agents |
| Speech-to-text | Local Whisper integration |
| Voice activity detection | Silero VAD |
| Text-to-speech | Local Kokoro integration |
| LLM runtime | Ollama |
| Voice-agent model | `gemma3:4b` |
| Workflow orchestration | LangGraph |
| Data validation | Pydantic |
| Persistence | SQLAlchemy with configured async database |
| Testing | pytest |

How It Works
1. The user configures an interview with a job description, candidate profile, skills, difficulty, and question count.
2. The frontend sends the configuration to FastAPI.
3. The interview service generates questions and initializes interview state.
4. The frontend obtains LiveKit credentials and joins the interview room.
5. The LiveKit agent retrieves interview context and greets the candidate.
6. Candidate speech is transcribed and processed as a conversational turn.
7. The agent may ask a contextual follow up and accumulates the main answer with follow-up responses.
8. The answer is submitted to the backend evaluation workflow.
9. The interview advances to the next question or completes.
10. The frontend retrieves and presents the assessment report.
Getting Started
Prerequisites
- Python 3.11
- Node.js and npm
- Ollama
- LiveKit credentials and required environment configuration
- Install the voice-agent model if it is not already installed:- ollama pull gemma3:4b
- Clone the repository:- git clone https://github.com/Rutuvik/AI_Interview_Agent.git, cd AI_Interview_Agent
- Set the backend:-
cd backend
python3.11 -m venv ivenv
source ivenv/bin/activate
pip install -r requirements.txt
- Start FastAPI:- uvicorn app.main:app --reload
- Start the LiveKit agent
cd backend
source ivenv/bin/activate
python -m py_compile backend/app/agents/voice_agent.py
- Start the frontend
cd frontend
npm install
npm run dev
Known Limitations
This project is under active development.
- Voice quality and response latency depend on local hardware, model size, and runtime configuration.
- Local LLM inference may contend for CPU/GPU and memory resources.
- AI-generated scores can differ from human judgments; benchmark results are needed to quantify agreement.
- Interview recovery, text fallback, and failure handling must be tested before being described as production ready.
- The recorded backend test baseline is below the assignment's minimum of 20 tests until additional tests are added.
- ## Future Updates

- [ ] **Evaluation:** Build a 20 scenario benchmark and compare AI scores against human reviewed scores.
- [ ] **Testing & Reliability:** Expand automated tests, validate model outputs, test failure scenarios, and measure latency.
- [ ] **Interview Experience:** Improve adaptive follow-ups, interruption handling, text fallback, and interview recovery.
- [ ] **Assessment Reports:** Add sample reports, report exports, and detailed skill wise evaluation.
- [ ] **Engineering & Deployment:** Add CI/CD, deployment documentation, database backup guidance, and stronger security practices.
