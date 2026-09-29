# AI-Engineering-Team

A multi-agent AI software engineering team built with [crewAI](https://crewai.com). Give it a high-level set of requirements and four specialized agents design, implement, test, and build a Gradio UI for a self-contained Python application, working together in a shared sandbox.

![Python](https://img.shields.io/badge/python-3.10--3.13-blue)
![crewAI](https://img.shields.io/badge/crewAI-1.14.4-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Table of Contents

- [Overview](#overview)
- [The Team](#the-team)
- [Workflow](#workflow)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [Generated Output](#generated-output)
- [Customizing](#customizing)
- [CLI Scripts](#cli-scripts)
- [Design Constraints](#design-constraints)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## Overview

`AI-Engineering-Team` simulates a small software team. You pass in requirements (the `{requirements}` input), and the crew produces:

1. A markdown **design** document
2. A Python **backend** module
3. A Gradio **frontend** (`app.py`) with a validation script
4. A **unit test** file and a test summary

All agents work in one flat `sandbox/` directory, which is also a uv workspace member, and use sandbox tools to write, run, and check their code.

## The Team

| Agent | Model | Tools | Responsibility |
|-------|-------|-------|----------------|
| **Engineering Lead** | `openai/gpt-5.5` | Context7 MCP | Designs the system (modules, classes, function signatures, no code) and assigns work. Includes explicit Gradio 6 API guidance for the frontend engineer. |
| **Backend Engineer** | `openai/gpt-5.4-mini` | Sandbox tools | Implements the design in standard-library-only Python. Writes no UI code. |
| **Frontend Engineer** | `openai/gpt-5.4-mini` | Sandbox tools, Context7 MCP | Builds a single-file Gradio UI and a validation script. Uses the palette `#ecad0a` / `#209dd7` / `#753991` with grays, working in light and dark mode. |
| **Test Engineer** | `openai/gpt-5.4-mini` | Sandbox tools | Writes `unittest` tests, runs them, and fixes defects until they pass. |

## Workflow

The crew runs **sequentially** (`Process.sequential`), with tracing enabled.

```
requirements
     │
     ▼
design_task ──► code_task ──► frontend_task ──► test_task
(Eng. Lead)    (Backend)      (Frontend)        (Test Eng.)
     │                                              │
     ▼                                              ▼
sandbox/design.md                        sandbox/test_summary.md
```

| Task | Agent | Context | Output |
|------|-------|---------|--------|
| `design_task` | Engineering Lead | none | `sandbox/design.md` |
| `code_task` | Backend Engineer | `design_task` | Python module(s) in `sandbox/` |
| `frontend_task` | Frontend Engineer | `code_task`, `design_task` | `app.py` and `_validate.py` in `sandbox/` |
| `test_task` | Test Engineer | `code_task`, `design_task` | Unit test file and `sandbox/test_summary.md` |

Key behaviours:

- The validation script must import `app.py` and confirm the `Blocks` object constructs, and must **not** call `.launch()`.
- The test engineer keeps iterating until all tests pass, and must avoid changes that break `app.py`.

## Tech Stack

| Component | Details |
|-----------|---------|
| Language | Python `>=3.10, <3.14` |
| Framework | `crewai[tools]==1.14.4` |
| LLMs | OpenAI (`gpt-5.5` for the lead, `gpt-5.4-mini` for the engineers) |
| Docs lookup | [Context7](https://context7.com) MCP server (`https://mcp.context7.com/mcp`) |
| UI in generated apps | Gradio 6 |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Build backend | Hatchling |

## Repository Structure

```
AI-Engineering-Team/
├── src/
│   └── engineering_team/
│       ├── config/
│       │   ├── agents.yaml          # Agent roles, goals, backstories, LLMs
│       │   └── tasks.yaml           # Task definitions and context chaining
│       ├── tools/
│       │   └── sandbox_tools.py     # Sandbox tools used by the engineers
│       ├── crew.py                  # EngineeringTeam crew (@CrewBase)
│       └── main.py                  # Entry points and requirements input
├── sandbox/                         # Shared workspace for generated code (uv workspace member)
├── knowledge/                       # Knowledge base resources
├── AGENTS.md                        # crewAI reference for AI coding assistants
├── LICENSE
├── pyproject.toml
├── uv.lock
└── README.md
```

## Prerequisites

- Python 3.10 to 3.13
- [uv](https://docs.astral.sh/uv/)
- An OpenAI API key with access to the configured models
- Internet access (for the Context7 MCP server)

## Installation

```bash
git clone https://github.com/rajesh0411/AI-Engineering-Team.git
cd AI-Engineering-Team

pip install uv
crewai install        # or: uv sync
```

## Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
```

Do not commit `.env`. Because `tracing=True` is set in `crew.py`, you may be prompted to connect a crewAI account for traces; set it to `False` to disable.

## Running the Project

Set your requirements in `src/engineering_team/main.py` (the `requirements` input), then run:

```bash
crewai run
```

## Generated Output

After a run, look in `sandbox/`:

| File | Description |
|------|-------------|
| `design.md` | The engineering lead's design |
| Backend module(s) | Standard-library Python implementation |
| `app.py` | Gradio UI demonstrating the backend |
| `_validate.py` | Script confirming the UI constructs without error |
| Test file | `unittest` tests for the backend |
| `test_summary.md` | Summary of test results |

To try the generated app:

```bash
cd sandbox
uv run app.py
```

## Customizing

| Change | Where |
|--------|-------|
| Models per agent | `llm:` in `config/agents.yaml` |
| Agent instructions and constraints | `goal` / `backstory` in `config/agents.yaml` |
| Task prompts, outputs, context | `config/tasks.yaml` |
| Tools, MCP servers, process type, tracing | `crew.py` |
| Requirements to build | `main.py` |

To switch to a hierarchical process, replace `Process.sequential` with `Process.hierarchical` in `crew.py` and set a `manager_llm`.

## CLI Scripts

| Script | Target |
|--------|--------|
| `engineering_team`, `run_crew` | `engineering_team.main:run` |
| `train` | `engineering_team.main:train` |
| `replay` | `engineering_team.main:replay` |
| `test` | `engineering_team.main:test` |
| `run_with_trigger` | `engineering_team.main:run_with_trigger` |

## Design Constraints

Enforced through the agent and task prompts:

- All generated files live in one flat directory (no packages or subdirectories).
- Backend and tests use only the Python standard library; tests use `unittest`, not pytest.
- Gradio is the only third-party package available to generated code.
- The lead's design contains signatures only, with no code.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Authentication or model errors | Check `OPENAI_API_KEY` and access to `gpt-5.5` / `gpt-5.4-mini`, or change `llm:` in `agents.yaml` |
| Context7 tools unavailable | Check network access to `https://mcp.context7.com/mcp` |
| Gradio UI fails to build | Review `sandbox/_validate.py` output and `design.md` |
| Tracing prompt on run | Set `tracing=False` in `crew.py` |
| `Module not found` | Run `crewai install` and confirm the entry point is `src/engineering_team/main.py` |

## Contributing

Contributions are welcome. Fork the repo, create a feature branch, and open a pull request.

## License

Released under the [MIT License](LICENSE).

## Author

**Rajesh C**, [@rajesh0411](https://github.com/rajesh0411)

Built with [crewAI](https://crewai.com).
