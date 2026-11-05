
import { useState, useEffect, useRef } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useConnectionState,
  useLocalParticipant,
} from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import "@livekit/components-styles";
import "./App.css";
import interviewerImage from "./assets/interviewer.png";

const API_URL = "http://localhost:8000/api/v1";

interface InterviewData {
  session_id: string;
  candidate_name: string;
  status: string;
  current_question: {
    question: string;
    skill: string;
    difficulty: string;
  };
  total_questions: number;
}

interface TokenData {
  token: string;
  url: string;
}

interface CategoryScore {
  name: string;
  weight: number;
  score: number | null;
}

interface QuestionReport {
  question_index: number;
  skill: string;
  category: string;
  category_name: string;
  question: string;
  candidate_answer: string;
  category_score: number;
  category_score_out_of_100: number | null;
  assessment_status: string;
  strengths: string[];
  weaknesses: string[];
  missing_concepts: string[];
  incorrect_claims: string[];
  suggested_improvements: string[];
  expected_point_evaluations: {
    point: string;
    status: string;
    explanation?: string;
  }[];
}

interface InterviewReport {
  session_id: string;
  candidate_name: string;
  interview_status: string;
  total_questions: number;
  overall_score: number | null;
  maximum_score: number;
  assessment_complete: boolean;
  score_status: string;
  category_scores: Record<string, CategoryScore>;
  skill_wise_scores: Record<string, number>;
  question_reports: QuestionReport[];
}

function InterviewRoom({
  interview,
  onEnd,
}: {
  interview: InterviewData;
  onEnd: () => void;
}) {
  const connectionState = useConnectionState();
  const { localParticipant } = useLocalParticipant();

  const [micEnabled, setMicEnabled] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    if (connectionState === ConnectionState.Connected) {
      localParticipant
        .setMicrophoneEnabled(true)
        .then(() => setMicEnabled(true))
        .catch((error) => console.error("Microphone error:", error));
    }
  }, [connectionState, localParticipant]);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTime((previous) => previous + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formattedTime = `${String(Math.floor(elapsedTime / 60)).padStart(
    2,
    "0"
  )}:${String(elapsedTime % 60).padStart(2, "0")}`;

  return (
    <div className="app-container live-app">
      <header className="navbar live-navbar">
        <div className="logo">
          <span className="logo-icon">AI</span>
          <span>
            Interview<span className="highlight">AI</span>
          </span>
        </div>

        <div className="live-header-right">
          <span className="live-indicator">
            <span className="live-dot" />
            LIVE INTERVIEW
          </span>
          <span className="live-timer">{formattedTime}</span>
        </div>
      </header>

      <main className="live-main">
        <section className="live-interview-card">
          <div className="live-top-info">
            <div>
              <span className="interview-label">TECHNICAL INTERVIEW</span>
              <h2>You're in the interview, {interview.candidate_name}</h2>
              <p>Focus on the conversation. Take your time to answer.</p>
            </div>

            <div className="connection-status">
              <span className="connection-dot" />
              {connectionState === ConnectionState.Connected
                ? "Connected"
                : "Connecting"}
            </div>
          </div>

          <div className="ai-interviewer-stage">
            <div className="ai-avatar-container">
              <div className="avatar-glow" />

              <div className="avatar-orbit orbit-one">
                <div className="avatar-orbit orbit-two" />
              </div>

              <img
                src={interviewerImage}
                alt="AI Interviewer"
                className="interviewer-photo"
              />
            </div>

            <div className="ai-interviewer-info">
              <div className="ai-status">
                <span className="ai-status-dot" />
                AI INTERVIEWER
              </div>

              <h3>Your interviewer is here</h3>

              <p className="ai-description">
                Listen carefully and respond naturally.
                <br />
                Your conversation is happening in real time.
              </p>

              <div className="sound-wave">
                {Array.from({ length: 31 }).map((_, index) => (
                  <span
                    key={index}
                    style={{
                      animationDelay: `${index * 0.055}s`,
                      height: `${12 + Math.abs(Math.sin(index * 0.65)) * 35}px`,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="live-bottom-section">
            <div className="candidate-audio-status">
              <div className={`mic-icon ${micEnabled ? "mic-on" : ""}`}>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="9" y="2" width="6" height="12" rx="3" />
                  <path d="M5 10a7 7 0 0 0 14 0" />
                  <path d="M12 17v5" />
                </svg>
              </div>

              <div className="mic-text">
                <span>{micEnabled ? "Microphone is on" : "Activating microphone"}</span>
                <small>Speak clearly when the interviewer asks a question</small>
              </div>

              <span className="mic-live-badge">
                <span />
                LIVE
              </span>
            </div>

            <div className="live-controls">
              <div className="interview-progress">
                <span>INTERVIEW IN PROGRESS</span>
                <span className="progress-live-dot" />
              </div>

              <button className="end-interview-button" onClick={onEnd}>
                <svg
                  width="17"
                  height="17"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
                End Interview
              </button>
            </div>
          </div>
        </section>

        <p className="live-footer-note">
          <span>🔒</span> Your interview session is private and secure
        </p>
      </main>

      <RoomAudioRenderer />
    </div>
  );
}

function ScoreBar({
  score,
  color = "#7c5cff",
}: {
  score: number | null;
  color?: string;
}) {
  const value = score ?? 0;

  return (
    <div className="score-bar-track">
      <div
        className="score-bar-fill"
        style={{
          width: `${Math.min(100, Math.max(0, value))}%`,
          background: color,
        }}
      />
    </div>
  );
}

function ResultsDashboard({
  report,
  onHome,
}: {
  report: InterviewReport;
  onHome: () => void;
}) {
  const score = report.overall_score;
  const scoreColor =
    score === null
      ? "#64748b"
      : score >= 80
      ? "#22c55e"
      : score >= 60
      ? "#f59e0b"
      : "#ef4444";

  return (
    <div className="app-container results-app">
      <header className="navbar results-navbar">
        <div className="logo">
          <span className="logo-icon">AI</span>
          <span>
            Interview<span className="highlight">AI</span>
          </span>
        </div>

        <button className="results-home-button" onClick={onHome}>
          ← Back to Home
        </button>
      </header>

      <main className="results-main">
        <div className="results-heading">
          <span className="hero-tag">
            ✦ {report.interview_status === "completed"
              ? "INTERVIEW COMPLETED"
              : "INTERVIEW ENDED"}
          </span>
          <h1>
            Your Performance <span className="gradient-text">Report</span>
          </h1>
          <p>
            Great work, {report.candidate_name}. Here's your detailed interview
            assessment.
          </p>
        </div>

        <section className="results-overview">
          <div className="overall-score-card">
            <span className="results-card-label">OVERALL SCORE</span>

            <div
              className="score-circle"
              style={{ "--score-color": scoreColor, "--score-value": score ?? 0 } as React.CSSProperties}
            >
              <div className="score-circle-inner">
                <strong>{score !== null ? score.toFixed(1) : "N/A"}</strong>
                <span>out of 100</span>
              </div>
            </div>

            <span className={`assessment-badge ${report.score_status}`}>
              {report.score_status === "complete"
                ? "Complete Assessment"
                : "Provisional Assessment"}
            </span>

            <p>
              {report.assessment_complete
                ? "All assessment categories have been evaluated."
                : "Some categories are still awaiting assessment."}
            </p>
          </div>

          <div className="category-scores-card">
            <div className="results-section-heading">
              <div>
                <span className="results-card-label">PERFORMANCE BREAKDOWN</span>
                <h2>Category Scores</h2>
              </div>
            </div>

            <div className="category-score-list">
              {Object.entries(report.category_scores).map(([key, category]) => (
                <div className="category-score-item" key={key}>
                  <div className="category-score-header">
                    <span>{category.name}</span>
                    <strong>
                      {category.score !== null
                        ? `${category.score.toFixed(1)} / 100`
                        : "Not assessed"}
                    </strong>
                  </div>

                  <ScoreBar
                    score={category.score}
                    color={
                      key === "technical"
                        ? "#7c5cff"
                        : key === "coding"
                        ? "#06b6d4"
                        : key === "scenario"
                        ? "#f59e0b"
                        : "#22c55e"
                    }
                  />

                  <small>Weight: {(category.weight * 100).toFixed(0)}%</small>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="skill-scores-section">
          <div className="results-section-heading">
            <div>
              <span className="results-card-label">YOUR EXPERTISE</span>
              <h2>Skill-wise Performance</h2>
            </div>
          </div>

          {Object.keys(report.skill_wise_scores).length === 0 ? (
            <p className="results-empty">No skill-wise scores available yet.</p>
          ) : (
            <div className="skill-score-grid">
              {Object.entries(report.skill_wise_scores).map(([skill, skillScore]) => (
                <div className="skill-score-card" key={skill}>
                  <span>{skill}</span>
                  <strong>{skillScore.toFixed(1)}%</strong>
                  <ScoreBar score={skillScore} />
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="question-results-section">
          <div className="results-section-heading">
            <div>
              <span className="results-card-label">DETAILED FEEDBACK</span>
              <h2>Question-wise Evaluation</h2>
            </div>
            <span className="question-count">
              {report.total_questions} Questions
            </span>
          </div>

          <div className="question-results-list">
            {report.question_reports.map((question, index) => (
              <details className="question-result-card" key={question.question_index}>
                <summary>
                  <div className="question-summary-left">
                    <span className="question-number">Q{index + 1}</span>
                    <div>
                      <h3>{question.skill}</h3>
                      <p>{question.category_name}</p>
                    </div>
                  </div>

                  <div className="question-summary-right">
                    <span
                      className={`question-score ${
                        question.assessment_status === "assessed"
                          ? ""
                          : "not-assessed"
                      }`}
                    >
                      {question.category_score_out_of_100 !== null
                        ? `${question.category_score_out_of_100.toFixed(1)} / 100`
                        : "Not assessed"}
                    </span>
                    <span className="expand-icon">+</span>
                  </div>
                </summary>

                <div className="question-result-content">
                  <div className="question-text-block">
                    <span>QUESTION</span>
                    <p>{question.question}</p>
                  </div>

                  <div className="candidate-answer-block">
                    <span>YOUR ANSWER</span>
                    <p>
                      {question.candidate_answer || "No answer recorded."}
                    </p>
                  </div>

                  {question.expected_point_evaluations?.length > 0 && (
                    <div className="expected-points-block">
                      <h4>Expected Concepts</h4>
                      {question.expected_point_evaluations.map((point, pointIndex) => (
                        <div className="expected-point-item" key={pointIndex}>
                          <span
                            className={`point-status ${point.status.replace(
                              /[^a-zA-Z0-9-]/g,
                              ""
                            )}`}
                          >
                            {point.status === "covered"
                              ? "✓"
                              : point.status === "partially_covered"
                              ? "~"
                              : "✕"}
                          </span>
                          <div>
                            <p>{point.point}</p>
                            {point.explanation && <small>{point.explanation}</small>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="feedback-grid">
                    {question.strengths?.length > 0 && (
                      <div className="feedback-block strengths-block">
                        <h4>✦ Strengths</h4>
                        <ul>
                          {question.strengths.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {question.weaknesses?.length > 0 && (
                      <div className="feedback-block weaknesses-block">
                        <h4>↗ Areas to Improve</h4>
                        <ul>
                          {question.weaknesses.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {question.missing_concepts?.length > 0 && (
                      <div className="feedback-block missing-block">
                        <h4>Missing Concepts</h4>
                        <ul>
                          {question.missing_concepts.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {question.incorrect_claims?.length > 0 && (
                      <div className="feedback-block incorrect-block">
                        <h4>Incorrect Claims</h4>
                        <ul>
                          {question.incorrect_claims.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {question.suggested_improvements?.length > 0 && (
                      <div className="feedback-block improvements-block">
                        <h4>Suggested Improvements</h4>
                        <ul>
                          {question.suggested_improvements.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </details>
            ))}
          </div>
        </section>

        <div className="results-bottom-action">
          <button className="start-button" onClick={onHome}>
            Start a New Interview →
          </button>
        </div>
      </main>
    </div>
  );
}

function App() {
  const [candidateName, setCandidateName] = useState("Rutvik");
  const [jobDescription, setJobDescription] = useState("");
  const [candidateProfile, setCandidateProfile] = useState("");
  const [skills, setSkills] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [numQuestions, setNumQuestions] = useState(5);

  const [interview, setInterview] = useState<InterviewData | null>(null);
  const [completedSessionId, setCompletedSessionId] = useState<string | null>(null);
  const [liveKitToken, setLiveKitToken] = useState<TokenData | null>(null);
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState("");
  const [reportError, setReportError] = useState("");

  const endingInterviewRef = useRef(false);

  const handleStartInterview = async () => {
    setLoading(true);
    setError("");
    setReport(null);
    setReportError("");
    endingInterviewRef.current = false;

    try {
      const response = await fetch(`${API_URL}/interviews/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          candidate_name: candidateName,
          job_description: jobDescription,
          candidate_profile: candidateProfile,
          skills: skills.split(",").map((skill) => skill.trim()).filter(Boolean),
          difficulty,
          num_questions: numQuestions,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to start interview");
      }

      const tokenResponse = await fetch(`${API_URL}/livekit/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: data.session_id,
          participant_name: candidateName,
        }),
      });

      const tokenData = await tokenResponse.json();

      if (!tokenResponse.ok) {
        throw new Error(
          tokenData.detail || "Failed to generate LiveKit token"
        );
      }

      setInterview(data);
      setCompletedSessionId(data.session_id);
      setLiveKitToken(tokenData);
    } catch (error) {
      console.error("Interview error:", error);
      setError(
        error instanceof Error
          ? error.message
          : "Unable to start interview. Check whether the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };


const handleEndInterview = async () => {
  if (endingInterviewRef.current) return;

  endingInterviewRef.current = true;

  // Preserve the session ID before disconnecting LiveKit.
  const sessionId = interview?.session_id || completedSessionId;

  setLiveKitToken(null);
  setInterview(null);

  if (!sessionId) {
    setReportError("Interview session ID is unavailable.");
    endingInterviewRef.current = false;
    return;
  }

  setCompletedSessionId(sessionId);
  setReportLoading(true);
  setReportError("");
  setReport(null);

  try {
    // First: mark the interview as terminated.
    const endResponse = await fetch(
      `${API_URL}/interviews/${sessionId}/end`,
      { method: "POST" }
    );

    const endData = await endResponse.json();

    if (!endResponse.ok) {
      throw new Error(
        endData.detail || "Unable to terminate interview."
      );
    }

    // Second: generate the report.
    const reportResponse = await fetch(
      `${API_URL}/interviews/${sessionId}/report`
    );

    const reportData = await reportResponse.json();

    if (!reportResponse.ok) {
      throw new Error(
        reportData.detail || "Unable to generate interview report."
      );
    }

    setReport(reportData);

  } catch (error) {
    console.error("Interview termination/report error:", error);

    setReportError(
      error instanceof Error
        ? error.message
        : "Unable to generate interview report."
    );

  } finally {
    setReportLoading(false);
  }
};

  const handleReturnHome = () => {
    setReport(null);
    setReportError("");
    endingInterviewRef.current = false;
  };

  if (reportLoading) {
    return (
      <div className="app-container results-app">
        <div className="report-loading">
          <div className="report-spinner" />
          <h2>Analyzing Your Interview</h2>
          <p>
            Your AI interviewer is evaluating your responses and preparing your
            performance report.
          </p>
        </div>
      </div>
    );
  }

  if (report) {
    return <ResultsDashboard report={report} onHome={handleReturnHome} />;
  }

  if (reportError) {
    return (
      <div className="app-container results-app">
        <div className="report-error-card">
          <h2>Interview Finished</h2>
          <p>{reportError}</p>
          <button
            className="start-button"
            onClick={handleReturnHome}
          >
            Back to Home
          </button>
          <button
            className="retry-report-button"
            onClick={async () => {
              if (!completedSessionId) {
                setReportError(
                  "The session ID is no longer available. Please start a new interview."
                );
                return;
              }
              setReportLoading(true);
              setReportError("");
              try {
                const response = await fetch(
                  `${API_URL}/interviews/${completedSessionId}/report`
                );
                const data = await response.json();
                if (!response.ok) {
                  throw new Error(
                    data.detail || "Unable to generate interview report."
                  );
                }
                setReport(data);
              } catch (error) {
                console.error("Report generation failed:", error);
                setReportError(
                  error instanceof Error
                    ? error.message
                    : "Unable to generate interview report."
                );
              } finally {
                setReportLoading(false);
              }
            }}
          >
            Retry Report
          </button>
        </div>
      </div>
    );
  }

  if (interview && liveKitToken) {
    return (
      <LiveKitRoom
        token={liveKitToken.token}
        serverUrl={liveKitToken.url}
        connect={true}
        audio={true}
        video={false}
        onDisconnected={handleEndInterview}
      >
        <InterviewRoom interview={interview} onEnd={handleEndInterview} />
      </LiveKitRoom>
    );
  }

  return (
    <div className="app-container">
      <header className="navbar">
        <div className="logo">
          <span className="logo-icon">AI</span>
          <span>
            Interview<span className="highlight">AI</span>
          </span>
        </div>
        <span className="nav-badge">REAL-TIME AI ASSESSMENT</span>
      </header>

      <main className="main-content">
        <div className="hero">
          <div className="hero-tag">✦ AI-POWERED INTERVIEW PLATFORM</div>
          <h1>
            Land your dream job with
            <br />
            <span className="gradient-text">AI-powered interviews.</span>
          </h1>
          <p>
            Practice real-world technical interviews with an AI interviewer.
            Get evaluated, improve your skills, and build confidence.
          </p>
        </div>

        <div className="interview-card">
          <div className="card-header">
            <div>
              <h2>Configure Your Interview</h2>
              <p>Set up your personalized technical assessment.</p>
            </div>
            <span className="status-badge">● Ready to begin</span>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label>Candidate Name</label>
              <input
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                placeholder="Enter your name"
              />
            </div>

            <div className="form-group">
              <label>Interview Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>

            <div className="form-group full-width">
              <label>Job Description</label>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the job description here..."
                rows={4}
              />
            </div>

            <div className="form-group full-width">
              <label>Candidate Profile / Resume Summary</label>
              <textarea
                value={candidateProfile}
                onChange={(e) => setCandidateProfile(e.target.value)}
                placeholder="Describe your experience, projects, and background..."
                rows={3}
              />
            </div>

            <div className="form-group">
              <label>Skills (comma separated)</label>
              <input
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
                placeholder="Python, ML, LangChain, RAG"
              />
            </div>

            <div className="form-group">
              <label>Number of Questions</label>
              <select
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
              >
                <option value={3}>3 Questions</option>
                <option value={5}>5 Questions</option>
                <option value={10}>10 Questions</option>
                <option value={15}>15 Questions</option>
                <option value={20}>20 Questions</option>
              </select>
            </div>
          </div>

          {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}

          <button
            className="start-button"
            onClick={handleStartInterview}
            disabled={loading}
          >
            {loading ? "Starting Interview..." : "Start Interview →"}
          </button>

          <p className="card-footer">
            🎙️ Voice-enabled &nbsp;·&nbsp; ⚡ Real-time evaluation
            &nbsp;·&nbsp; 🔒 Private assessment
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
