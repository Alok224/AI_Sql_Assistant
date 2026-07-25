"""
agents/retry_agent.py

Retry Agent: on execution failure, feeds the database error back into the
loop so the SQL Generator can try again. The retry-count bookkeeping and
the should_retry() routing check are real now; the actual "ask the LLM to
fix the query using this error" prompt is added alongside the SQL
Generator's real implementation.
"""

from __future__ import annotations

from graph.state import GraphState

MAX_RETRIES_DEFAULT = 3


def retry_node(state: GraphState) -> GraphState:
    """Increments the retry counter ahead of looping back to SQL
    generation. The error itself (state["last_error"]) was already set
    by the Execution Agent or the Validator on failure.
    """
    trace = state.get("agent_trace", [])
    trace.append("retry_agent")

    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "agent_trace": trace,
    }


def route_after_validation(state: GraphState) -> str:
    """Conditional-edge function used right after the Validator node.

    Returns:
        "execute" if the SQL passed validation,
        "retry" if it failed but retries remain,
        "give_up" if it failed and retries are exhausted.
    """
    validation_result = state.get("validation_result", {})
    if validation_result.get("is_valid", False):
        return "execute"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", MAX_RETRIES_DEFAULT)
    if retry_count >= max_retries:
        return "give_up"
    return "retry"


def should_retry(state: GraphState) -> str:
    """Conditional-edge function: decides where to go after execution.

    Returns:
        "retry" if execution failed and retries remain,
        "respond" if execution succeeded or validation failed outright,
        "give_up" if execution failed and retries are exhausted.
    """
    execution_result = state.get("execution_result")
    validation_result = state.get("validation_result")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", MAX_RETRIES_DEFAULT)

    validation_failed = validation_result is not None and not validation_result.get(
        "is_valid", True
    )
    execution_failed = execution_result is not None and not execution_result.get(
        "success", True
    )

    if not (validation_failed or execution_failed):
        return "respond"

    if retry_count >= max_retries:
        return "give_up"

    return "retry"
