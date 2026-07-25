"""
agents/response_agent.py

Response Agent: turns SQL execution output into a natural-language
answer instead of dumping a raw table. Falls back to a clear templated
message (no LLM call) for error/validation-failure paths, since there's
nothing meaningful to summarize in those cases.
"""

from __future__ import annotations

from graph.state import GraphState
from prompts.response_summary import build_response_summary_prompt

MAX_PREVIEW_ROWS = 10


def response_node(state: GraphState, llm) -> GraphState:
    """Builds the final natural-language response.

    Args:
        state: current graph state.
        llm: chat model used to summarize successful results. Not called
            on error paths.
    """
    trace = state.get("agent_trace", [])
    trace.append("response_agent")

    validation_result = state.get("validation_result")
    execution_result = state.get("execution_result")

    if validation_result is not None and not validation_result.get("is_valid", True):
        errors = "; ".join(validation_result.get("errors", []))
        final_response = f"I couldn't run that query safely: {errors}"

    elif execution_result is not None and not execution_result.get("success", True):
        final_response = (
            "I tried generating and running a query for that, but it kept failing "
            f"after {state.get('retry_count', 0)} attempt(s). "
            f"Last error: {execution_result.get('error_message')}"
        )

    elif execution_result is not None:
        df = execution_result.get("dataframe")
        row_count = execution_result.get("row_count", 0)

        if df is None or row_count == 0:
            final_response = "That query ran successfully but returned no matching rows."
        else:
            preview_csv = df.head(MAX_PREVIEW_ROWS).to_csv(index=False)
            prompt = build_response_summary_prompt()
            messages = prompt.format_messages(
                user_query=state["user_query"],
                row_count=row_count,
                data_preview=preview_csv,
            )
            response = llm.invoke(messages)
            final_response = response.content.strip()

    else:
        final_response = "I wasn't able to process that request."

    return {
        "final_response": final_response,
        "agent_trace": trace,
    }
