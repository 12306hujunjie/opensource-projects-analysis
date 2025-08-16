#!/usr/bin/env python3
"""
SuperClaude Report Generator
分析报告生成工具
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str, verbose: bool = False):
        self.output_dir = Path(output_dir).resolve()
        self.verbose = verbose
        
        # 加载项目元数据
        metadata_file = self.output_dir / "project-metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
    
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}", file=sys.stderr)
    
    def generate_statistics(self) -> Dict:
        """生成统计信息"""
        stats = {
            'document_count': 0,
            'total_lines': 0,
            'level_distribution': {},
            'average_lines_per_doc': 0,
            'largest_document': {'name': '', 'lines': 0},
            'smallest_document': {'name': '', 'lines': float('inf')},
            'analysis_coverage': {}
        }
        
        # 扫描所有Markdown文档
        md_files = list(self.output_dir.glob("*.md"))
        stats['document_count'] = len(md_files)
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    stats['total_lines'] += lines
                
                # 更新最大和最小文档
                if lines > stats['largest_document']['lines']:
                    stats['largest_document'] = {'name': md_file.name, 'lines': lines}
                
                if lines < stats['smallest_document']['lines']:
                    stats['smallest_document'] = {'name': md_file.name, 'lines': lines}
                
                # 统计级别分布
                level_match = self._extract_level(md_file.name)
                if level_match:
                    level = f"L{level_match}"
                    stats['level_distribution'][level] = stats['level_distribution'].get(level, 0) + 1
                
            except Exception as e:
                self.log(f"处理文件 {md_file.name} 时出错: {e}", "ERROR")
        
        # 计算平均行数
        if stats['document_count'] > 0:
            stats['average_lines_per_doc'] = stats['total_lines'] // stats['document_count']
        
        # 重置最小文档（如果没有找到文件）
        if stats['smallest_document']['lines'] == float('inf'):
            stats['smallest_document'] = {'name': '', 'lines': 0}
        
        # 分析覆盖度统计
        stats['analysis_coverage'] = self._calculate_coverage()
        
        return stats
    
    def _extract_level(self, filename: str) -> Optional[int]:
        """从文件名提取级别"""
        import re
        match = re.search(r'L(\d+)', filename)
        return int(match.group(1)) if match else None
    
    def _calculate_coverage(self) -> Dict:
        """计算分析覆盖度"""
        coverage = {
            'architecture': False,
            'security': False,
            'performance': False,
            'quality': False,
            'documentation': False
        }
        
        # 检查文档文件
        md_files = list(self.output_dir.glob("*.md"))
        
        for md_file in md_files:
            filename_lower = md_file.name.lower()
            
            if 'architecture' in filename_lower or '架构' in filename_lower:
                coverage['architecture'] = True
            if 'security' in filename_lower or '安全' in filename_lower:
                coverage['security'] = True
            if 'performance' in filename_lower or '性能' in filename_lower:
                coverage['performance'] = True
            if 'quality' in filename_lower or '质量' in filename_lower:
                coverage['quality'] = True
            if 'doc' in filename_lower or 'readme' in filename_lower:
                coverage['documentation'] = True
        
        return coverage
    
    def generate_summary_report(self) -> str:
        """生成摘要报告"""
        stats = self.generate_statistics()
        
        report_lines = []
        
        # 基本统计
        report_lines.append(f"**文档数量**: {stats['document_count']}")
        report_lines.append(f"**总行数**: {stats['total_lines']:,}")
        report_lines.append(f"**平均行数**: {stats['average_lines_per_doc']}")
        
        # 级别分布
        if stats['level_distribution']:
            report_lines.append("")
            report_lines.append("**级别分布**:")
            for level in sorted(stats['level_distribution'].keys()):
                count = stats['level_distribution'][level]
                report_lines.append(f"- {level}: {count}个文档")
        
        # 文档大小统计
        if stats['largest_document']['name']:
            report_lines.append("")
            report_lines.append("**文档规模**:")
            report_lines.append(f"- 最大文档: {stats['largest_document']['name']} ({stats['largest_document']['lines']:,}行)")
            report_lines.append(f"- 最小文档: {stats['smallest_document']['name']} ({stats['smallest_document']['lines']:,}行)")
        
        # 分析覆盖度
        coverage = stats['analysis_coverage']
        covered_areas = [area for area, covered in coverage.items() if covered]
        
        if covered_areas:
            report_lines.append("")
            report_lines.append("**分析覆盖领域**:")
            area_names = {
                'architecture': '架构设计',
                'security': '安全分析',
                'performance': '性能分析',
                'quality': '质量评估',
                'documentation': '文档完善'
            }
            
            for area in covered_areas:
                area_name = area_names.get(area, area)
                report_lines.append(f"- ✅ {area_name}")
            
            uncovered_areas = [area for area, covered in coverage.items() if not covered]
            for area in uncovered_areas:
                area_name = area_names.get(area, area)
                report_lines.append(f"- ⚪ {area_name}")
        
        # 项目元数据统计
        if self.metadata:
            report_lines.append("")
            report_lines.append("**项目信息**:")
            
            if 'type' in self.metadata:
                report_lines.append(f"- 项目类型: {self.metadata['type']}")
            
            if 'technologies' in self.metadata:
                tech_list = ', '.join(self.metadata['technologies'])
                report_lines.append(f"- 技术栈: {tech_list}")
            
            if 'complexity' in self.metadata:
                complexity = self.metadata['complexity']
                if 'level' in complexity:
                    report_lines.append(f"- 复杂度: {complexity['level']}")
        
        return '\n'.join(report_lines)
    
    def generate_quality_report(self) -> Dict:
        """生成质量报告"""
        stats = self.generate_statistics()
        
        quality_report = {
            'overall_score': 0,
            'completeness_score': 0,
            'depth_score': 0,
            'consistency_score': 0,
            'issues': [],
            'recommendations': []
        }
        
        # 完整性评分 (40%)
        completeness_score = 0
        
        # 检查文档数量
        if stats['document_count'] >= 5:
            completeness_score += 30
        elif stats['document_count'] >= 3:
            completeness_score += 20
        else:
            completeness_score += 10
            quality_report['issues'].append("文档数量较少，建议增加更多分析文档")
        
        # 检查覆盖度
        coverage = stats['analysis_coverage']
        covered_count = sum(1 for covered in coverage.values() if covered)
        completeness_score += (covered_count / len(coverage)) * 70
        
        quality_report['completeness_score'] = min(completeness_score, 100)
        
        # 深度评分 (35%)
        depth_score = 0
        
        # 基于总行数评估深度
        if stats['total_lines'] >= 5000:
            depth_score = 100
        elif stats['total_lines'] >= 2000:
            depth_score = 80
        elif stats['total_lines'] >= 1000:
            depth_score = 60
        else:
            depth_score = 40
            quality_report['issues'].append("分析深度不足，建议增加更详细的分析内容")
        
        quality_report['depth_score'] = depth_score
        
        # 一致性评分 (25%)
        consistency_score = 100
        
        # 检查文档大小一致性
        if stats['document_count'] > 1:
            largest = stats['largest_document']['lines']
            smallest = stats['smallest_document']['lines']
            
            if largest > 0 and smallest > 0:
                ratio = smallest / largest
                if ratio < 0.3:  # 最小文档不到最大文档的30%
                    consistency_score -= 20
                    quality_report['issues'].append("文档长度差异较大，建议平衡各文档的内容深度")
        
        quality_report['consistency_score'] = consistency_score
        
        # 计算总体评分
        quality_report['overall_score'] = (
            quality_report['completeness_score'] * 0.4 +
            quality_report['depth_score'] * 0.35 +
            quality_report['consistency_score'] * 0.25
        )
        
        # 生成建议
        if quality_report['overall_score'] >= 90:
            quality_report['recommendations'].append("分析质量优秀，建议保持当前标准")
        elif quality_report['overall_score'] >= 70:
            quality_report['recommendations'].append("分析质量良好，可以考虑在某些方面进一步深化")
        else:
            quality_report['recommendations'].append("分析质量需要改进，建议增加更多内容和深度")
        
        return quality_report


def main():
    parser = argparse.ArgumentParser(description="SuperClaude报告生成器")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--format", choices=['summary', 'quality', 'both'], default='summary', help="报告格式")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 创建报告生成器
    generator = ReportGenerator(args.output_dir, args.verbose)
    
    if args.format in ['summary', 'both']:
        summary = generator.generate_summary_report()
        print(summary)
    
    if args.format in ['quality', 'both']:
        quality_report = generator.generate_quality_report()
        
        if args.format == 'both':
            print("\n" + "="*50)
            print("质量评估报告")
            print("="*50)
        
        print(f"总体评分: {quality_report['overall_score']:.1f}/100")
        print(f"完整性: {quality_report['completeness_score']:.1f}/100")
        print(f"深度: {quality_report['depth_score']:.1f}/100")
        print(f"一致性: {quality_report['consistency_score']:.1f}/100")
        
        if quality_report['issues']:
            print("\n发现的问题:")
            for issue in quality_report['issues']:
                print(f"- {issue}")
        
        if quality_report['recommendations']:
            print("\n改进建议:")
            for rec in quality_report['recommendations']:
                print(f"- {rec}")


if __name__ == "__main__":
    main()