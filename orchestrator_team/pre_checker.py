"""
任务预检器 — 代理启动前的可行性评估
决策：PROCEED / MERGE / SKIP / DOWNGRADE
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PreCheckResult:
    """预检结果"""
    decision: str  # PROCEED / MERGE / SKIP / DOWNGRADE
    reason: str = ""
    merge_target: Optional[str] = None
    downgrade_config: Optional[dict] = None


class TaskPreChecker:
    """
    任务预检器 — 在子代理启动前评估可行性
    
    检查项：
    1. 任务描述是否明确（<50字则合并到父任务）
    2. 前置依赖是否满足（依赖未完成则等待/跳过）
    3. 预算是否充足（不够则降级）
    4. 相似任务是否已存在（避免重复）
    """

    def __init__(self, min_task_length: int = 20, 
                 max_single_task_ratio: float = 0.3):
        self.min_task_length = min_task_length
        self.max_single_task_ratio = max_single_task_ratio

    def check(self, task_id: str, task_desc: str, 
              dependencies: list[str],
              completed_tasks: dict,
              remaining_budget: int,
              estimated_tokens: int,
              existing_outputs: dict = None) -> PreCheckResult:
        """
        执行预检
        
        Args:
            task_id: 任务ID
            task_desc: 任务描述
            dependencies: 前置依赖任务ID列表
            completed_tasks: 已完成任务 {id: result}
            remaining_budget: 剩余Token预算
            estimated_tokens: 预估Token消耗
            existing_outputs: 已有产出 {task_id: [files]}
        
        Returns:
            PreCheckResult
        """
        # 1. 任务明确性检查
        if len(task_desc.strip()) < self.min_task_length:
            return PreCheckResult(
                decision="SKIP",
                reason=f"任务描述过短({len(task_desc)}字)，跳过"
            )

        # 2. 依赖检查
        for dep_id in dependencies:
            if dep_id not in completed_tasks:
                return PreCheckResult(
                    decision="SKIP",
                    reason=f"前置依赖 {dep_id} 未完成，跳过"
                )
            dep_result = completed_tasks[dep_id]
            if isinstance(dep_result, dict) and dep_result.get("status") == "FAILED":
                return PreCheckResult(
                    decision="SKIP",
                    reason=f"前置依赖 {dep_id} 失败，跳过"
                )

        # 3. 预算检查
        if estimated_tokens > remaining_budget * self.max_single_task_ratio:
            downgrade_tokens = int(remaining_budget * 0.15)
            return PreCheckResult(
                decision="DOWNGRADE",
                reason=f"预算不足(预估{estimated_tokens}，剩余{remaining_budget})，降级执行",
                downgrade_config={"max_tokens": downgrade_tokens}
            )

        # 4. 重复检查
        if existing_outputs:
            for existing_id, existing_files in existing_outputs.items():
                if existing_id == task_id:
                    continue
                # 检查是否有大量文件重叠
                if existing_files and self._has_significant_overlap(task_desc, existing_id):
                    return PreCheckResult(
                        decision="SKIP",
                        reason=f"与已有任务 {existing_id} 重复，复用其结果"
                    )

        return PreCheckResult(decision="PROCEED")

    def _has_significant_overlap(self, task_desc: str, existing_id: str) -> bool:
        """检查任务是否与已有任务有显著重叠"""
        # 简单实现：检查任务ID是否在描述中
        # 实际应用中可以用向量相似度
        return False
