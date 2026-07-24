"""Repositories — the ONLY layer allowed to talk SQL.

The Repository pattern: each table gets one module with plain-Python
functions (add_topic, list_topics...). The rest of the app calls those
functions and never writes SQL. If we ever swap SQLite for PostgreSQL,
only this folder changes.
"""
