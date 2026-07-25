"""
agents/execution_agent.py

Execute SQL Agent: runs validated SQL against the connected database and
returns a dataframe, row count, and execution time. Fully implemented now
(unlike the LLM-dependent agents) since it's pure SQLAlchemy + timing,
nothing to defer.
"""

from __future__ import annotations

import time

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from graph.state import ExecutionResult, GraphState


def execution_node(state: GraphState, engine: Engine) -> GraphState:
    """Executes `state["generated_sql"]` if it passed validation.

    Args:
        state: current graph state. Expects `validation_result.is_valid`
            to already be True -- the graph's conditional edges should
            route invalid SQL to the Retry Agent instead of here.
        engine: the SQLAlchemy engine to run against, injected by the
            graph builder.
    """
    trace = state.get("agent_trace", [])
    trace.append("execution_agent")

    sql = state["generated_sql"]
    start = time.perf_counter()

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
        df = pd.DataFrame(rows, columns=columns)
        elapsed = time.perf_counter() - start

        execution_result: ExecutionResult = {
            "success": True,
            "dataframe": df,
            "row_count": len(df),
            "execution_time_seconds": round(elapsed, 4),
            "error_message": None,
        }
        return {
            "execution_result": execution_result,
            "last_error": None,
            "agent_trace": trace,
        }

    except Exception as exc:  # noqa: BLE001 - error text feeds the Retry Agent
        elapsed = time.perf_counter() - start
        execution_result = {
            "success": False,
            "dataframe": None,
            "row_count": 0,
            "execution_time_seconds": round(elapsed, 4),
            "error_message": str(exc),
        }
        return {
            "execution_result": execution_result,
            "last_error": str(exc),
            "agent_trace": trace,
        }
