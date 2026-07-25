🧠 Gen AI Chatbot with SQL Database

This project is a Generative AI-powered chatbot that can interact with a PostgreSQL database using natural language queries.
The chatbot allows users to ask questions in plain English, and it automatically translates them into SQL queries, executes them, and returns the results in a conversational format.


⚡ Features

-> 💬 Natural Language to SQL – Ask database-related questions in plain English.

-> 🗄️ Database Integration – Works with PostgreSQL (tested on local + hosted DB).

-> 🎯 Dynamic Schema Understanding – Automatically inspects DB schema for intelligent query generation.

-> 🔒 Table Restriction (Optional) – Can limit access to specific tables during development.

-> 🖥️ Streamlit UI – Simple, interactive interface for chatting with the database.

-> 🤖 LLM-powered – Built using LangChain + Groq API (or any supported LLM).


🛠️ Tech Stack

-> Python 3.9+

-> LangChain (for LLM + SQL agent)

-> SQLAlchemy (for database connection)

-> PostgreSQL (as the SQL database)

-> Streamlit (for the web interface)