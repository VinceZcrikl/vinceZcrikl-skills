---
name: hermes-plugin-builder
description: Build Hermes Agent plugins from idea to working implementation. Use when the user wants to create, scaffold, package, debug, enable, or distribute a Hermes plugin with tools, hooks, slash commands, CLI commands, bundled skills, data files, or specialized plugin types such as platform/model/memory/context/image backends. / 用于从需求到可运行实现构建 Hermes Agent 插件，覆盖目录结构、plugin.yaml、register(ctx)、工具 schema/handler、hook、命令、技能打包、调试、启用与分发。
---

# Hermes Plugin Builder

## Language

If the user writes in Chinese, answer in Chinese. Keep code, file names, config keys, and CLI commands exactly as shown.

## Overview

Use this skill to build Hermes Agent plugins without modifying Hermes core. A Hermes plugin is a directory or Python package that Hermes discovers at startup. It can register LLM-callable tools, lifecycle hooks, slash commands, terminal CLI commands, bundled skills, platform adapters, model providers, memory providers, context engines, image-generation providers, and more.

For most custom integrations, prefer a plugin over editing core files under `tools/`, `toolsets.py`, or `model_tools.py`. Core-tool development is for built-in Hermes contributions; plugins are the normal path for personal, team, project, or distributed extensions.

## When to Use

Use this skill when the user asks to:

- Build a custom Hermes tool without changing Hermes core.
- Create a plugin directory under `~/.hermes/plugins/<name>/`, `.hermes/plugins/<name>/`, or a repo `plugins/<category>/<name>/`.
- Write `plugin.yaml`, `__init__.py`, `schemas.py`, `tools.py`, or plugin test prompts.
- Register `ctx.register_tool`, `ctx.register_hook`, `ctx.register_command`, `ctx.register_cli_command`, `ctx.register_skill`, `ctx.dispatch_tool`, or specialized provider/platform registrations.
- Package a plugin for pip using `[project.entry-points."hermes_agent.plugins"]`.
- Debug plugin discovery, enablement, missing env vars, hook failures, or handler/schema issues.

Do not use this skill as the primary guide for:

- Adding a built-in core Hermes tool shipped in `tools/` and `toolsets.py` — use Hermes contributor/tooling docs.
- Pure MCP integration — declare `mcp_servers.<name>` in config instead.
- TTS/STT command backends — configure command templates in `config.yaml` or env vars.
- Gateway event hooks that are not Python plugins — use `~/.hermes/hooks/<name>/HOOK.yaml` + `handler.py`.

## Extension Surface Decision Map

Choose the right surface before writing code:

- **LLM-callable tool:** general Python plugin using `ctx.register_tool()`.
- **Lifecycle hook:** general Python plugin using `ctx.register_hook("event", callback)`.
- **In-session slash command:** general Python plugin using `ctx.register_command("name", handler, description=...)`.
- **Terminal command `hermes <plugin>`:** general Python plugin using `ctx.register_cli_command(...)`.
- **Bundled plugin skill:** `ctx.register_skill(skill_name, path_to_skill_md)`; loaded as `skill_view("plugin:skill")`.
- **Gateway platform:** `plugins/platforms/<name>/` with `ctx.register_platform(...)` and `kind: platform`.
- **Image generation backend:** `plugins/image_gen/<name>/` with `ctx.register_image_gen_provider(...)`.
- **Memory backend:** `plugins/memory/<name>/` subclassing `MemoryProvider`; single active provider selected in config.
- **Context engine:** `plugins/context_engine/<name>/` subclassing `ContextEngine`; single active engine selected in config.
- **LLM/model provider:** `plugins/model-providers/<name>/` registering a `ProviderProfile`.
- **External server tools:** MCP, not a Python plugin.
- **Shell notification/audit hooks:** `hooks:` in `config.yaml`, not necessarily a plugin.

## Plugin Discovery and Enablement

Hermes discovers plugins from these sources:

- **Bundled:** `<hermes-repo>/plugins/`
- **User:** `~/.hermes/plugins/`
- **Project:** `./.hermes/plugins/` when `HERMES_ENABLE_PROJECT_PLUGINS=true`
- **Pip:** packages exposing the `hermes_agent.plugins` entry point
- **Nix:** `services.hermes-agent.extraPlugins` or `extraPythonPackages`

General third-party plugins are opt-in. Discovery finds them, but Hermes does not run arbitrary plugin code until enabled.

Enable/disable:

```bash
hermes plugins list
hermes plugins enable <plugin-name>
hermes plugins disable <plugin-name>
hermes plugins
```

Equivalent config shape:

```yaml
plugins:
  enabled:
    - my-plugin
  disabled:
    - noisy-plugin
```

Important distinctions:

- `enabled`: loaded next session.
- `disabled`: explicitly off, wins over enabled.
- `not enabled`: discovered but not opted in.
- Bundled platform/backend infrastructure may auto-load differently; user-installed general plugins still need explicit enablement.
- Restart Hermes or start a new session after enabling a plugin.

## Standard General Plugin Layout

Use this layout for most plugins:

```text
~/.hermes/plugins/my-plugin/
├── plugin.yaml      # manifest: name/version/description/provides/requires_env
├── __init__.py      # register(ctx): wires schemas to handlers and hooks
├── schemas.py       # JSON schemas the LLM sees
├── tools.py         # handler implementations
├── data/            # optional shipped data files
└── skills/          # optional bundled plugin skills
    └── my-workflow/
        └── SKILL.md
```

Project-local equivalent:

```text
<project>/.hermes/plugins/my-plugin/
```

Enable project-local plugin discovery only for trusted repos:

```bash
HERMES_ENABLE_PROJECT_PLUGINS=true hermes
```

## Build Workflow

### Step 1 — Clarify the plugin contract

Before coding, define:

- Plugin name: kebab-case directory name and manifest name.
- Target source: user plugin, project plugin, bundled plugin, or pip package.
- Capabilities: tools, hooks, slash commands, CLI commands, bundled skills, data files, or specialized backend.
- Required credentials/env vars.
- Tool inputs/outputs and error cases.
- Verification prompts or commands.

If the user only gives an idea, ask at most one concise question if the target capability is unclear. Otherwise choose the standard general plugin pattern.

### Step 2 — Create the directory

```bash
mkdir -p ~/.hermes/plugins/my-plugin
cd ~/.hermes/plugins/my-plugin
```

For project-local plugins:

```bash
mkdir -p .hermes/plugins/my-plugin
```

For bundled Hermes repo plugins, use the matching category under `plugins/`.

### Step 3 — Write `plugin.yaml`

Minimal manifest:

```yaml
name: my-plugin
version: 1.0.0
description: Concise description of what this plugin adds
provides_tools:
  - my_tool
provides_hooks:
  - post_tool_call
```

Useful optional fields:

```yaml
author: Your Name
requires_env:
  - SIMPLE_API_KEY
  - name: RICH_API_KEY
    description: "API key for the external service"
    url: "https://example.com/api-keys"
    secret: true
```

For platform plugins, use `kind: platform`. For model providers, use `kind: model-provider`. For image/backend-style plugins, use the appropriate documented kind, commonly `backend`.

### Step 4 — Write tool schemas in `schemas.py`

Schemas are what the LLM reads to decide whether and how to call a tool. Make descriptions specific.

```python
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
```

Schema rules:

- `name` must match the registered tool name.
- `description` must be precise; vague descriptions cause bad tool selection.
- `parameters` should be normal JSON Schema object shape.
- Require only fields that are truly required.
- Prefer constrained enums when the operation has a fixed set of modes.

### Step 5 — Write handlers in `tools.py`

Handlers execute when the LLM calls the tool.

```python
"""Tool handlers — code that runs on tool calls."""

import json


def my_tool(args: dict, **kwargs) -> str:
    """Run the operation and always return a JSON string."""
    query = (args.get("query") or "").strip()
    if not query:
        return json.dumps({"success": False, "error": "Missing query"})

    try:
        # Do work here.
        data = {"echo": query}
        return json.dumps({"success": True, "data": data})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})
```

Handler contract:

1. Signature: `def handler(args: dict, **kwargs) -> str`.
2. Always return a JSON string, including errors.
3. Catch exceptions and encode them as error JSON.
4. Accept `**kwargs` for forward compatibility.
5. Do not return raw dicts.
6. Do not modify unrelated files or run destructive actions unless explicitly intended and guarded.

### Step 6 — Register everything in `__init__.py`

```python
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

    ctx.register_hook("post_tool_call", _on_post_tool_call)

    # Optional: bundled skills, loaded as skill_view("my-plugin:skill-name").
    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.exists():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                ctx.register_skill(child.name, skill_md)
```

`register(ctx)` APIs commonly used:

- `ctx.register_tool(name, toolset, schema, handler, check_fn=None, ...)`
- `ctx.register_hook(event_name, callback)`
- `ctx.register_command(name, handler, description="")`
- `ctx.register_cli_command(name, help, setup_fn, handler_fn)`
- `ctx.register_skill(skill_name, skill_md_path)`
- `ctx.dispatch_tool(name, args, parent_agent=None)`
- `ctx.llm.complete(...)` or `ctx.llm.complete_structured(...)` for host-owned one-shot LLM calls, when available in the installed Hermes version.

If `register()` crashes, the plugin is disabled and Hermes continues. Keep registration minimal and defensive.

## Slash Commands

Use slash commands for in-session commands in CLI and gateways such as Telegram.

```python
def _handle_status(raw_args: str) -> str:
    if raw_args.strip() == "help":
        return "Usage: /mystatus [help]"
    return "Plugin status: ok"


def register(ctx):
    ctx.register_command(
        "mystatus",
        handler=_handle_status,
        description="Show plugin status",
    )
```

Rules:

- Name has no leading `/`.
- Handler receives the raw string after the command name.
- Handler may be sync or async.
- Built-in command names take precedence; conflicts are rejected and logged.
- The command appears in autocomplete/help/Telegram bot menu after plugin load.

### Dispatch tools from slash commands

Use `ctx.dispatch_tool()` instead of private framework internals when a slash command needs tool orchestration.

```python
def register(ctx):
    def _handle_scan(raw_args: str):
        return ctx.dispatch_tool(
            "terminal",
            {"command": f"python -m pytest {raw_args}"},
        )

    ctx.register_command(
        "scan",
        handler=_handle_scan,
        description="Run a terminal-backed scan",
    )
```

`ctx.dispatch_tool()` goes through normal approval, redaction, budget, and parent-agent context wiring.

## CLI Subcommands

Use CLI subcommands for terminal-only management surfaces like `hermes my-plugin status`.

```python
def _my_command(args):
    sub = getattr(args, "my_plugin_command", None)
    if sub == "status":
        print("All good")
    else:
        print("Usage: hermes my-plugin status")


def _setup_argparse(subparser):
    subs = subparser.add_subparsers(dest="my_plugin_command")
    subs.add_parser("status", help="Show plugin status")
    subparser.set_defaults(func=_my_command)


def register(ctx):
    ctx.register_cli_command(
        name="my-plugin",
        help="Manage my plugin",
        setup_fn=_setup_argparse,
        handler_fn=_my_command,
    )
```

Use `register_command()` for `/name` in a chat session; use `register_cli_command()` for `hermes name` in a shell.

## Hooks

Plugin hooks observe or influence lifecycle events. Common hooks:

- `pre_tool_call`: before any tool executes.
- `post_tool_call`: after any tool returns.
- `pre_llm_call`: once per turn before the LLM loop; may inject context.
- `post_llm_call`: after a successful LLM turn.
- `on_session_start`: first turn of a new session.
- `on_session_end`: end of `run_conversation` and CLI exit.
- `on_session_finalize`: CLI/gateway tears down an active session.
- `on_session_reset`: gateway swaps in a new session key.
- `subagent_stop`: after a delegated child agent finishes.
- `pre_gateway_dispatch`: before gateway auth/dispatch; can allow, rewrite, or skip.

Hook rules:

- Accept `**kwargs` for forward compatibility.
- Never let hooks crash; catch and log exceptions.
- Most hook return values are ignored.
- `pre_llm_call` can return `{"context": "..."}` or a non-empty string to append context to the current user message.
- Injected hook context is appended to the user message, not the system prompt, preserving prompt caching.
- Multiple context-returning plugins are joined with double newlines in discovery order.

Example `pre_llm_call` context injection:

```python
def inject_context(session_id=None, user_message=None, is_first_turn=False, **kwargs):
    if not user_message:
        return None
    return {"context": "Additional plugin context for this turn only."}


def register(ctx):
    ctx.register_hook("pre_llm_call", inject_context)
```

## Bundled Skills

Plugins can ship skills without copying them into `~/.hermes/skills/`.

Layout:

```text
my-plugin/
├── __init__.py
├── plugin.yaml
└── skills/
    ├── my-workflow/
    │   └── SKILL.md
    └── my-checklist/
        └── SKILL.md
```

Registration:

```python
from pathlib import Path


def register(ctx):
    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)
```

Loading behavior:

- Load with `skill_view("my-plugin:my-workflow")`.
- Bare `skill_view("my-workflow")` still resolves to the normal installed/built-in skill if present.
- Plugin skills are read-only from the skill manager.
- Plugin skills do not appear in the system prompt `<available_skills>` index.
- Namespace prevents collisions with built-in or user skills.

Avoid the legacy pattern that copies plugin skills into `~/.hermes/skills/`; it risks collisions.

## Data Files

Ship static data under the plugin directory and read relative to `__file__`.

```python
from pathlib import Path
import yaml

_PLUGIN_DIR = Path(__file__).parent
_DATA_FILE = _PLUGIN_DIR / "data" / "languages.yaml"

with open(_DATA_FILE, "r", encoding="utf-8") as f:
    DATA = yaml.safe_load(f)
```

Do not assume the process working directory. Always resolve paths relative to the plugin file.

## Environment Variables and Optional Requirements

Gate plugins or tools on credentials:

```yaml
requires_env:
  - name: WEATHER_API_KEY
    description: "API key for OpenWeather"
    url: "https://openweathermap.org/api"
    secret: true
```

Runtime behavior:

- Missing env vars disable the plugin with a clear message.
- `hermes plugins install` prompts for missing env vars and can save them to `.env`.
- Already-set env vars are skipped.

For optional libraries, hide a single tool instead of disabling the whole plugin:

```python
def _has_optional_lib():
    try:
        import some_package  # noqa: F401
        return True
    except Exception:
        return False


def register(ctx):
    ctx.register_tool(
        name="optional_tool",
        toolset="my_plugin",
        schema={...},
        handler=optional_handler,
        check_fn=_has_optional_lib,
    )
```

## Specialized Plugin Types

### Model provider plugins

Use this when adding an LLM backend/inference provider.

```text
plugins/model-providers/acme/
├── __init__.py
└── plugin.yaml
```

```python
from providers import register_provider
from providers.base import ProviderProfile

register_provider(ProviderProfile(
    name="acme",
    aliases=("acme-inference",),
    display_name="Acme Inference",
    env_vars=("ACME_API_KEY", "ACME_BASE_URL"),
    base_url="https://api.acme.example.com/v1",
    auth_type="api_key",
    default_aux_model="acme-small-fast",
    fallback_models=("acme-large-v3", "acme-medium-v3"),
))
```

```yaml
name: acme-provider
kind: model-provider
version: 1.0.0
description: Acme Inference — OpenAI-compatible direct API
```

Provider profiles are lazily discovered when provider lookup runs.

### Platform plugins

Use this when adding a gateway channel.

```python
from gateway.platforms.base import BasePlatformAdapter

class MyPlatformAdapter(BasePlatformAdapter):
    async def connect(self): ...
    async def send(self, chat_id, text): ...
    async def disconnect(self): ...


def check_requirements():
    import os
    return bool(os.environ.get("MYPLATFORM_TOKEN"))


def _env_enablement():
    import os
    tok = os.getenv("MYPLATFORM_TOKEN", "").strip()
    if not tok:
        return None
    return {"token": tok}


def register(ctx):
    ctx.register_platform(
        name="myplatform",
        label="MyPlatform",
        adapter_factory=lambda cfg: MyPlatformAdapter(cfg),
        check_fn=check_requirements,
        required_env=["MYPLATFORM_TOKEN"],
        env_enablement_fn=_env_enablement,
        cron_deliver_env_var="MYPLATFORM_HOME_CHANNEL",
        emoji="💬",
        platform_hint="You are chatting via MyPlatform. Keep responses concise.",
    )
```

```yaml
name: myplatform-platform
label: MyPlatform
kind: platform
version: 1.0.0
description: MyPlatform gateway adapter
requires_env:
  - name: MYPLATFORM_TOKEN
    description: "Bot token from the MyPlatform console"
    password: true
optional_env:
  - name: MYPLATFORM_HOME_CHANNEL
    description: "Default channel for cron delivery"
    password: false
```

### Memory provider plugins

Use this when replacing or extending cross-session memory.

```python
from agent.memory_provider import MemoryProvider

class MyMemoryProvider(MemoryProvider):
    @property
    def name(self) -> str:
        return "my-memory"

    def is_available(self) -> bool:
        import os
        return bool(os.environ.get("MY_MEMORY_API_KEY"))

    def initialize(self, session_id: str, **kwargs) -> None:
        self._session_id = session_id

    def sync_turn(self, user_message, assistant_response, **kwargs) -> None:
        ...

    def prefetch(self, query: str, **kwargs) -> str | None:
        ...


def register(ctx):
    ctx.register_memory_provider(MyMemoryProvider())
```

Memory providers are single-select via `memory.provider`.

### Context engine plugins

Use this when replacing context compression.

```python
from agent.context_engine import ContextEngine

class MyContextEngine(ContextEngine):
    @property
    def name(self) -> str:
        return "my-engine"

    def should_compress(self, messages, model) -> bool: ...
    def compress(self, messages, model) -> list[dict]: ...


def register(ctx):
    ctx.register_context_engine(MyContextEngine())
```

Context engines are single-select via `context.engine`.

### Image generation plugins

Use this when adding an image-generation backend.

```python
from agent.image_gen_provider import ImageGenProvider

class MyImageGenProvider(ImageGenProvider):
    @property
    def name(self) -> str:
        return "my-imggen"

    def is_available(self) -> bool: ...
    def generate(self, prompt: str, **kwargs) -> str: ...  # returns image path


def register(ctx):
    ctx.register_image_gen_provider(MyImageGenProvider())
```

```yaml
name: my-imggen
kind: backend
version: 1.0.0
description: Custom image generation backend
```

## Distribution

### Pip distribution

Add an entry point:

```toml
[project.entry-points."hermes_agent.plugins"]
my-plugin = "my_plugin_package"
```

Install:

```bash
pip install hermes-plugin-my-plugin
```

Hermes discovers the plugin on next startup.

### NixOS distribution

Entry-point package:

```nix
services.hermes-agent.extraPythonPackages = [
  (pkgs.python312Packages.buildPythonPackage {
    pname = "my-plugin";
    version = "1.0.0";
    src = pkgs.fetchFromGitHub {
      owner = "you";
      repo = "hermes-my-plugin";
      rev = "v1.0.0";
      hash = "sha256-...";
    };
    format = "pyproject";
    build-system = [ pkgs.python312Packages.setuptools ];
  })
];
```

Directory plugin:

```nix
services.hermes-agent.extraPlugins = [
  (pkgs.fetchFromGitHub {
    owner = "you";
    repo = "hermes-my-plugin";
    rev = "v1.0.0";
    hash = "sha256-...";
  })
];
```

## Testing and Debugging

### Basic smoke test

Start Hermes:

```bash
hermes
```

Expected:

- Plugin tools appear in the banner/tool list.
- `/plugins` shows the plugin loaded.
- Test prompts trigger the intended tool.

Example prompts:

```text
Use <tool purpose> on this input: ...
Run /<slash-command> status
```

### Discovery debug logs

If the plugin is missing or not loading:

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list
```

Look for:

- Scanned plugin directories.
- Manifest parse errors.
- Resolved plugin key/name/kind/source/path.
- Skip reasons such as `disabled via config`, `not enabled in config`, `exclusive plugin`, `no plugin.yaml`, or depth cap.
- Import/registration tracebacks.
- Registration summary: tools/hooks/commands/skills.

Logs also appear in Hermes logs:

```bash
hermes logs --level WARNING | grep -i plugin
```

Profile-specific note: when debugging a gateway profile, run commands with the same profile, e.g. `hermes -p coder plugins list`, and inspect that profile's logs/config.

### Common reasons a plugin does not appear

- Directory is too deep. General plugins must be `~/.hermes/plugins/<plugin-name>/plugin.yaml` or one category level where supported.
- Missing `plugin.yaml`.
- Missing `__init__.py` with `register(ctx)`.
- Manifest YAML syntax error.
- Plugin discovered but not enabled.
- Plugin is in `plugins.disabled`.
- Wrong `kind` for a specialized plugin.
- Required env vars are missing.
- `register()` imports optional dependencies at top level and crashes.
- Current Hermes process was not restarted after enabling or editing the plugin.

### Handler/schema problems

Symptoms and fixes:

- Model never calls the tool → improve schema `description`; check tool is enabled and visible.
- Tool call fails → handler likely raised or returned invalid data; catch exceptions and return JSON string.
- Tool output unreadable → return consistent `success`, `data`, and `error` keys.
- Future Hermes update breaks handler → handler did not accept `**kwargs`.
- Slash command conflicts → rename; built-in commands win.

## Common Mistakes

1. **Returning a dict from a handler.** Return `json.dumps(...)` instead.
2. **Omitting `**kwargs`.** Hermes may pass more context later.
3. **Letting exceptions escape.** Catch and encode errors in JSON.
4. **Vague schema descriptions.** The model needs exact use cases and supported inputs.
5. **Assuming plugins auto-run after discovery.** Enable general plugins explicitly.
6. **Editing a plugin while Hermes is running and expecting instant reload.** Restart or start a new session.
7. **Using process working directory for data files.** Use `Path(__file__).parent`.
8. **Copying bundled skills into `~/.hermes/skills/`.** Prefer `ctx.register_skill()` to avoid collisions.
9. **Putting credentials in code or `plugin.yaml`.** Use `.env` and `requires_env`.
10. **Using private context internals.** Use public APIs such as `ctx.dispatch_tool()`.

## Verification Checklist

Before calling the plugin done, verify:

- [ ] Chosen extension surface is correct.
- [ ] Directory contains `plugin.yaml` and `__init__.py`.
- [ ] `plugin.yaml` parses and has name/version/description.
- [ ] Every registered tool has a specific schema and matching handler.
- [ ] Every handler uses `def handler(args: dict, **kwargs) -> str`.
- [ ] Every handler returns a JSON string for success and error.
- [ ] Hooks accept `**kwargs` and do not crash the agent.
- [ ] Env vars are declared under `requires_env` when needed.
- [ ] Data files are read relative to `Path(__file__).parent`.
- [ ] Plugin is enabled with `hermes plugins enable <name>` if it is a general plugin.
- [ ] `HERMES_PLUGINS_DEBUG=1 hermes plugins list` shows expected discovery/loading behavior.
- [ ] `/plugins` in a running session shows the plugin loaded.
- [ ] At least one realistic prompt or slash command has been tested.

## One-Shot Scaffold Recipe

For a simple tool plugin named `my-plugin` with one tool named `my_tool`:

```bash
PLUGIN_DIR="$HOME/.hermes/plugins/my-plugin"
mkdir -p "$PLUGIN_DIR"
```

Create:

- `plugin.yaml` using the manifest template.
- `schemas.py` using the schema template.
- `tools.py` using the handler template.
- `__init__.py` using the registration template.

Then run:

```bash
python -m py_compile "$PLUGIN_DIR"/*.py
hermes plugins enable my-plugin
HERMES_PLUGINS_DEBUG=1 hermes plugins list
hermes
```

Inside Hermes:

```text
/plugins
Use my_tool to process: hello world
```
