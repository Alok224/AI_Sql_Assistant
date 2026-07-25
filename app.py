"""
app.py

Streamlit entry point for the Agentic SQL Assistant.

This step replaces the LangChain create_sql_agent path with the LangGraph
multi-agent workflow (Planner -> Schema -> SQL Generator -> Validator ->
Execute -> Retry -> Response) built in graph/workflow.py, and adds the
SQL preview, results panel, downloads, and query history from the spec.

The Connection Management sidebar from the previous step is unchanged.
"""

import json
import logging
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from database import DEFAULT_PORTS, SUPPORTED_DB_TYPES, DatabaseConfig, DatabaseManager
from graph.workflow import build_graph

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="🦜🔗 Agentic SQL Assistant", layout="wide")
st.title("🦜🔗 Agentic SQL Assistant")

LLM_PROVIDERS = ["Groq"]


def init_session_state() -> None:
    """Ensures every session_state key this app relies on exists before use."""
    defaults = {
        "db_manager": None,
        "connection_status": "Disconnected",
        "connection_error": None,
        "messages": [{"role": "assistant", "content": "How can I help you today?"}],
        "query_history": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def log_query_event(
    user_query: str,
    db_type: str,
    generated_sql: str,
    execution_time: float,
    retry_count: int,
    error: str | None,
) -> None:
    """Writes the structured log line required by the spec."""
    logger.info(
        "QUERY | db_type=%s | retries=%d | exec_time=%.4fs | error=%s | "
        "question=%r | sql=%r",
        db_type,
        retry_count,
        execution_time,
        error,
        user_query,
        generated_sql,
    )


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="results")
    return buffer.getvalue()


init_session_state()

st.sidebar.header("LLM Configuration")
llm_provider = st.sidebar.selectbox("LLM Provider", LLM_PROVIDERS, index=0)
api_key = st.sidebar.text_input("API Key", type="password")

if not api_key:
    st.sidebar.warning("Enter an API key to enable the assistant.")


st.sidebar.header("Database Connection")

db_type = st.sidebar.selectbox("Database Type", SUPPORTED_DB_TYPES, index=0)

if db_type == "SQLite":
    host = username = password = None
    port = None
    database_value = st.sidebar.text_input("Database File Path", value="student_model.db")
else:
    host = st.sidebar.text_input("Host", value="localhost")
    port = st.sidebar.number_input(
        "Port", value=DEFAULT_PORTS.get(db_type) or 5432, step=1, format="%d"
    )
    username = st.sidebar.text_input(
        "Username", value="postgres" if db_type == "PostgreSQL" else ""
    )
    password = st.sidebar.text_input("Password", type="password")
    database_value = st.sidebar.text_input(
        "Database Name", value="student_model" if db_type == "PostgreSQL" else ""
    )

col_connect, col_disconnect = st.sidebar.columns(2)
connect_clicked = col_connect.button("Connect", use_container_width=True)
disconnect_clicked = col_disconnect.button("Disconnect", use_container_width=True)

if connect_clicked:
    config = DatabaseConfig(
        db_type=db_type,
        host=host,
        port=int(port) if port else None,
        username=username,
        password=password,
        database=database_value,
    )
    manager = DatabaseManager(config)
    try:
        manager.connect()
        st.session_state.db_manager = manager
        st.session_state.connection_status = "Connected"
        st.session_state.connection_error = None
    except Exception as exc:  # noqa: BLE001 - surfaced directly to the user
        st.session_state.db_manager = None
        st.session_state.connection_status = "Disconnected"
        st.session_state.connection_error = str(exc)
        logger.error("Connection failed: %s", exc)

if disconnect_clicked and st.session_state.db_manager is not None:
    st.session_state.db_manager.disconnect()
    st.session_state.db_manager = None
    st.session_state.connection_status = "Disconnected"
    st.session_state.connection_error = None

if st.session_state.connection_status == "Connected":
    st.sidebar.success(f"Status: Connected to {db_type}")
else:
    st.sidebar.error("Status: Disconnected")
    if st.session_state.connection_error:
        st.sidebar.caption(st.session_state.connection_error)


st.sidebar.header("Safety")
allow_write_ops = st.sidebar.checkbox(
    "Allow write operations (disable Read Only mode)",
    value=False,
    help="When unchecked, the Validator Agent rejects INSERT/UPDATE/DELETE/"
    "DROP/ALTER/TRUNCATE and similar statements before they ever run.",
)


if not api_key:
    st.info("Enter your LLM API key in the sidebar to get started.")
    st.stop()

if st.session_state.db_manager is None or not st.session_state.db_manager.is_connected:
    st.info("Configure your database in the sidebar and click 'Connect' to get started.")
    st.stop()

db = st.session_state.db_manager.sql_database
engine = st.session_state.db_manager.engine


llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=api_key, streaming=False)
workflow = build_graph(llm=llm, db=db, engine=engine, allow_write_ops=allow_write_ops)

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

prompt = st.chat_input(placeholder="Ask anything from the database")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    conversation_history = [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]
    ]

    initial_state = {
        "user_query": prompt,
        "conversation_history": conversation_history,
        "db_type": db_type,
        "retry_count": 0,
        "max_retries": 3,
        "agent_trace": [],
    }

    with st.chat_message("assistant"):
        with st.spinner("Working on it..."):
            try:
                result = workflow.invoke(initial_state)
            except Exception as exc:  # noqa: BLE001 - last-resort safety net
                logger.exception("Workflow crashed")
                result = {
                    "final_response": f"Something went wrong while processing that: {exc}",
                    "generated_sql": "",
                    "execution_result": {},
                    "retry_count": 0,
                }

        final_response = result.get("final_response", "I wasn't able to process that request.")
        generated_sql = result.get("generated_sql", "")
        execution_result = result.get("execution_result") or {}
        retry_count = result.get("retry_count", 0)

        st.write(final_response)

        if generated_sql:
            with st.expander("Generated SQL"):
                st.code(generated_sql, language="sql")

        df = execution_result.get("dataframe")
        if df is not None and not df.empty:
            col_a, col_b = st.columns(2)
            col_a.metric("Rows Returned", execution_result.get("row_count", 0))
            col_b.metric(
                "Execution Time", f"{execution_result.get('execution_time_seconds', 0):.3f}s"
            )
            st.dataframe(df, use_container_width=True)

            dl_col1, dl_col2, dl_col3 = st.columns(3)
            dl_col1.download_button(
                "Download CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="results.csv",
                mime="text/csv",
                use_container_width=True,
            )
            dl_col2.download_button(
                "Download Excel",
                dataframe_to_excel_bytes(df),
                file_name="results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            dl_col3.download_button(
                "Download JSON",
                df.to_json(orient="records", indent=2).encode("utf-8"),
                file_name="results.json",
                mime="application/json",
                use_container_width=True,
            )

        st.session_state.messages.append({"role": "assistant", "content": final_response})

        log_query_event(
            user_query=prompt,
            db_type=db_type,
            generated_sql=generated_sql,
            execution_time=execution_result.get("execution_time_seconds", 0.0),
            retry_count=retry_count,
            error=execution_result.get("error_message"),
        )

        st.session_state.query_history.append(
            {
                "question": prompt,
                "sql": generated_sql,
                "execution_time": execution_result.get("execution_time_seconds", 0.0),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "response": final_response,
            }
        )

if st.session_state.query_history:
    with st.expander(f"Query History ({len(st.session_state.query_history)})"):
        for item in reversed(st.session_state.query_history):
            st.markdown(f"**{item['timestamp']}** — {item['question']}")
            st.code(item["sql"], language="sql")
            st.caption(f"{item['execution_time']:.3f}s — {item['response']}")
            st.divider()
