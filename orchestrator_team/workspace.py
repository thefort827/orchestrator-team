"""
物理目录隔离 — 每个子代理独立工作目录
核心原则：子代理只能写自己的目录，共享依赖通过只读软链接提供
"""

import os
import shutil
import glob
from dataclasses import dataclass, field


@dataclass
class MergeReport:
    """合并报告"""
    added: list = field(default_factory=list)
    overwritten: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    kept_existing: list = field(default_factory=list)

    @property
    def total_files(self):
        return len(self.added) + len(self.overwritten) + len(self.skipped) + len(self.kept_existing)

    def summary(self) -> str:
        return (
            f"合并完成: 新增{len(self.added)} | 覆盖{len(self.overwritten)} | "
            f"跳过{len(self.skipped)} | 保留{len(self.kept_existing)}"
        )


class IsolatedWorkspace:
    """
    物理目录隔离 — 每个子代理独立工作目录
    
    流程：
    1. 编排器创建 /tmp/workspaces/{run_id}/ 主目录
    2. 每个子代理分配 /tmp/workspaces/{run_id}/{agent_id}/
    3. 子代理启动时：cwd 设为独立目录，只挂载 shared/ 只读
    4. 子代理完成后：编排器合并到主输出目录
    5. 合并时：检测冲突、处理同名文件
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self._shared_dir = os.path.join(base_dir, "_shared")
        self._output_dir = os.path.join(base_dir, "_output")

    def create_workspace(self) -> str:
        """创建工作区根目录"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self._shared_dir, exist_ok=True)
        os.makedirs(self._output_dir, exist_ok=True)
        return self.base_dir

    def create_agent_dir(self, agent_id: str, shared_deps: list[str] = None) -> str:
        """
        为子代理创建隔离目录
        
        Args:
            agent_id: 子代理ID
            shared_deps: 需要挂载的共享依赖路径列表（相对于_shared目录）
        
        Returns:
            子代理工作目录路径
        """
        agent_dir = os.path.join(self.base_dir, agent_id)
        os.makedirs(agent_dir, exist_ok=True)

        # 软链接共享依赖（只读）
        if shared_deps:
            for dep_path in shared_deps:
                src = os.path.join(self._shared_dir, dep_path)
                dst = os.path.join(agent_dir, dep_path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(src) and not os.path.exists(dst):
                    # Windows用junction，Linux用symlink
                    if os.name == 'nt':
                        if os.path.isdir(src):
                            os.symlink(src, dst, target_is_directory=True)
                        else:
                            os.symlink(src, dst)
                    else:
                        os.symlink(src, dst)

        return agent_dir

    def copy_to_shared(self, source_path: str, rel_path: str):
        """将文件复制到共享目录（供其他子代理使用）"""
        dest = os.path.join(self._shared_dir, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.isdir(source_path):
            shutil.copytree(source_path, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, dest)

    def merge_to_output(self, source_dir: str = None) -> MergeReport:
        """
        合并子代理产出到输出目录
        
        Args:
            source_dir: 指定源目录（默认扫描所有子代理目录）
        """
        report = MergeReport()

        if source_dir:
            # 合并指定目录
            self._merge_single(source_dir, os.path.basename(source_dir), report)
        else:
            # 扫描所有子代理目录
            for item in sorted(os.listdir(self.base_dir)):
                item_path = os.path.join(self.base_dir, item)
                if not os.path.isdir(item_path):
                    continue
                if item.startswith("_"):  # 跳过 _shared, _output
                    continue
                self._merge_single(item_path, item, report)

        return report

    def _merge_single(self, agent_dir: str, agent_id: str, report: MergeReport):
        """合并单个子代理的产出"""
        for root, dirs, files in os.walk(agent_dir):
            # 跳过软链接目录
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]

            for file_name in files:
                file_path = os.path.join(root, file_name)
                if os.path.islink(file_path):
                    continue

                rel = os.path.relpath(file_path, agent_dir)
                dest = os.path.join(self._output_dir, rel)

                if os.path.exists(dest):
                    if self._files_identical(file_path, dest):
                        report.skipped.append((agent_id, rel))
                    elif os.path.getsize(file_path) > os.path.getsize(dest):
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(file_path, dest)
                        report.overwritten.append((agent_id, rel))
                    else:
                        report.kept_existing.append((agent_id, rel))
                else:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(file_path, dest)
                    report.added.append((agent_id, rel))

    def get_output_dir(self) -> str:
        """获取输出目录"""
        return self._output_dir

    def get_agent_dir(self, agent_id: str) -> str:
        """获取子代理工作目录"""
        return os.path.join(self.base_dir, agent_id)

    def cleanup(self):
        """清理临时工作区"""
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir, ignore_errors=True)

    @staticmethod
    def _files_identical(path1: str, path2: str) -> bool:
        """比较两个文件内容是否相同"""
        with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
            return f1.read() == f2.read()
