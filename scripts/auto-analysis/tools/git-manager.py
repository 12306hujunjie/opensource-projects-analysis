#!/usr/bin/env python3
"""
SuperClaude Git Manager
Git操作管理工具，处理提交和推送操作
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class GitManager:
    """Git操作管理器"""
    
    def __init__(self, project_root: str, verbose: bool = False):
        self.project_root = Path(project_root).resolve()
        self.verbose = verbose
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}", file=sys.stderr)
    
    def is_git_repo(self) -> bool:
        """检查是否在Git仓库中"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_git_status(self) -> Dict:
        """获取Git状态"""
        if not self.is_git_repo():
            return {'is_repo': False}
        
        try:
            # 获取状态
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            # 解析状态
            status_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            status = {
                'is_repo': True,
                'is_clean': len(status_lines) == 0,
                'modified': [],
                'added': [],
                'deleted': [],
                'untracked': []
            }
            
            for line in status_lines:
                if len(line) < 3:
                    continue
                    
                status_code = line[:2]
                file_path = line[3:]
                
                if status_code == '??':
                    status['untracked'].append(file_path)
                elif status_code[0] == 'M' or status_code[1] == 'M':
                    status['modified'].append(file_path)
                elif status_code[0] == 'A' or status_code[1] == 'A':
                    status['added'].append(file_path)
                elif status_code[0] == 'D' or status_code[1] == 'D':
                    status['deleted'].append(file_path)
            
            return status
            
        except subprocess.CalledProcessError as e:
            self.log(f"获取Git状态失败: {e}", "ERROR")
            return {'is_repo': True, 'error': str(e)}
    
    def add_files(self, file_patterns: List[str]) -> bool:
        """添加文件到暂存区"""
        if not self.is_git_repo():
            self.log("不在Git仓库中", "ERROR")
            return False
        
        try:
            for pattern in file_patterns:
                result = subprocess.run(
                    ["git", "add", pattern],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.log(f"已添加文件模式: {pattern}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"添加文件失败: {e}", "ERROR")
            return False
    
    def commit_changes(self, message: str) -> bool:
        """提交更改"""
        if not self.is_git_repo():
            self.log("不在Git仓库中", "ERROR")
            return False
        
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.log(f"提交成功: {result.stdout.strip()}")
            return True
            
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in e.stdout:
                self.log("没有需要提交的更改")
                return True
            else:
                self.log(f"提交失败: {e}", "ERROR")
                return False
    
    def push_changes(self, remote: str = "origin", branch: str = "main") -> bool:
        """推送更改"""
        if not self.is_git_repo():
            self.log("不在Git仓库中", "ERROR")
            return False
        
        try:
            result = subprocess.run(
                ["git", "push", remote, branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.log(f"推送成功: {result.stdout.strip()}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"推送失败: {e}", "ERROR")
            return False
    
    def generate_commit_message(self, project_path: str, output_dir: str) -> str:
        """生成提交消息"""
        project_name = Path(project_path).name
        output_path = Path(output_dir)
        
        # 统计文档信息
        doc_files = list(output_path.glob("*.md"))
        doc_count = len(doc_files)
        
        total_lines = 0
        for doc_file in doc_files:
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    total_lines += len(f.readlines())
            except Exception:
                pass
        
        # 检测最高分析级别
        max_level = 1
        for doc_file in doc_files:
            filename = doc_file.name
            if match := __import__('re').match(r'(\d+)-L(\d+)-', filename):
                level = int(match.group(2))
                max_level = max(max_level, level)
        
        # 生成文档结构描述
        doc_structure = []
        for level in range(1, max_level + 1):
            level_docs = [f for f in doc_files if f.name.startswith(f"{level:02d}-L{level}-")]
            if level_docs:
                level_desc = f"L{level}: " + ", ".join([
                    doc.name.replace(f"{doc.name.split('-')[0]}-L{level}-", "").replace('.md', '')
                    for doc in level_docs
                ])
                doc_structure.append(level_desc)
        
        # 构建提交消息
        message = f"""feat: 完成{project_name}深度源码分析

🔍 Ultra-Think 级别分析成果:
• {doc_count}个L1-L{max_level}级别文档，总计{total_lines}+行深度分析
• 系统化架构洞察与技术价值分析
• 企业级技术框架完整剖析
• 深度挖掘核心设计理念与创新点

📚 文档结构:
{chr(10).join(doc_structure)}

🎯 分析价值:
• 提供完整的技术架构理解框架
• 深入挖掘技术创新点和最佳实践
• 为技术学习和项目参考提供价值蓝本
• 系统化的知识沉淀和经验总结

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
        
        return message
    
    def handle_documentation_commit(self, project_path: str, output_dir: str) -> bool:
        """处理文档提交的完整流程"""
        self.log("开始处理Git操作...")
        
        # 检查Git状态
        status = self.get_git_status()
        
        if not status.get('is_repo'):
            self.log("不在Git仓库中，跳过Git操作")
            return True
        
        if 'error' in status:
            self.log(f"Git状态检查失败: {status['error']}", "ERROR")
            return False
        
        # 添加文档文件
        output_path = Path(output_dir)
        relative_output = output_path.relative_to(self.project_root)
        
        add_patterns = [
            str(relative_output) + "/",
            "CLAUDE.md"  # 如果存在的话
        ]
        
        if not self.add_files(add_patterns):
            return False
        
        # 生成提交消息
        commit_msg = self.generate_commit_message(project_path, output_dir)
        
        # 提交更改
        if not self.commit_changes(commit_msg):
            return False
        
        # 推送更改
        if not self.push_changes():
            return False
        
        self.log("Git操作完成")
        return True


def main():
    parser = argparse.ArgumentParser(description="SuperClaude Git管理器")
    parser.add_argument("--project-root", required=True, help="项目根目录")
    parser.add_argument("--output-dir", required=True, help="文档输出目录")
    parser.add_argument("--project-path", required=True, help="被分析的项目路径")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 创建Git管理器
    git_manager = GitManager(args.project_root, args.verbose)
    
    # 处理文档提交
    success = git_manager.handle_documentation_commit(args.project_path, args.output_dir)
    
    if success:
        print("Git操作成功完成")
    else:
        print("Git操作失败", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()