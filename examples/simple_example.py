"""
Orchestrator Team — 最简示例
演示如何用3个Agent协作完成一个项目
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator_team import Orchestrator, TaskDef, TaskResult


async def my_agent(task: TaskDef, workspace_dir: str, context: str) -> TaskResult:
    """
    你的Agent执行器 — 在这里调用LLM
    
    Args:
        task: 当前任务定义
        workspace_dir: Agent的隔离工作目录（只能写这个目录）
        context: 编排器构建的上下文（含全局+角色+任务信息）
    """
    # 示例：直接创建文件（实际使用时替换为LLM调用）
    output_file = os.path.join(workspace_dir, f"{task.id}.py")
    with open(output_file, "w") as f:
        f.write(f'"""Module: {task.name}"""\n')
        f.write(f"# Task: {task.description}\n")
        f.write(f"# Role: {task.role}\n\n")
        f.write(f"def main():\n")
        f.write(f'    print("Hello from {task.name}")\n\n')
        f.write(f'if __name__ == "__main__":\n')
        f.write(f"    main()\n")

    return TaskResult(
        task_id=task.id,
        status="COMPLETED",
        agent_id=task.id,
        files_created=[f"{task.id}.py"],
        tokens_used=1000,  # 实际使用时记录真实token消耗
    )


async def main():
    # 定义任务
    tasks = [
        TaskDef(
            id="models",
            name="数据模型",
            role="engineer",
            description="定义User、Post、Comment三个数据模型",
            dependencies=[],
        ),
        TaskDef(
            id="api",
            name="API接口",
            role="engineer",
            description="开发RESTful API接口",
            dependencies=["models"],
        ),
        TaskDef(
            id="tests",
            name="单元测试",
            role="tester",
            description="编写API接口的单元测试",
            dependencies=["api"],
        ),
    ]

    # 创建编排器
    orchestrator = Orchestrator(
        agent_executor=my_agent,
        max_parallel=2,
    )

    # 运行
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    result = await orchestrator.run(tasks, output_dir, budget=50000)

    # 输出结果
    print(result.summary())

    # 查看产出文件
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            print(f"  📄 {f}")


if __name__ == "__main__":
    asyncio.run(main())
