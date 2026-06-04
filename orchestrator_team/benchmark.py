"""
基准测试运行器 — 对比多智能体 vs 单智能体
"""

import asyncio
import time
import json
import os
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from .orchestrator import Orchestrator, TaskDef, TaskResult, OrchestrationResult
from .context_pool import SharedContextPool
from .pre_checker import TaskPreChecker
from .quality_gate import QualityGate


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    approach: str  # "multi-agent" / "single-agent"
    runtime: float = 0.0
    total_tokens: int = 0
    files_created: int = 0
    lines_written: int = 0
    tasks_completed: int = 0
    tasks_skipped: int = 0
    tasks_failed: int = 0
    quality_issues: int = 0
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "approach": self.approach,
            "runtime_seconds": round(self.runtime, 1),
            "total_tokens": self.total_tokens,
            "files_created": self.files_created,
            "lines_written": self.lines_written,
            "tasks_completed": self.tasks_completed,
            "tasks_skipped": self.tasks_skipped,
            "tasks_failed": self.tasks_failed,
            "quality_issues": self.quality_issues,
            "tokens_per_file": round(self.total_tokens / max(1, self.files_created)),
            "tokens_per_line": round(self.total_tokens / max(1, self.lines_written), 1),
            "files_per_minute": round(self.files_created / max(0.01, self.runtime / 60), 1),
        }


class BenchmarkRunner:
    """
    基准测试运行器
    
    对比多智能体（优化版编排器）和单智能体的：
    - Token消耗
    - 执行时间
    - 产出文件数
    - 代码行数
    - 质量得分
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    async def run_multi_agent(self, tasks: list[TaskDef],
                               agent_executor: Callable,
                               budget: int = 300000) -> BenchmarkResult:
        """运行多智能体测试"""
        start = time.time()

        # 创建优化版编排器
        context_pool = SharedContextPool()
        context_pool.set_global_context(
            project_overview="分布式软件开发项目",
            code_standards="Python 3.11+, 类型注解, async优先, 每文件不超过250行"
        )

        orchestrator = Orchestrator(
            agent_executor=agent_executor,
            context_pool=context_pool,
            pre_checker=TaskPreChecker(),
            quality_gate=QualityGate(),
            max_parallel=4
        )

        # 执行
        result = await orchestrator.run(tasks, self.output_dir, budget)

        runtime = time.time() - start

        return BenchmarkResult(
            approach="multi-agent",
            runtime=runtime,
            total_tokens=result.total_tokens,
            files_created=result.total_files,
            lines_written=result.total_lines,
            tasks_completed=result.completed,
            tasks_skipped=result.skipped,
            tasks_failed=result.failed,
            details={
                "stages": len(result.stages),
                "merge_report": result.merge_report.summary() if result.merge_report else "",
                "run_id": result.run_id
            }
        )

    async def run_single_agent(self, requirement: str,
                                agent_executor: Callable) -> BenchmarkResult:
        """运行单智能体测试"""
        start = time.time()

        # 单智能体：一个代理完成所有任务
        result = await agent_executor(requirement, self.output_dir)

        runtime = time.time() - start

        return BenchmarkResult(
            approach="single-agent",
            runtime=runtime,
            total_tokens=result.get("tokens", 0),
            files_created=result.get("files", 0),
            lines_written=result.get("lines", 0),
            tasks_completed=1,
            details=result
        )

    def compare(self, multi: BenchmarkResult, 
                single: BenchmarkResult) -> dict:
        """对比两个测试结果"""
        def pct_diff(a, b):
            if b == 0:
                return 0
            return round((a - b) / b * 100, 1)

        return {
            "multi_agent": multi.to_dict(),
            "single_agent": single.to_dict(),
            "comparison": {
                "token_diff": pct_diff(multi.total_tokens, single.total_tokens),
                "runtime_diff": pct_diff(multi.runtime, single.runtime),
                "files_diff": pct_diff(multi.files_created, single.files_created),
                "lines_diff": pct_diff(multi.lines_written, single.lines_written),
                "multi_token_efficiency": round(multi.lines_written / max(1, multi.total_tokens) * 1000, 2),
                "single_token_efficiency": round(single.lines_written / max(1, single.total_tokens) * 1000, 2),
            }
        }

    def save_report(self, comparison: dict, filename: str = "benchmark_report.json"):
        """保存对比报告"""
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        return path

    def print_report(self, comparison: dict):
        """打印对比报告"""
        multi = comparison["multi_agent"]
        single = comparison["single_agent"]
        diff = comparison["comparison"]

        print("\n" + "=" * 60)
        print("基准测试对比报告")
        print("=" * 60)

        print(f"\n{'指标':<20} {'多智能体':>12} {'单智能体':>12} {'差异':>10}")
        print("-" * 56)
        print(f"{'Token消耗':<20} {multi['total_tokens']:>12,} {single['total_tokens']:>12,} {diff['token_diff']:>+9}%")
        print(f"{'耗时(秒)':<20} {multi['runtime_seconds']:>12} {single['runtime_seconds']:>12} {diff['runtime_diff']:>+9}%")
        print(f"{'文件数':<20} {multi['files_created']:>12} {single['files_created']:>12} {diff['files_diff']:>+9}%")
        print(f"{'代码行':<20} {multi['lines_written']:>12} {single['lines_written']:>12} {diff['lines_diff']:>+9}%")
        print(f"{'Token效率(行/K)':<20} {diff['multi_token_efficiency']:>12} {diff['single_token_efficiency']:>12}")

        print(f"\n多智能体详情: {multi.get('details', {})}")
        print(f"单智能体详情: {single.get('details', {})}")
        print("=" * 60)
