#!/usr/bin/env python3
"""
SuperClaude Project Analyzer
项目结构分析和元数据提取工具
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


class ProjectAnalyzer:
    """项目分析器"""
    
    def __init__(self, project_path: str, verbose: bool = False):
        self.project_path = Path(project_path).resolve()
        self.verbose = verbose
        self.metadata = {}
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}", file=sys.stderr)
    
    def detect_project_type(self) -> str:
        """检测项目类型"""
        indicators = {
            'framework': [
                'setup.py', 'pyproject.toml', 'framework.py', 
                'core/__init__.py', 'lib/', 'src/core/'
            ],
            'library': [
                'setup.py', 'pyproject.toml', '__init__.py',
                'lib.py', 'package.json', 'cargo.toml'
            ],
            'application': [
                'main.py', 'app.py', 'index.js', 'package.json',
                'requirements.txt', 'Dockerfile'
            ],
            'plugin': [
                'plugin.py', 'extension.py', 'addon.py',
                'manifest.json', 'plugin.json'
            ]
        }
        
        scores = {proj_type: 0 for proj_type in indicators}
        
        for proj_type, files in indicators.items():
            for file_pattern in files:
                if self._find_files(file_pattern):
                    scores[proj_type] += 1
        
        # 特殊检测逻辑
        if self._find_files('SuperClaude') or self._find_files('CLAUDE.md'):
            scores['framework'] += 5
            
        if self._find_files('Core/') and self._find_files('*.md', count=5):
            scores['framework'] += 3
        
        detected_type = max(scores, key=scores.get)
        confidence = scores[detected_type] / sum(scores.values()) if sum(scores.values()) > 0 else 0
        
        self.log(f"检测到项目类型: {detected_type} (置信度: {confidence:.2f})")
        return detected_type
    
    def analyze_structure(self) -> Dict:
        """分析项目结构"""
        structure = {
            'directories': [],
            'key_files': [],
            'file_counts': {},
            'total_files': 0,
            'total_lines': 0
        }
        
        # 遍历项目目录
        for root, dirs, files in os.walk(self.project_path):
            # 跳过隐藏目录和常见的忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in 
                      ['__pycache__', 'node_modules', '.git', 'venv', 'env']]
            
            rel_root = Path(root).relative_to(self.project_path)
            
            if rel_root != Path('.'):
                structure['directories'].append(str(rel_root))
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = Path(root) / file
                rel_file_path = file_path.relative_to(self.project_path)
                
                # 统计文件类型
                ext = file_path.suffix.lower()
                structure['file_counts'][ext] = structure['file_counts'].get(ext, 0) + 1
                structure['total_files'] += 1
                
                # 识别关键文件
                if self._is_key_file(file):
                    structure['key_files'].append(str(rel_file_path))
                
                # 统计代码行数
                if self._is_code_file(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            structure['total_lines'] += lines
                    except Exception:
                        pass
        
        return structure
    
    def detect_technologies(self) -> List[str]:
        """检测使用的技术栈"""
        technologies = set()
        
        # Python项目检测
        if self._find_files('*.py'):
            technologies.add('Python')
            
            # 检测Python框架
            if self._find_files('requirements.txt') or self._find_files('pyproject.toml'):
                req_content = self._read_file_content('requirements.txt') or ''
                req_content += self._read_file_content('pyproject.toml') or ''
                
                frameworks = {
                    'Django': ['django'],
                    'Flask': ['flask'],
                    'FastAPI': ['fastapi'],
                    'Click': ['click'],
                    'Typer': ['typer'],
                }
                
                for framework, patterns in frameworks.items():
                    if any(pattern in req_content.lower() for pattern in patterns):
                        technologies.add(framework)
        
        # JavaScript/Node.js项目检测
        if self._find_files('package.json'):
            technologies.add('Node.js')
            
            package_content = self._read_file_content('package.json') or ''
            js_frameworks = {
                'React': ['react'],
                'Vue': ['vue'],
                'Angular': ['@angular'],
                'Express': ['express'],
            }
            
            for framework, patterns in js_frameworks.items():
                if any(pattern in package_content.lower() for pattern in patterns):
                    technologies.add(framework)
        
        # 其他技术检测
        if self._find_files('Dockerfile'):
            technologies.add('Docker')
        
        if self._find_files('docker-compose.yml'):
            technologies.add('Docker Compose')
            
        if self._find_files('*.go'):
            technologies.add('Go')
            
        if self._find_files('cargo.toml'):
            technologies.add('Rust')
        
        return sorted(list(technologies))
    
    def extract_metadata(self) -> Dict:
        """提取项目元数据"""
        metadata = {
            'name': self.project_path.name,
            'path': str(self.project_path),
            'type': self.detect_project_type(),
            'technologies': self.detect_technologies(),
            'structure': self.analyze_structure()
        }
        
        # 提取版本信息
        version = self._extract_version()
        if version:
            metadata['version'] = version
        
        # 提取描述信息
        description = self._extract_description()
        if description:
            metadata['description'] = description
        
        # 分析复杂度
        metadata['complexity'] = self._analyze_complexity(metadata['structure'])
        
        return metadata
    
    def _find_files(self, pattern: str, count: int = 1) -> bool:
        """查找匹配模式的文件"""
        found = 0
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if self._match_pattern(file, pattern) or self._match_pattern(Path(root).name, pattern):
                    found += 1
                    if found >= count:
                        return True
        return False
    
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """匹配文件名模式"""
        if '*' in pattern:
            # 简单的通配符匹配
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            return bool(re.match(regex_pattern, filename, re.IGNORECASE))
        else:
            return pattern.lower() in filename.lower()
    
    def _is_key_file(self, filename: str) -> bool:
        """判断是否是关键文件"""
        key_files = [
            'README.md', 'README.txt', 'CHANGELOG.md', 'LICENSE',
            'setup.py', 'pyproject.toml', 'requirements.txt',
            'package.json', 'cargo.toml', 'Dockerfile',
            'main.py', 'app.py', '__main__.py', '__init__.py',
            'CLAUDE.md', 'config.yaml', 'settings.py'
        ]
        
        return any(key_file.lower() in filename.lower() for key_file in key_files)
    
    def _is_code_file(self, file_path: Path) -> bool:
        """判断是否是代码文件"""
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', 
            '.cpp', '.c', '.h', '.hpp', '.php', '.rb', '.scala', '.kt'
        }
        return file_path.suffix.lower() in code_extensions
    
    def _read_file_content(self, filename: str) -> Optional[str]:
        """读取文件内容"""
        try:
            file_path = self.project_path / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        return None
    
    def _extract_version(self) -> Optional[str]:
        """提取版本信息"""
        # 从setup.py提取
        setup_content = self._read_file_content('setup.py') or ''
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_content)
        if version_match:
            return version_match.group(1)
        
        # 从package.json提取
        package_content = self._read_file_content('package.json') or ''
        if package_content:
            try:
                import json
                package_data = json.loads(package_content)
                return package_data.get('version')
            except:
                pass
        
        return None
    
    def _extract_description(self) -> Optional[str]:
        """提取项目描述"""
        readme_content = (self._read_file_content('README.md') or 
                         self._read_file_content('README.txt') or '')
        
        if readme_content:
            # 提取第一段作为描述
            lines = readme_content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and len(line) > 20:
                    return line[:200] + ('...' if len(line) > 200 else '')
        
        return None
    
    def _analyze_complexity(self, structure: Dict) -> Dict:
        """分析项目复杂度"""
        total_files = structure['total_files']
        total_dirs = len(structure['directories'])
        total_lines = structure['total_lines']
        
        # 计算复杂度分数 (0-1)
        file_complexity = min(total_files / 100, 1.0)
        dir_complexity = min(total_dirs / 20, 1.0)
        line_complexity = min(total_lines / 10000, 1.0)
        
        overall_complexity = (file_complexity + dir_complexity + line_complexity) / 3
        
        return {
            'file_complexity': file_complexity,
            'directory_complexity': dir_complexity,
            'line_complexity': line_complexity,
            'overall_complexity': overall_complexity,
            'level': self._complexity_level(overall_complexity)
        }
    
    def _complexity_level(self, complexity: float) -> str:
        """复杂度等级"""
        if complexity < 0.2:
            return 'Simple'
        elif complexity < 0.5:
            return 'Moderate'
        elif complexity < 0.8:
            return 'Complex'
        else:
            return 'Very Complex'


def main():
    parser = argparse.ArgumentParser(description="SuperClaude项目分析器")
    parser.add_argument("--project-path", required=True, help="项目路径")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--project-type", default="auto", help="项目类型")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = ProjectAnalyzer(args.project_path, args.verbose)
    
    # 执行分析
    metadata = analyzer.extract_metadata()
    
    # 如果指定了项目类型，覆盖检测结果
    if args.project_type != "auto":
        metadata['type'] = args.project_type
    
    # 保存元数据
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_file = output_dir / "project-metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"项目分析完成，元数据已保存到: {metadata_file}")
    
    # 输出摘要信息
    if args.verbose:
        print(f"\n项目摘要:")
        print(f"  名称: {metadata['name']}")
        print(f"  类型: {metadata['type']}")
        print(f"  技术栈: {', '.join(metadata['technologies'])}")
        print(f"  文件数: {metadata['structure']['total_files']}")
        print(f"  代码行数: {metadata['structure']['total_lines']}")
        print(f"  复杂度: {metadata['complexity']['level']}")


if __name__ == "__main__":
    main()