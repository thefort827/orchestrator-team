<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-blue?style=for-the-badge" alt="version">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="license">
  <img src="https://img.shields.io/badge/agents-unlimited-FF6B35?style=for-the-badge" alt="agents">
</p>

<h1 align="center">🎯 Orchestrator Team</h1>

<p align="center">
  <b>轻量级多智能体编排框架</b><br>
  物理目录隔离 · 任务预检 · 质量门禁 · 零LLM开销<br>
  <i>让多个AI Agent像团队一样协作，而不是互相踩脚</i>
</p>

---

## 🤔 为什么需要它？

现有的多智能体框架（CrewAI、AutoGen、LangGraph）存在三个致命问题：

| 问题 | 后果 | Orchestrator Team 的方案 |
|------|------|--------------------------|
| **Agent互相覆盖文件** | 5个Agent写了5份相同的models.py | ✅ 物理目录隔离 |
| **40% Agent在摸鱼** | 消耗Token但0产出 | ✅ 任务预检器 |
| **产出质量不可控** | 空文件、语法错误、占位符代码 | ✅ 2层质量门禁 |

## 📊 实测数据

在3个基准测试中，Orchestrator Team v3.0 表现：

| 指标 | 原版多智能体 | v3.0 | 改善 |
|------|-------------|------|------|
| Token消耗 | 826K | 55.6K | **-93%** |
| 耗时 | 100min | 11min | **-89%** |
| Agent有效率 | 56% | 100% | **+44%** |
| 文件重复率 | 高 | 0% | **-100%** |

## 🚀 快速开始

### 安装

```bash
# pip
pip install orchestrator-team

# npm (CLI)
npm install -g orchestrator-team
npx orchestrator-team --help
```

### 30秒示例

```python
from orchestrator_team import Orchestrator, TaskDef

# 定义任务
tasks = [
    TaskDef(id="arch", name="架构设计", role="architect",
            description="设计系统架构", dependencies=[]),
    TaskDef(id="backend", name="后端开发", role="engineer",
            description="开发API服务", dependencies=["arch"]),
    TaskDef(id="frontend", name="前端开发", role="engineer",
            description="开发Web界面", dependencies=["arch"]),
    TaskDef(id="test", name="测试", role="tester",
            description="编写测试用例", dependencies=["backend", "frontend"]),
]

# 定义执行器（你的LLM调用逻辑）
async def my_executor(task, workspace_dir, context):
    # 在这里调用你的LLM
    # response = await llm.chat(context)
    # 在 workspace_dir 中创建文件
    ...

# 运行编排
import asyncio
orchestrator = Orchestrator(agent_executor=my_executor)
result = asyncio.run(orchestrator.run(tasks, "./output"))
print(result.summary())
```

### YAML 工作流

```yaml
name: "my-project"
version: "1.0.0"

config:
  max_parallelism: 4
  budget:
    max_tokens: 300000

nodes:
  - id: arch
    type: agent
    config:
      role: architect
      task: "设计系统架构"
      output: "architecture.md"

  - id: backend
    type: agent
    config:
      role: engineer
      task: "开发后端API"
      depends_on: [arch]
      output: "backend/"

edges:
  - source: arch
    target: backend
    type: always
```

```bash
npx orchestrator-team run workflow.yaml
```

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator Team v3.0                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Task       │  │  Quality    │  │  Context    │    │
│  │  Pre-Check  │  │  Gate       │  │  Pool       │    │
│  │  (过滤无效) │  │  (零LLM)    │  │  (3层共享)  │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │            │
│         ▼                ▼                ▼            │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Orchestrator Core                   │   │
│  │   拓扑排序 → 并行派发 → 产出校验 → 合并汇总    │   │
│  └──────────────────────┬──────────────────────────┘   │
│                         │                              │
│         ┌───────────────┼───────────────┐              │
│         ▼               ▼               ▼              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │ Agent A  │    │ Agent B  │    │ Agent C  │         │
│  │ /tmp/a/  │    │ /tmp/b/  │    │ /tmp/c/  │         │
│  │ (隔离)   │    │ (隔离)   │    │ (隔离)   │         │
│  └──────────┘    └──────────┘    └──────────┘         │
│         │               │               │              │
│         ▼               ▼               ▼              │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Isolated Workspace                     │   │
│  │   独立目录 + 只读软链接 + 自动合并 + 冲突处理   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🔑 核心特性

### 1. 物理目录隔离

每个Agent在独立目录中工作，**物理上不可能**互相覆盖文件。

```python
workspace = IsolatedWorkspace("/tmp/workspaces/run-001")
agent_dir = workspace.create_agent_dir("agent_a")
# agent_a 只能写 /tmp/workspaces/run-001/agent_a/
# 其他Agent看不到也写不了这个目录
```

### 2. 任务预检器

在Agent启动前评估可行性，过滤掉"注定摸鱼"的任务。

```python
checker = TaskPreChecker()
result = checker.check(
    task_id="backend",
    task_desc="开发后端API",
    dependencies=["arch"],
    completed_tasks={"arch": {"status": "COMPLETED"}},
    remaining_budget=200000,
    estimated_tokens=30000
)
# result.decision: "PROCEED" | "SKIP" | "DOWNGRADE"
```

### 3. 质量门禁

2层检查，**零LLM成本**。

```python
gate = QualityGate()
result = gate.check(
    agent_id="backend",
    workspace_dir="/tmp/workspaces/run-001/backend/",
    claimed_files=["main.py", "routes.py"]
)
# 检查: 文件存在、大小合理、Python语法正确、无重复
```

### 4. 共享上下文池

3层缓存，避免每个Agent重复加载相同的系统提示词。

```python
pool = SharedContextPool()
pool.set_global_context(
    project_overview="电商平台",
    code_standards="Python 3.11+, 类型注解"
)
pool.set_role_context("engineer", ["python", "fastapi"], ["async"])

# 每个Agent只接收自己需要的上下文
context = pool.build_context("engineer", "开发用户服务", "无前置依赖")
```

## 📁 项目结构

```
orchestrator-team/
├── orchestrator_team/          # Python 核心包
│   ├── __init__.py
│   ├── orchestrator.py         # 编排器主循环
│   ├── workspace.py            # 物理目录隔离
│   ├── pre_checker.py          # 任务预检器
│   ├── quality_gate.py         # 质量门禁
│   ├── context_pool.py         # 共享上下文池
│   └── benchmark.py            # 基准测试工具
├── cli/                        # Node.js CLI
│   └── index.js
├── docs/                       # 文档
├── examples/                   # 示例
├── pyproject.toml              # pip 安装配置
├── package.json                # npm 安装配置
└── README.md
```

## 🧪 运行测试

```bash
# Python 测试
pip install -e ".[dev]"
python -m pytest orchestrator_team/tests/ -v

# 或直接运行
python orchestrator_team/tests/test_core.py
```

## 📈 与竞品对比

| 特性 | CrewAI | AutoGen | LangGraph | **Orchestrator Team** |
|------|--------|---------|-----------|----------------------|
| 物理目录隔离 | ❌ | ❌ | ❌ | ✅ |
| 任务预检 | ❌ | ❌ | ❌ | ✅ |
| 质量门禁 | ❌ | 部分 | ❌ | ✅ (零LLM) |
| 共享上下文 | ❌ | ❌ | ❌ | ✅ (3层) |
| Token效率 | 低 | 中 | 中 | **高** |
| 学习曲线 | 中 | 高 | 高 | **低** |
| 外部依赖 | 多 | 多 | 多 | **少** |

## 🤝 Contributing

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
git clone https://github.com/thefort827/orchestrator-team.git
cd orchestrator-team
pip install -e ".[dev]"
python -m pytest
```

## 📄 License

MIT License — 随便用，记得Star就行 ⭐

---

<p align="center">
  <b>如果这个项目帮到了你，请给个 ⭐ Star！</b><br>
  <sub>你的Star是我继续开发的动力 🚀</sub>
</p>
