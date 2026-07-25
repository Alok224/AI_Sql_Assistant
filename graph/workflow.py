"""
graph/workflow.py


This module only builds the graph -- it does not yet replace the
create_sql_agent path in app.py. That swap happens once the LLM-backed
nodes (planner, schema, sql_generator) have their real implementations
instead of the current stubs, so we don't ship a regression.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph
from sqlalchemy.engine import Engine

from agents.execution_agent import execution_node
from agents.planner_agent import planner_node
from agents.response_agent import response_node
from agents.retry_agent import retry_node, route_after_validation, should_retry
from agents.schema_agent import schema_node
from agents.sql_generator_agent import sql_generator_node
from agents.sql_validator_agent import sql_validator_node
from graph.state import GraphState


def build_graph(llm, db, engine: Engine, allow_write_ops: bool = False):
    """Assembles and compiles the agent graph.

    Args:
        llm: chat model used by the SQL Generator (and, later, the
            Planner and Response agents).
        db: langchain_community.utilities.SQLDatabase used by the
            Schema Agent.
        engine: SQLAlchemy engine used by the Execution Agent.
        allow_write_ops: passed through to the Validator. False (the
            default) enforces Read Only mode.

    Returns:
        A compiled LangGraph graph with an `.invoke(state)` method.
    """
    graph = StateGraph(GraphState)

    
    graph.add_node("planner_agent", planner_node)
    graph.add_node("schema_agent", partial(schema_node, db=db))
    graph.add_node("sql_generator_agent", partial(sql_generator_node, llm=llm))
    graph.add_node(
        "sql_validator_agent", partial(sql_validator_node, allow_write_ops=allow_write_ops)
    )
    graph.add_node("execution_agent", partial(execution_node, engine=engine))
    graph.add_node("retry_agent", retry_node)
    graph.add_node("response_agent", partial(response_node, llm=llm))

    graph.add_edge(START, "planner_agent")
    graph.add_edge("planner_agent", "schema_agent")
    graph.add_edge("schema_agent", "sql_generator_agent")
    graph.add_edge("sql_generator_agent", "sql_validator_agent")

    graph.add_conditional_edges(
        "sql_validator_agent",
        route_after_validation,
        {
            "execute": "execution_agent",
            "retry": "retry_agent",
            "give_up": "response_agent",
        },
    )

    graph.add_conditional_edges(
        "execution_agent",
        should_retry,
        {
            "respond": "response_agent",
            "retry": "retry_agent",
            "give_up": "response_agent",
        },
    )


    graph.add_edge("retry_agent", "sql_generator_agent")

    graph.add_edge("response_agent", END)

    return graph.compile()
