"""Tool schemas — what the LLM sees."""

MY_TOOL = {
    "name": "my_tool",
    "description": (
        "Do a specific operation. Use when the user asks to ... "
        "Returns structured JSON with success/data or error."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The query or instruction to process",
            },
        },
        "required": ["query"],
    },
}
