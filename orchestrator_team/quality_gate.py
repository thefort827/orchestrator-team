"""
质量门禁 — 2层检查（机械检查 + 产出校验）
零LLM成本
"""

import os
import re
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    """检查结果"""
    passed: bool
    score: float = 1.0
    details: list = field(default_factory=list)


@dataclass
class QualityResult:
    """质量门禁结果"""
    passed: bool
    phase: str = ""
    score: float = 1.0
    details: list = field(default_factory=list)
    action: str = ""  # RETRY / SKIP / PASS


class QualityGate:
    """
    2层质量门禁 — 零LLM成本
    
    Phase 1: 机械检查 — 文件存在、大小、语法、格式
    Phase 2: 产出校验 — 重复检测、模板检测、依赖完整性
    """

    def __init__(self, min_file_size: int = 10,
                 check_syntax: bool = True,
                 check_duplicates: bool = True):
        self.min_file_size = min_file_size
        self.check_syntax = check_syntax
        self.check_duplicates = check_duplicates
        self._existing_files: dict[str, list[str]] = {}  # agent_id -> [files]

    def check(self, agent_id: str, workspace_dir: str,
              claimed_files: list[str] = None) -> QualityResult:
        """
        执行质量检查
        
        Args:
            agent_id: 子代理ID
            workspace_dir: 子代理工作目录
            claimed_files: 声称创建的文件列表
        """
        # 收集实际创建的文件
        actual_files = self._collect_files(workspace_dir)

        # Phase 1: 机械检查
        mech = self._mechanical_check(actual_files, workspace_dir, claimed_files)
        if not mech.passed:
            return QualityResult(
                passed=False, phase="mechanical",
                score=mech.score, details=mech.details, action="RETRY"
            )

        # Phase 2: 产出校验
        prod = self._production_check(agent_id, actual_files, workspace_dir)
        if not prod.passed:
            return QualityResult(
                passed=False, phase="production",
                score=prod.score, details=prod.details, action="SKIP"
            )

        # 记录产出
        self._existing_files[agent_id] = actual_files

        return QualityResult(
            passed=True,
            score=mech.score * 0.5 + prod.score * 0.5,
            action="PASS"
        )

    def _mechanical_check(self, actual_files: list[str], 
                          workspace_dir: str,
                          claimed_files: list[str] = None) -> CheckResult:
        """Phase 1: 机械检查"""
        issues = []

        # 文件存在性（如果声称了文件）
        if claimed_files:
            for f in claimed_files:
                full_path = os.path.join(workspace_dir, f)
                if not os.path.exists(full_path):
                    issues.append(f"声称的文件不存在: {f}")

        # 文件大小
        for f in actual_files:
            full_path = os.path.join(workspace_dir, f)
            size = os.path.getsize(full_path)
            if size < self.min_file_size:
                issues.append(f"文件过小: {f} ({size} bytes)")

        # Python语法检查
        if self.check_syntax:
            for f in actual_files:
                if f.endswith('.py'):
                    full_path = os.path.join(workspace_dir, f)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as fh:
                            compile(fh.read(), f, 'exec')
                    except SyntaxError as e:
                        issues.append(f"语法错误: {f}:{e.lineno}")
                    except Exception:
                        pass  # 编码问题等，跳过

        return CheckResult(
            passed=len(issues) == 0,
            score=1.0 - min(1.0, len(issues) * 0.2),
            details=issues
        )

    def _production_check(self, agent_id: str, actual_files: list[str],
                          workspace_dir: str) -> CheckResult:
        """Phase 2: 产出校验"""
        issues = []

        # 重复检测（与其他代理的产出对比）
        if self.check_duplicates:
            for f in actual_files:
                for other_id, other_files in self._existing_files.items():
                    if other_id == agent_id:
                        continue
                    if f in other_files:
                        # 检查内容是否相同
                        other_path = self._get_other_path(other_id, f)
                        if other_path and os.path.exists(other_path):
                            my_path = os.path.join(workspace_dir, f)
                            if self._files_identical(my_path, other_path):
                                issues.append(f"文件与代理 {other_id} 完全相同: {f}")

        # 模板检测（内容是否是占位符）
        for f in actual_files:
            if f.endswith('.py'):
                full_path = os.path.join(workspace_dir, f)
                try:
                    content = open(full_path, 'r', encoding='utf-8').read()
                    if self._is_placeholder(content):
                        issues.append(f"文件是占位符: {f}")
                except Exception:
                    pass

        return CheckResult(
            passed=len(issues) == 0,
            score=1.0 - min(1.0, len(issues) * 0.15),
            details=issues
        )

    def _collect_files(self, directory: str) -> list[str]:
        """收集目录中的所有文件（相对路径）"""
        files = []
        if not os.path.exists(directory):
            return files
        for root, dirs, filenames in os.walk(directory):
            # 跳过隐藏目录和__pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for fname in filenames:
                if fname.startswith('.'):
                    continue
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, directory)
                files.append(rel_path)
        return files

    def _is_placeholder(self, content: str) -> bool:
        """检测是否是占位符代码"""
        stripped = content.strip()
        # 太短
        if len(stripped) < 20:
            return True
        # 只有pass/.../TODO
        if stripped in ('pass', '...', '# TODO', 'raise NotImplementedError'):
            return True
        # 只有import没有实际代码
        lines = [l.strip() for l in stripped.split('\n') if l.strip() and not l.strip().startswith('#')]
        if len(lines) <= 2 and all(l.startswith(('import', 'from', '"""', "'''")) for l in lines):
            return True
        return False

    @staticmethod
    def _files_identical(path1: str, path2: str) -> bool:
        with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
            return f1.read() == f2.read()

    def _get_other_path(self, other_id: str, file_rel: str) -> str:
        """获取其他代理的文件路径（需要外部配置）"""
        # 这个方法需要在实际使用时由编排器注入
        return None
