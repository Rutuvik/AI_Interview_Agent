
from langgraph.graph import StateGraph, START, END
from app.graph.interview_state import InterviewState
from app.graph.interview_nodes import (
    ask_question,
    evaluate_answer,
     evaluate_communication,
    next_question,
    route_after_evaluation,
)


def build_interview_graph():
    """
    Construct and compile the AI interview workflow.
    """

    workflow = StateGraph(InterviewState)

    # Register nodes
    workflow.add_node("ask_question", ask_question)
    workflow.add_node("evaluate_answer", evaluate_answer)
    workflow.add_node("evaluate_communication", evaluate_communication)
    workflow.add_node("next_question", next_question)

    # Define workflow entry
    workflow.add_edge(START, "ask_question")

    # Define normal transitions
    workflow.add_edge("ask_question", END)

    workflow.add_conditional_edges(
        "evaluate_answer",
        route_after_evaluation,
        {
            "next_question": "next_question",
            "finish": "evaluate_communication",
        },
    )

    workflow.add_edge("next_question", "ask_question")
    workflow.add_edge("evaluate_communication", END)
    return workflow.compile()


interview_graph = build_interview_graph()
