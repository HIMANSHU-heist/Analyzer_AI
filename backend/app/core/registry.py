"""
In-memory registry that maps file_id -> {filepath, schema_summary}.

Step 1 (upload.py) should call `register_file()` right after a file is
successfully uploaded and its schema/stats are computed.

Step 2 (chat.py) calls `get_file_context()` to pull that same schema/stats
back out, so the LLM always knows exactly what dataset it's talking about.

NOTE: This is in-memory (dict), so it resets on server restart and won't
work across multiple worker processes. Fine for MVP/demo. For production,
swap this for Redis or a DB table — the function signatures below are the
only thing the rest of the app depends on, so the swap is a 1-file change.
"""

from typing import Dict, Optional

_registry: Dict[str, dict] = {}


def register_file(file_id: str, filepath: str, schema_summary: dict) -> None:
    _registry[file_id] = {
        "filepath": filepath,
        "schema_summary": schema_summary,
    }


def get_file_context(file_id: str) -> Optional[dict]:
    return _registry.get(file_id)


def list_files() -> Dict[str, dict]:
    return _registry
