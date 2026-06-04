# Orchestrator Team

Minimal overhead, maximum control — a multi-agent orchestration framework that gets out of your way.

> **93% token reduction** vs naive multi-agent approaches. Filesystem isolation eliminates file conflicts. Zero-LLM quality gates catch bad output before it costs you.

<p align="center">
  <a href="https://pypi.org/project/orchestrator-team/"><img src="https://img.shields.io/pypi/v/orchestrator-team?color=blue" alt="PyPI"></a>
  <a href="https://www.npmjs.com/package/orchestrator-team"><img src="https://img.shields.io/npm/v/orchestrator-team?color=red" alt="npm"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
</p>

---

## Why

<blockquote>
  <strong>The problem:</strong> Running 5 agents in parallel often gives you 5 copies of <code>models.py</code> overwriting each other, 40% of agents producing nothing useful, and a token bill approaching 1M.
</blockquote>

**Orchestrator Team** is a thin orchestration layer between you and your agents. It doesn't define your workflow — it runs *your* workflow, with three guarantees:

1. **Isolated workspaces** — Physical directory per agent. No merge conflicts by construction.
2. **Pre-check** — Filter unwinnable tasks before execution. No tokens wasted on agents with unmet dependencies.
3. **Quality gates** — Mechanical checks on output (file exists, non-empty, no duplicates). Zero LLM cost.

## Benchmarks

Three real projects, measured:

| Project | Baseline (multi-agent) | OT v3.0 | Delta |
|---|---|---|---|
| E-commerce (8 services) | 826K tokens / 100 min | 55.6K / 11 min | **-93% token, -89% time** |
| Tower defense (10 modules) | — | 79.8K / 13 min | 100% success rate |
| Collaborative docs (8 modules) | — | 55.6K / 11 min | 0 duplicate files |

## Install

```bash
pip install orchestrator-team
# or
npm install -g orchestrator-team
```

## Quick start

```python
from orchestrator_team import Orchestrator, TaskDef, TaskResult

async def my_agent(task: TaskDef, workspace_dir: str, context: str) -> TaskResult:
    """Your agent executor. Call any LLM you want."""
    with open(f"{workspace_dir}/{task.id}.py", "w") as f:
        f.write(f"# {task.description}")
    return TaskResult(
        task_id=task.id,
        status="COMPLETED",
        files_created=[f"{task.id}.py"],
    )

tasks = [
    TaskDef("models", "Data Models", role="engineer",
            description="Define User/Post/Comment models"),
    TaskDef("api", "API Layer", role="engineer",
            description="REST endpoints", dependencies=["models"]),
    TaskDef("tests", "Tests", role="tester",
            description="Unit tests", dependencies=["api"]),
]

orch = Orchestrator(agent_executor=my_agent)
result = await orch.run(tasks, "./output")
```

### YAML pipeline

```yaml
name: my-project
config:
  max_parallelism: 4

nodes:
  - id: models
    config:
      role: engineer
      task: "Define data models"
  - id: api
    config:
      role: engineer
      task: "Build API layer"
      depends_on: [models]
```

```bash
npx orchestrator-team run workflow.yaml
```

## How it works

```
  Task Pre-Check        Quality Gate          Context Pool
  (filter invalid)      (zero-LLM checks)     (3-layer cache)
       |                      |                     |
       v                      v                     v
  +------------------------------------------------------+
  |              Orchestrator Core                        |
  |   topo-sort -> dispatch -> verify -> merge           |
  +------------------------------------------------------+
       |              |               |
       v              v               v
  [Agent A]      [Agent B]       [Agent C]
  /tmp/a/        /tmp/b/         /tmp/c/
  (isolated)     (isolated)      (isolated)
```

Each agent writes to its own filesystem directory. A soft-link provides read-only access to dependencies. After execution, the orchestrator collects all outputs, runs quality checks, and merges into a single output directory with conflict resolution.

## Comparison

|                        | CrewAI | AutoGen | LangGraph | **OT** |
|------------------------|:------:|:-------:|:---------:|:------:|
| Filesystem isolation   |        |         |           |   ✓    |
| Pre-execution filtering|        |         |           |   ✓    |
| Quality gates          | partial|         |           |   ✓    |
| Shared context cache   |        |         |           |   ✓    |
| Token efficiency       |  low   |   mid   |    mid    |  high  |
| Zero framework lock-in |        |         |           |   ✓    |

## Project structure

```
orchestrator-team/
  orchestrator_team/     # Python package
    orchestrator.py      # Core event loop
    workspace.py         # Filesystem isolation
    pre_checker.py       # Task validation
    quality_gate.py      # Output verification
    context_pool.py      # Shared prompt cache
    benchmark.py         # Benchmarking toolkit
  cli/                   # Node.js CLI
    index.js
  examples/
    simple_example.py
    workflow.yaml
  pyproject.toml
  package.json
```

## Philosophy

Orchestrator Team is deliberately minimal. It does not:

- Ship with pre-built agents or "roles"
- Lock you into a specific LLM provider
- Require Docker, Kubernetes, or any infrastructure beyond Python
- Add framework taxes to your token consumption

It gives you **isolation, validation, and reliability** — the three things every multi-agent system needs and most frameworks miss. You bring your models, your prompts, your logic. OT makes sure they don't step on each other.

## Contact

Issues and PRs: [github.com/thefort827/orchestrator-team](https://github.com/thefort827/orchestrator-team)

Email: [1759799340@qq.com](mailto:1759799340@qq.com)

## License

MIT
