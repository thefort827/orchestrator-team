"""
编排器 — 轻量级多智能体编排主循环
职责：任务拆分、预检、派发、产出校验、汇总
"""

import asyncio
import time
import uuid
import os
import shutil
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

from .workspace import IsolatedWorkspace, MergeReport
from .pre_checker import TaskPreChecker, PreCheckResult
from .quality_gate import QualityGate, QualityResult
from .context_pool import SharedContextPool


@dataclass
class TaskDef:
    """任务定义"""
    id: str
    name: str
    role: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    output_dir: str = ""
    max_tokens: int = 30000
    timeout: int = 300  # 秒


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: str  # COMPLETED / SKIPPED / FAILED / TIMEOUT
    agent_id: str = ""
    files_created: list[str] = field(default_factory=list)
    quality: Optional[QualityResult] = None
    duration: float = 0.0
    tokens_used: int = 0
    error: str = ""
    reason: str = ""  # 跳过/失败原因


@dataclass
class StageResult:
    """阶段执行结果"""
    stage_name: str
    tasks: list[TaskResult] = field(default_factory=list)
    duration: float = 0.0


@dataclass
class OrchestrationResult:
    """编排总结果"""
    run_id: str = ""
    total_tasks: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    total_files: int = 0
    total_lines: int = 0
    total_tokens: int = 0
    total_duration: float = 0.0
    stages: list[StageResult] = field(default_factory=list)
    merge_report: Optional[MergeReport] = None

    def summary(self) -> str:
        return (
            f"编排完成 [{self.run_id[:8]}]\n"
            f"  任务: {self.completed}成功 / {self.skipped}跳过 / {self.failed}失败\n"
            f"  产出: {self.total_files}文件 / {self.total_lines}行\n"
            f"  消耗: {self.total_tokens:,} tokens / {self.total_duration:.1f}秒"
        )


class Orchestrator:
    """
    轻量编排器 — 只做四件事
    
    1. 任务预检（规则驱动，无LLM）
    2. 派发执行（并行+隔离目录）
    3. 产出校验（零LLM成本）
    4. 结果汇总（模板化，无LLM）
    """

    def __init__(self,
                 agent_executor: Callable[[TaskDef, str, str], Awaitable[TaskResult]],
                 context_pool: SharedContextPool = None,
                 pre_checker: TaskPreChecker = None,
                 quality_gate: QualityGate = None,
                 max_parallel: int = 4):
        """
        Args:
            agent_executor: 子代理执行函数 (task, agent_dir, context) -> TaskResult
            context_pool: 共享上下文池
            pre_checker: 任务预检器
            quality_gate: 质量门禁
            max_parallel: 最大并行数
        """
        self.agent_executor = agent_executor
        self.context_pool = context_pool or SharedContextPool()
        self.pre_checker = pre_checker or TaskPreChecker()
        self.quality_gate = quality_gate or QualityGate()
        self.max_parallel = max_parallel

    async def run(self, tasks: list[TaskDef],
                  output_dir: str,
                  budget: int = 300000) -> OrchestrationResult:
        """
        执行编排
        
        Args:
            tasks: 任务列表
            output_dir: 最终输出目录
            budget: 总Token预算
        """
        run_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        result = OrchestrationResult(run_id=run_id)

        # 创建隔离工作区
        workspace = IsolatedWorkspace(f"/tmp/workspaces/{run_id}")
        workspace.create_workspace()

        # 构建任务索引
        task_map = {t.id: t for t in tasks}
        completed = {}
        remaining_budget = budget
        all_results = []

        try:
            # 按拓扑序分阶段执行
            stages = self._topological_sort(tasks)

            for stage_tasks in stages:
                stage_result = StageResult(
                    stage_name="+".join(t.id for t in stage_tasks)
                )
                stage_start = time.time()

                # 并行派发同一阶段的任务
                coroutines = []
                for task in stage_tasks:
                    # 任务预检
                    precheck = self.pre_checker.check(
                        task_id=task.id,
                        task_desc=task.description,
                        dependencies=task.dependencies,
                        completed_tasks=completed,
                        remaining_budget=remaining_budget,
                        estimated_tokens=task.max_tokens
                    )

                    if precheck.decision == "SKIP":
                        tr = TaskResult(
                            task_id=task.id, status="SKIPPED",
                            reason=precheck.reason
                        )
                        stage_result.tasks.append(tr)
                        all_results.append(tr)
                        completed[task.id] = {"status": "SKIPPED"}
                        continue

                    if precheck.decision == "DOWNGRADE":
                        task.max_tokens = precheck.downgrade_config.get("max_tokens", task.max_tokens)

                    # 创建隔离目录
                    agent_dir = workspace.create_agent_dir(task.id)

                    # 构建上下文
                    deps_summary = self._build_deps_summary(task, completed)
                    context = self.context_pool.build_context(
                        role=task.role,
                        task_desc=task.description,
                        deps_summary=deps_summary
                    )

                    # 派发子代理
                    coroutines.append(
                        self._execute_with_timeout(task, agent_dir, context, workspace)
                    )

                # 等待阶段内所有任务完成
                if coroutines:
                    stage_results = await asyncio.gather(*coroutines, return_exceptions=True)

                    for tr in stage_results:
                        if isinstance(tr, Exception):
                            tr = TaskResult(task_id="unknown", status="FAILED", error=str(tr))
                        stage_result.tasks.append(tr)
                        all_results.append(tr)
                        if tr.status == "COMPLETED":
                            completed[tr.task_id] = {"status": "COMPLETED", "files": tr.files_created}
                            remaining_budget -= tr.tokens_used
                        else:
                            completed[tr.task_id] = {"status": tr.status}

                stage_result.duration = time.time() - stage_start
                result.stages.append(stage_result)

            # 合并产出到工作区内部目录
            merge_report = workspace.merge_to_output()
            result.merge_report = merge_report

            # 将工作区输出复制到最终输出目录
            workspace_output = workspace.get_output_dir()
            if os.path.exists(workspace_output):
                os.makedirs(output_dir, exist_ok=True)
                for item in os.listdir(workspace_output):
                    src = os.path.join(workspace_output, item)
                    dst = os.path.join(output_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)

            # 汇总
            result.total_tasks = len(tasks)
            result.completed = len([r for r in all_results if r.status == "COMPLETED"])
            result.skipped = len([r for r in all_results if r.status == "SKIPPED"])
            result.failed = len([r for r in all_results if r.status == "FAILED"])
            result.total_files = len(merge_report.added) + len(merge_report.overwritten)
            result.total_tokens = budget - remaining_budget
            result.total_duration = time.time() - start_time

        finally:
            # 清理
            workspace.cleanup()

        return result

    async def _execute_with_timeout(self, task: TaskDef, agent_dir: str,
                                     context: str,
                                     workspace: IsolatedWorkspace) -> TaskResult:
        """带超时的子代理执行"""
        try:
            tr = await asyncio.wait_for(
                self.agent_executor(task, agent_dir, context),
                timeout=task.timeout
            )

            # 产出校验
            if tr.status == "COMPLETED":
                quality = self.quality_gate.check(
                    agent_id=task.id,
                    workspace_dir=agent_dir,
                    claimed_files=tr.files_created
                )
                tr.quality = quality

                if not quality.passed:
                    if quality.action == "RETRY":
                        # 重试一次
                        tr = await asyncio.wait_for(
                            self.agent_executor(task, agent_dir, context),
                            timeout=task.timeout
                        )
                        tr.quality = self.quality_gate.check(
                            agent_id=task.id,
                            workspace_dir=agent_dir,
                            claimed_files=tr.files_created
                        )

            # 将产出复制到共享目录
            if tr.status == "COMPLETED" and tr.files_created:
                for f in tr.files_created:
                    src = __import__('os').path.join(agent_dir, f)
                    if __import__('os').path.exists(src):
                        workspace.copy_to_shared(src, f)

            return tr

        except asyncio.TimeoutError:
            return TaskResult(
                task_id=task.id, status="TIMEOUT",
                error=f"超时({task.timeout}秒)"
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id, status="FAILED",
                error=str(e)
            )

    def _topological_sort(self, tasks: list[TaskDef]) -> list[list[TaskDef]]:
        """拓扑排序，返回分阶段的任务列表"""
        task_map = {t.id: t for t in tasks}
        in_degree = {t.id: 0 for t in tasks}
        dependents = {t.id: [] for t in tasks}

        for t in tasks:
            for dep in t.dependencies:
                if dep in dependents:
                    dependents[dep].append(t.id)
                    in_degree[t.id] += 1

        stages = []
        remaining = set(t.id for t in tasks)

        while remaining:
            # 找出入度为0的节点
            current = [tid for tid in remaining if in_degree[tid] == 0]
            if not current:
                # 有循环，强制取剩余节点
                current = list(remaining)[:1]

            stages.append([task_map[tid] for tid in current])

            for tid in current:
                remaining.remove(tid)
                for dep_tid in dependents[tid]:
                    if dep_tid in remaining:
                        in_degree[dep_tid] -= 1

        return stages

    def _build_deps_summary(self, task: TaskDef, completed: dict) -> str:
        """构建前置依赖摘要"""
        if not task.dependencies:
            return ""

        parts = []
        for dep_id in task.dependencies:
            if dep_id in completed:
                dep = completed[dep_id]
                if dep.get("status") == "COMPLETED" and dep.get("files"):
                    parts.append(f"- {dep_id}: {', '.join(dep['files'][:5])}")
                else:
                    parts.append(f"- {dep_id}: {dep.get('status', 'unknown')}")

        return "\n".join(parts) if parts else ""
