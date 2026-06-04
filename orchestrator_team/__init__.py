"""Orchestrator Team — Lightweight Multi-Agent Orchestration Framework"""

__version__ = "3.0.0"

from .orchestrator import Orchestrator, TaskDef, TaskResult, OrchestrationResult
from .workspace import IsolatedWorkspace, MergeReport
from .pre_checker import TaskPreChecker, PreCheckResult
from .quality_gate import QualityGate, QualityResult
from .context_pool import SharedContextPool

__all__ = [
    "Orchestrator", "TaskDef", "TaskResult", "OrchestrationResult",
    "IsolatedWorkspace", "MergeReport",
    "TaskPreChecker", "PreCheckResult",
    "QualityGate", "QualityResult",
    "SharedContextPool",
]
