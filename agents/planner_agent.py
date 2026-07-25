"""
agents/planner_agent.py

Planner Agent: the first node in the graph. Decides user intent
(data retrieval, aggregation, analytics, schema info, etc.) and which
downstream agents are required.

This is currently a stub that always routes to the full pipeline so the
graph is runnable end-to-end. The real LLM-based intent classification is
filled in once the graph skeleton (this step) is verified.
"""

from __future__ import annotations

from graph.state import GraphState

# Every node downstream of the planner, in execution order. Once real
# intent classification is added, simple requests (e.g. "list the
# tables") will be routed straight to the Schema Agent and skip SQL
# generation/execution entirely.
DEFAULT_PIPELINE = [
    "schema_agent",
    "sql_generator_agent",
    "sql_validator_agent",
    "execution_agent",
    "response_agent",
]


def planner_node(state: GraphState) -> GraphState:
    """Classifies user intent and decides which agents are needed.

    TODO (next step): replace the hardcoded intent/pipeline with an LLM
    call that classifies `state["user_query"]` into one of the intents
    defined in GraphState and trims `required_agents` accordingly.
    """
    trace = state.get("agent_trace", [])
    trace.append("planner_agent")

    return {
        "intent": "data_retrieval",
        "required_agents": DEFAULT_PIPELINE,
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3),
        "agent_trace": trace,
    }
