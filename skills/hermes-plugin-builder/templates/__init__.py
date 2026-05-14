"""my-plugin — registration."""

import logging
from pathlib import Path

from . import schemas, tools

logger = logging.getLogger(__name__)


def _on_post_tool_call(tool_name, args, result, task_id=None, **kwargs):
    """Observer hook; never crash the agent."""
    try:
        logger.debug("Tool called: %s session=%s", tool_name, task_id)
    except Exception:
        logger.exception("post_tool_call hook failed")


def register(ctx):
    """Called once at startup to register plugin capabilities."""
    ctx.register_tool(
        name="my_tool",
        toolset="my_plugin",
        schema=schemas.MY_TOOL,
        handler=tools.my_tool,
    )

    # Optional hook; remove if unused.
    ctx.register_hook("post_tool_call", _on_post_tool_call)

    # Optional bundled skills: skill_view("my-plugin:skill-name").
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.exists():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                ctx.register_skill(child.name, skill_md)
