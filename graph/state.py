"""
graph/state.py

Shared state schema for the LangGraph multi-agent SQL workflow.

Every node in the graph (Planner, Schema, SQL Generator, Validator,
Execute, Retry, Response) reads from and writes to this single
TypedDict. Keeping it in one place is what lets nodes stay independent --
a node only needs to know which keys it reads and which it writes, not
how any other node works internally.
"""

from __future__ import annotations

from typing import Any, List, Literal, Optional, TypedDict

import pandas as pd


class ChatTurn(TypedDict):
    """One prior turn of conversation, used for follow-up questions."""

    role: Literal["user", "assistant"]
    content: str


class SchemaInfo(TypedDict, total=False):
    """Trimmed-down schema context handed to the SQL Generator.

    Populated by the Schema Agent. Only the tables/columns relevant to the
    current question should be included -- not the whole database -- to
    keep prompts small and avoid hallucinated joins.
    """

    relevant_tables: List[str]
    table_ddl: str  # CREATE TABLE-style text for the relevant tables only
    primary_keys: dict
    foreign_keys: dict


class ValidationResult(TypedDict, total=False):
    """Output of the SQL Validator Agent."""

    is_valid: bool
    is_read_only: bool
    errors: List[str]  # human-readable reasons for rejection, if any


class ExecutionResult(TypedDict, total=False):
    """Output of the Execute SQL Agent."""

    success: bool
    dataframe: Optional[pd.DataFrame]
    row_count: int
    execution_time_seconds: float
    error_message: Optional[str]


class GraphState(TypedDict, total=False):
    """The full state object threaded through the LangGraph workflow.

    `total=False` so each node only needs to set the keys it's
    responsible for; LangGraph merges partial updates into this dict
    between node calls.
    """

    
    user_query: str
    conversation_history: List[ChatTurn]

    # Connection context
    db_type: str

    #Planner Agent output
    intent: Literal[
        "data_retrieval",
        "aggregation",
        "analytics",
        "schema_info",
        "metadata",
        "table_explanation",
        "database_info",
    ]
    required_agents: List[str]

    # Schema Agent output
    schema_info: SchemaInfo

    #SQL Generator Agent output
    generated_sql: str

    #SQL Validator Agent output
    validation_result: ValidationResult

    #Execute SQL Agent output
    execution_result: ExecutionResult

    #Retry loop bookkeeping
    retry_count: int
    max_retries: int
    last_error: Optional[str]

    #Response Agent output
    final_response: str

    #Misc / observability
    agent_trace: List[str] 
