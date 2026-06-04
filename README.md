<div align="center">

```
 ██████╗ ██████╗  ██████╗██╗  ██╗███████╗███████╗████████╗██████╗  █████╗ ████████╗ ██████╗ ██████╗ 
██╔═══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗
██║   ██║██████╔╝██║     ███████║█████╗  ███████╗   ██║   ██████╔╝███████║   ██║   ██║   ██║██████╔╝
██║   ██║██╔══██╗██║     ██╔══██║██╔══╝  ╚════██║   ██║   ██╔══██╗██╔══██║   ██║   ██║   ██║██╔══██╗
╚██████╔╝██║  ██║╚██████╗██║  ██║███████╗███████║   ██║   ██║  ██║██║  ██║   ██║   ╚██████╔╝██║  ██║
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
```

### 🎯 **T E A M**

**让多个 AI Agent 像真正的团队一样协作，而不是互相踩脚**

[![PyPI version](https://img.shields.io/pypi/v/orchestrator-team?style=flat-square&logo=pypi&color=3776AB)](https://pypi.org/project/orchestrator-team/)
[![npm version](https://img.shields.io/npm/v/orchestrator-team?style=flat-square&logo=npm&color=CB3837)](https://www.npmjs.com/package/orchestrator-team)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
[![Stars](https://img.shields.io/github/stars/thefort827/orchestrator-team?style=flat-square&color=yellow)](https://github.com/thefort827/orchestrator-team/stargazers)

[English](#english) | [中文](#中文)

</div>

---

<a name="中文"></a>

## 🤔 为什么需要它？

> 你试过让 5 个 AI Agent 一起写代码吗？结果通常是：5 个人都写了 models.py，互相覆盖，最后只剩一份。

现有框架的三个致命问题：

<table>
<tr>
<td width="50%">

### ❌ 现状

- Agent **互相覆盖文件**（5个Agent写了5份相同的models.py）
- **40% Agent在摸鱼**（消耗Token但0产出）
- 产出质量不可控（空文件、语法错误、占位符代码）
- Token消耗爆炸（一个项目烧掉800K tokens）

</td>
<td width="50%">

### ✅ Orchestrator Team

- **物理目录隔离**（每个Agent独立工作目录，不可能冲突）
- **任务预检器**（启动前过滤无效任务）
- **2层质量门禁**（零LLM成本，机械检查+产出校验）
- **Token效率提升93%**（826K → 55.6K）

</td>
</tr>
</table>

## 📊 实测数据

> 3轮基准测试，真实项目，真实消耗

| 测试项目 | 原版多智能体 | v3.0 | 改善 |
|---------|-------------|------|------|
| 🛒 电商平台（8微服务） | 826K tokens / 100min | 55.6K / 11min | **-93% token / -89% 时间** |
| 🎮 塔防游戏（10模块） | — | 79.8K / 13min | 100%成功率 |
| 📝 协作文档系统（8模块） | — | 55.6K / 11min | 0文件重复 |

<div align="center">

```
Token消耗对比
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v1.0 原版    ████████████████████████████  826K
v3.0 优化    ███                           55.6K  (-93%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</div>

## 🚀 快速开始

### 安装

```bash
# Python
pip install orchestrator-team

# Node.js CLI
npm install -g orchestrator-team
```

### 30秒示例

```python
import asyncio
from orchestrator_team import Orchestrator, TaskDef, TaskResult

# 1. 定义你的Agent执行器（在这里调用LLM）
async def my_agent(task: TaskDef, workspace_dir: str, context: str) -> TaskResult:
    # 调用你的LLM
    # response = await llm.chat(context)
    # 在 workspace_dir 中创建文件
    with open(f"{workspace_dir}/{task.id}.py", "w") as f:
        f.write(f"# {task.description}\n")
    return TaskResult(
        task_id=task.id, status="COMPLETED",
        files_created=[f"{task.id}.py"]
    )

# 2. 定义任务（支持依赖关系）
tasks = [
    TaskDef(id="models", name="数据模型", role="engineer",
            description="定义User/Post/Comment模型", dependencies=[]),
    TaskDef(id="api", name="API接口", role="engineer",
            description="开发RESTful API", dependencies=["models"]),
    TaskDef(id="tests", name="测试", role="tester",
            description="编写单元测试", dependencies=["api"]),
]

# 3. 运行编排
orch = Orchestrator(agent_executor=my_agent)
result = asyncio.run(orch.run(tasks, "./output"))
print(result.summary())
# → 编排完成: 3成功 / 0跳过 / 0失败 / 3文件
```

### YAML 工作流

```yaml
name: my-project
config:
  max_parallelism: 4
  budget:
    max_tokens: 300000

nodes:
  - id: models
    config:
      role: engineer
      task: "定义数据模型"
  - id: api
    config:
      role: engineer
      task: "开发API"
      depends_on: [models]
  - id: tests
    config:
      role: tester
      task: "编写测试"
      depends_on: [api]
```

```bash
npx orchestrator-team run workflow.yaml
```

## 🏗️ 架构

<div align="center">

```
┌─────────────────────────────────────────────────────────────┐
│                  🎯 Orchestrator Team v3.0                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐          │
│   │  📋 Task  │    │  ✅ Quality│    │  📦 Context│          │
│   │ Pre-Check │    │   Gate    │    │   Pool    │          │
│   │ (过滤无效)│    │ (零LLM)   │    │ (3层共享) │          │
│   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘          │
│         │                │                │                │
│         ▼                ▼                ▼                │
│   ┌─────────────────────────────────────────────────┐      │
│   │           🧠 Orchestrator Core                   │      │
│   │    拓扑排序 → 并行派发 → 产出校验 → 合并汇总    │      │
│   └───────────────────────┬─────────────────────────┘      │
│                           │                                │
│           ┌───────────────┼───────────────┐                │
│           ▼               ▼               ▼                │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│     │ 🤖 Agent │    │ 🤖 Agent │    │ 🤖 Agent │          │
│     │ /tmp/a/  │    │ /tmp/b/  │    │ /tmp/c/  │          │
│     │ (隔离)   │    │ (隔离)   │    │ (隔离)   │          │
│     └──────────┘    └──────────┘    └──────────┘          │
│           │               │               │                │
│           ▼               ▼               ▼                │
│   ┌─────────────────────────────────────────────────┐      │
│   │         📂 Isolated Workspace                    │      │
│   │   独立目录 + 只读软链接 + 自动合并 + 冲突处理   │      │
│   └─────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

</div>

## 🔑 核心特性

<table>
<tr>
<td width="50%">

### 🔒 物理目录隔离

每个Agent在**独立目录**中工作，物理上不可能互相覆盖文件。

```python
workspace = IsolatedWorkspace("/tmp/run-001")
dir_a = workspace.create_agent_dir("agent_a")
# agent_a 只能写自己的目录
# 其他Agent看不到也写不了
```

</td>
<td width="50%">

### 📋 任务预检器

启动前评估可行性，过滤"注定摸鱼"的任务。

```python
checker = TaskPreChecker()
result = checker.check(
    task_id="api",
    dependencies=["models"],
    completed_tasks={"models": {...}},
    remaining_budget=200000
)
# → PROCEED / SKIP / DOWNGRADE
```

</td>
</tr>
<tr>
<td width="50%">

### ✅ 质量门禁

2层检查，**零LLM成本**。

```python
gate = QualityGate()
result = gate.check(
    agent_id="api",
    workspace_dir="/tmp/run-001/api/"
)
# 文件存在？大小合理？语法正确？无重复？
```

</td>
<td width="50%">

### 📦 共享上下文池

3层缓存，避免重复加载系统提示词。

```python
pool = SharedContextPool()
pool.set_global_context(
    project_overview="电商平台",
    code_standards="Python 3.11+"
)
# Global → Role → Task，逐层叠加
```

</td>
</tr>
</table>

## 📈 与竞品对比

| 特性 | CrewAI | AutoGen | LangGraph | **Orchestrator Team** |
|------|:------:|:-------:|:---------:|:---------------------:|
| 物理目录隔离 | ❌ | ❌ | ❌ | ✅ |
| 任务预检 | ❌ | ❌ | ❌ | ✅ |
| 质量门禁 | ❌ | 部分 | ❌ | ✅ 零LLM |
| 共享上下文 | ❌ | ❌ | ❌ | ✅ 3层 |
| Token效率 | 低 | 中 | 中 | **高** |
| 学习曲线 | 中 | 高 | 高 | **低** |
| 外部依赖 | 多 | 多 | 多 | **少** |
| pip/npm 安装 | ✅ | ✅ | ✅ | ✅ |

## 📁 项目结构

```
orchestrator-team/
├── orchestrator_team/          # 🐍 Python 核心包
│   ├── __init__.py             #   pip install orchestrator-team
│   ├── orchestrator.py         #   编排器主循环
│   ├── workspace.py            #   物理目录隔离
│   ├── pre_checker.py          #   任务预检器
│   ├── quality_gate.py         #   质量门禁
│   ├── context_pool.py         #   共享上下文池
│   └── benchmark.py            #   基准测试工具
├── cli/                        # 📦 Node.js CLI
│   └── index.js                #   npx orchestrator-team
├── examples/                   # 📝 示例代码
│   ├── simple_example.py       #   Python 示例
│   └── workflow.yaml           #   YAML 工作流示例
├── pyproject.toml              # pip 配置
├── package.json                # npm 配置
└── README.md
```

## 🧪 测试

```bash
pip install -e ".[dev]"
python -m pytest orchestrator_team/tests/ -v
```

## 🤝 Contributing

```bash
git clone https://github.com/thefort827/orchestrator-team.git
cd orchestrator-team
pip install -e ".[dev]"
python -m pytest
```

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 License

MIT — 随便用，记得 Star ⭐

---

<div align="center">

**如果这个项目帮到了你，请给个 ⭐ Star！**

你的 Star 是我继续开发的动力 🚀

[![Star History Chart](https://api.star-history.com/svg?repos=thefort827/orchestrator-team&type=Date)](https://star-history.com/#thefort827/orchestrator-team&Date)

</div>

---

<a name="english"></a>

## 🇺🇸 English

### What is it?

A lightweight multi-agent orchestration framework that solves three critical problems:

- **🔒 Physical Directory Isolation** — Each agent works in its own directory. No file conflicts, ever.
- **📋 Task Pre-Checker** — Filters out invalid tasks before execution. No more wasted tokens.
- **✅ Quality Gates** — 2-layer checks with zero LLM cost. No more empty files or syntax errors.

### Install

```bash
pip install orchestrator-team
# or
npm install -g orchestrator-team
```

### Quick Start

```python
from orchestrator_team import Orchestrator, TaskDef

tasks = [
    TaskDef(id="backend", name="Backend", role="engineer",
            description="Build REST API", dependencies=[]),
    TaskDef(id="frontend", name="Frontend", role="engineer",
            description="Build Web UI", dependencies=["backend"]),
]

orch = Orchestrator(agent_executor=your_agent_fn)
result = asyncio.run(orch.run(tasks, "./output"))
```

### Benchmarks

| Metric | Before | After v3.0 | Improvement |
|--------|--------|------------|-------------|
| Token usage | 826K | 55.6K | **-93%** |
| Execution time | 100min | 11min | **-89%** |
| Agent success rate | 56% | 100% | **+44%** |

[MIT License](LICENSE) · [Contributing](CONTRIBUTING.md) · [GitHub](https://github.com/thefort827/orchestrator-team)
