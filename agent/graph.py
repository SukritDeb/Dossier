from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes import (
    intake_node,
    planner_node,
    tools_node,
    grader_node,
    grade_router,
    enricher_node,
    writer_node
)


def build_graph():
    builder = StateGraph(AgentState)

    # ALL NODES 
    builder.add_node("intake_node",   intake_node)
    builder.add_node("planner_node",  planner_node)
    builder.add_node("tools_node",    tools_node)
    builder.add_node("grader_node",   grader_node)
    builder.add_node("enricher_node", enricher_node)
    builder.add_node("writer_node",   writer_node)

    # FIXED EDGES 
    builder.add_edge(START,           "intake_node")
    builder.add_edge("intake_node",   "planner_node")
    builder.add_edge("planner_node",  "tools_node")
    builder.add_edge("tools_node",    "grader_node")

    # After enrich - always write (no re-grading)
    builder.add_edge("enricher_node", "writer_node")
    builder.add_edge("writer_node",   END)

    # CONDITIONAL EDGE 
    # After grader, route based on quality score
    builder.add_conditional_edges(
        "grader_node",
        grade_router,
        {
            "planner_node" : "planner_node",    # loop: re-search
            "enricher_node": "enricher_node",   # branch: enrich
            "writer_node"  : "writer_node"      # done: write
        }
    )

    return builder.compile()

# Compile once at import time
agent_graph = build_graph()