"""Tool handlers — code that runs when the LLM calls plugin tools."""

import json


def my_tool(args: dict, **kwargs) -> str:
    """Run the operation and always return a JSON string."""
    del kwargs  # remove this if you need task/session context later
    query = (args.get("query") or "").strip()
    if not query:
        return json.dumps({"success": False, "error": "Missing query"})

    try:
        data = {"echo": query}
        return json.dumps({"success": True, "data": data})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})
