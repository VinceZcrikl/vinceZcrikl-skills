# VinceZcrikl-skills

An open-source collection of Agent Skills for AI assistants. Each skill is a self-contained folder with a `SKILL.md` file that teaches the agent how to complete specialized tasks — from file search to document generation.

## Skills

**System & Productivity**

- **[everything-search](./skills/everything-search)** `[Windows only]` — Instant file search powered by [Everything (voidtools)](https://www.voidtools.com). Find any file by name, extension, size, date, or path in milliseconds. Accepts natural language or raw Everything query syntax.

**Engineering & IP**

- **[patent-builder](./skills/patent-builder)** — Discover patentable ideas, refine early concepts, analyze implementations for patent potential, and draft patent disclosure materials. Supports English and Chinese. Three entry modes: existing implementation, initial idea, or open exploration.

## Installation

### Register as a plugin marketplace

```
/plugin marketplace add VinceZcrikl/VinceZcrikl-skills
```

### Install via git clone

Personal install (available in all projects):

```bash
git clone https://github.com/VinceZcrikl/VinceZcrikl-skills.git "%USERPROFILE%\.claude\skills\VinceZcrikl-skills"
```

Project install (current project only):

```bash
git clone https://github.com/VinceZcrikl/VinceZcrikl-skills.git ".claude\skills\VinceZcrikl-skills"
```

## Resources

- [Agent Skills specification](./spec/agent-skills-spec.md)

## License

MIT
