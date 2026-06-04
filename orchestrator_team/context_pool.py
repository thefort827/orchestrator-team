"""
共享上下文池 — 代理间的公共信息缓存
避免每个代理重复加载系统提示词、工具说明、项目规范
"""

from dataclasses import dataclass


@dataclass
class ContextLayers:
    """分层上下文"""
    global_ctx: str = ""      # Layer 0: 所有代理共享
    role_ctx: str = ""        # Layer 1: 同角色共享
    task_ctx: str = ""        # Layer 2: 单任务独有


class SharedContextPool:
    """
    共享上下文池 — 代理间的公共信息缓存
    
    分层策略：
    - Layer 0 (Global): 所有代理共享，只加载一次
      - 工具说明 (~1500 tokens)
      - 代码规范 (~300 tokens)
      - 项目约束 (~200 tokens)
    - Layer 1 (Role): 同角色代理共享
      - 角色能力说明 (~500 tokens)
      - 角色约束 (~200 tokens)
    - Layer 2 (Task): 单任务独有
      - 任务描述 (~1000 tokens)
      - 前置结果摘要 (~500 tokens)
    
    优化前：每个代理 ~5000 tokens × 16 = 80K
    优化后：Global(2K) + Role(700×4) + Task(1500×16) = 28.8K
    节省：51.2K tokens (64%)
    """

    def __init__(self):
        self._global_ctx: str = ""
        self._role_ctx: dict[str, str] = {}
        self._tool_docs: str = ""
        self._code_standards: str = ""
        self._project_overview: str = ""

    def set_global_context(self, tool_docs: str = "", code_standards: str = "",
                           project_overview: str = ""):
        """设置全局共享上下文（只调用一次）"""
        self._tool_docs = tool_docs
        self._code_standards = code_standards
        self._project_overview = project_overview

        parts = []
        if project_overview:
            parts.append(f"## 项目概述\n{project_overview}")
        if code_standards:
            parts.append(f"## 代码规范\n{code_standards}")
        if tool_docs:
            parts.append(f"## 工具说明\n{tool_docs}")
        self._global_ctx = "\n\n".join(parts)

    def set_role_context(self, role: str, capabilities: list[str],
                         constraints: list[str], extra: str = ""):
        """设置角色上下文"""
        parts = [f"## 角色: {role}"]
        if capabilities:
            parts.append(f"能力: {', '.join(capabilities)}")
        if constraints:
            parts.append(f"约束: {', '.join(constraints)}")
        if extra:
            parts.append(extra)
        self._role_ctx[role] = "\n".join(parts)

    def build_context(self, role: str, task_desc: str,
                      deps_summary: str = "") -> str:
        """
        为子代理构建上下文
        
        Args:
            role: 子代理角色
            task_desc: 任务描述
            deps_summary: 前置依赖摘要
        """
        parts = []

        # Layer 0: 全局共享
        if self._global_ctx:
            parts.append(self._global_ctx)

        # Layer 1: 角色共享
        if role in self._role_ctx:
            parts.append(self._role_ctx[role])

        # Layer 2: 任务独有
        task_parts = [f"## 任务\n{task_desc}"]
        if deps_summary:
            task_parts.append(f"## 前置结果\n{deps_summary}")
        parts.append("\n\n".join(task_parts))

        return "\n\n---\n\n".join(parts)

    def get_global_context(self) -> str:
        """获取全局上下文"""
        return self._global_ctx

    def get_role_context(self, role: str) -> str:
        """获取角色上下文"""
        return self._role_ctx.get(role, "")
