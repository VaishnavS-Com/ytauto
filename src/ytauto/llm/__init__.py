"""LLM access layer.

Same single-gateway pattern as database.py and http_client.py:
the rest of the app calls `generate_json(prompt)` and doesn't know or care
which model (or even which LLM server) sits behind it. Swap Ollama for a
cloud API later = change one file.
"""
