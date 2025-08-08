# CrewAI 安全性深度分析

## 概述

本文档深入分析 CrewAI 框架的安全特性和潜在风险点，基于对框架核心实现的源码级分析，提供全面的安全评估、威胁模型和最佳实践指导。通过系统性的安全分析，帮助开发者构建安全、可靠的多智能体协作系统。

## 1. 安全架构分析

### 1.1 整体安全架构

```python
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
import hashlib
import secrets
import logging
from pathlib import Path
import os
import re

class SecurityLevel(Enum):
    """安全级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatCategory(Enum):
    """威胁类别枚举"""
    INJECTION = "injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXPOSURE = "data_exposure"
    DENIAL_OF_SERVICE = "denial_of_service"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CODE_EXECUTION = "code_execution"

@dataclass
class SecurityThreat:
    """安全威胁定义"""
    id: str
    category: ThreatCategory
    level: SecurityLevel
    description: str
    attack_vectors: List[str]
    mitigation_strategies: List[str]
    affected_components: List[str]
    likelihood: float  # 0.0 - 1.0
    impact: float     # 0.0 - 1.0
    risk_score: float # likelihood * impact

class CrewAISecurityAnalyzer:
    """CrewAI 安全分析器"""
    
    def __init__(self):
        self.threat_database = self._initialize_threat_database()
        self.security_policies = self._initialize_security_policies()
        self.audit_log: List[Dict] = []
        self.risk_assessments: List[Dict] = []
        
        # 安全配置
        self.security_config = {
            'input_validation': {
                'max_input_length': 10000,
                'allowed_file_types': ['.txt', '.json', '.csv', '.md'],
                'blocked_patterns': [
                    r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # XSS
                    r'(union|select|insert|update|delete|drop)\s+',      # SQL injection
                    r'(exec|eval|system|shell_exec)\s*\(',               # Code execution
                    r'\.\.\/|\.\.\\',                                    # Path traversal
                    r'(rm\s+-rf|format\s+c:)',                          # Dangerous commands
                ],
                'sanitize_html': True,
                'escape_sql': True
            },
            'file_operations': {
                'allowed_paths': [],  # 允许的文件路径前缀
                'blocked_paths': ['/etc', '/root', '/home', 'C:\\Windows'],
                'max_file_size': 10 * 1024 * 1024,  # 10MB
                'scan_for_malware': True
            },
            'api_security': {
                'rate_limiting': {
                    'requests_per_minute': 100,
                    'burst_limit': 20
                },
                'authentication_required': True,
                'encrypt_communications': True,
                'validate_certificates': True
            }
        }
    
    def _initialize_threat_database(self) -> List[SecurityThreat]:
        """初始化威胁数据库"""
        
        return [
            SecurityThreat(
                id="CREW-001",
                category=ThreatCategory.INJECTION,
                level=SecurityLevel.HIGH,
                description="任务描述中的恶意代码注入",
                attack_vectors=[
                    "在task.description中嵌入恶意脚本",
                    "通过context参数传递恶意代码",
                    "利用模板注入执行任意代码"
                ],
                mitigation_strategies=[
                    "严格输入验证和sanitization",
                    "使用参数化模板",
                    "限制代码执行上下文",
                    "实施内容安全策略(CSP)"
                ],
                affected_components=["Task", "Agent", "Template Engine"],
                likelihood=0.7,
                impact=0.8,
                risk_score=0.56
            ),
            
            SecurityThreat(
                id="CREW-002",
                category=ThreatCategory.UNAUTHORIZED_ACCESS,
                level=SecurityLevel.CRITICAL,
                description="未授权访问敏感文件和系统资源",
                attack_vectors=[
                    "通过output_file参数访问任意文件",
                    "利用工具执行未授权系统命令",
                    "绕过文件路径验证机制"
                ],
                mitigation_strategies=[
                    "严格的文件路径验证",
                    "实施最小权限原则",
                    "沙箱环境隔离",
                    "文件访问审计日志"
                ],
                affected_components=["FileWriterTool", "BaseTool", "Task.output_file"],
                likelihood=0.6,
                impact=0.9,
                risk_score=0.54
            ),
            
            SecurityThreat(
                id="CREW-003",
                category=ThreatCategory.DATA_EXPOSURE,
                level=SecurityLevel.HIGH,
                description="敏感数据泄露和隐私侵犯",
                attack_vectors=[
                    "通过日志记录泄露敏感信息",
                    "在错误消息中暴露内部信息",
                    "缓存中存储敏感数据",
                    "通过API响应泄露数据"
                ],
                mitigation_strategies=[
                    "敏感数据脱敏和掩码",
                    "安全的日志记录实践",
                    "加密敏感数据存储",
                    "实施数据分类和保护策略"
                ],
                affected_components=["Logging", "Cache", "API", "Error Handling"],
                likelihood=0.8,
                impact=0.7,
                risk_score=0.56
            ),
            
            SecurityThreat(
                id="CREW-004",
                category=ThreatCategory.CODE_EXECUTION,
                level=SecurityLevel.CRITICAL,
                description="远程代码执行和系统命令注入",
                attack_vectors=[
                    "通过自定义工具执行恶意代码",
                    "利用eval()或exec()函数",
                    "操作系统命令注入",
                    "Python代码注入攻击"
                ],
                mitigation_strategies=[
                    "禁用危险函数",
                    "沙箱环境执行",
                    "严格的工具验证",
                    "代码签名和验证"
                ],
                affected_components=["BaseTool", "Custom Tools", "Python Runtime"],
                likelihood=0.5,
                impact=1.0,
                risk_score=0.50
            ),
            
            SecurityThreat(
                id="CREW-005",
                category=ThreatCategory.DENIAL_OF_SERVICE,
                level=SecurityLevel.MEDIUM,
                description="拒绝服务攻击和资源耗尽",
                attack_vectors=[
                    "创建大量并发任务",
                    "提交超大输入数据",
                    "触发无限循环或递归",
                    "消耗过量内存资源"
                ],
                mitigation_strategies=[
                    "实施速率限制",
                    "资源使用监控",
                    "超时机制",
                    "输入大小限制"
                ],
                affected_components=["Task Executor", "Memory Management", "API"],
                likelihood=0.7,
                impact=0.6,
                risk_score=0.42
            )
        ]
    
    def _initialize_security_policies(self) -> Dict[str, Any]:
        """初始化安全策略"""
        
        return {
            'data_classification': {
                'public': {'encryption': False, 'access_logging': False},
                'internal': {'encryption': True, 'access_logging': True},
                'confidential': {'encryption': True, 'access_logging': True, 'approval_required': True},
                'restricted': {'encryption': True, 'access_logging': True, 'approval_required': True, 'audit_required': True}
            },
            'access_control': {
                'authentication_methods': ['api_key', 'oauth2', 'certificate'],
                'authorization_model': 'rbac',  # Role-Based Access Control
                'session_timeout': 3600,  # 1 hour
                'multi_factor_required': False
            },
            'audit_requirements': {
                'log_all_access': True,
                'log_data_modifications': True,
                'log_security_events': True,
                'retention_period_days': 365
            }
        }
    
    def analyze_security_risks(self, component: str = None) -> Dict[str, Any]:
        """分析安全风险"""
        
        relevant_threats = self.threat_database
        
        if component:
            relevant_threats = [
                threat for threat in self.threat_database
                if component in threat.affected_components
            ]
        
        # 计算风险统计
        risk_summary = {
            'total_threats': len(relevant_threats),
            'critical_risks': len([t for t in relevant_threats if t.level == SecurityLevel.CRITICAL]),
            'high_risks': len([t for t in relevant_threats if t.level == SecurityLevel.HIGH]),
            'medium_risks': len([t for t in relevant_threats if t.level == SecurityLevel.MEDIUM]),
            'low_risks': len([t for t in relevant_threats if t.level == SecurityLevel.LOW]),
            'average_risk_score': sum(t.risk_score for t in relevant_threats) / len(relevant_threats) if relevant_threats else 0,
            'top_risks': sorted(relevant_threats, key=lambda x: x.risk_score, reverse=True)[:5]
        }
        
        # 生成风险热图数据
        risk_heatmap = {}
        for threat in relevant_threats:
            category = threat.category.value
            if category not in risk_heatmap:
                risk_heatmap[category] = {'count': 0, 'total_risk': 0.0}
            
            risk_heatmap[category]['count'] += 1
            risk_heatmap[category]['total_risk'] += threat.risk_score
        
        # 计算平均风险
        for category in risk_heatmap:
            count = risk_heatmap[category]['count']
            risk_heatmap[category]['average_risk'] = risk_heatmap[category]['total_risk'] / count
        
        return {
            'component': component or 'All Components',
            'risk_summary': risk_summary,
            'risk_heatmap': risk_heatmap,
            'detailed_threats': [
                {
                    'id': threat.id,
                    'category': threat.category.value,
                    'level': threat.level.value,
                    'description': threat.description,
                    'risk_score': threat.risk_score,
                    'mitigation_strategies': threat.mitigation_strategies
                }
                for threat in relevant_threats
            ],
            'recommendations': self._generate_security_recommendations(relevant_threats)
        }
    
    def _generate_security_recommendations(self, threats: List[SecurityThreat]) -> List[str]:
        """基于威胁分析生成安全建议"""
        
        recommendations = set()
        
        for threat in threats:
            if threat.level in [SecurityLevel.CRITICAL, SecurityLevel.HIGH]:
                recommendations.update(threat.mitigation_strategies)
        
        # 添加通用安全建议
        general_recommendations = [
            "定期进行安全代码审查",
            "实施自动化安全测试",
            "建立安全事件响应流程",
            "定期更新依赖组件",
            "实施最小权限原则",
            "启用全面的审计日志"
        ]
        
        recommendations.update(general_recommendations)
        
        return sorted(list(recommendations))
```

### 1.2 核心组件安全评估

```python
class ComponentSecurityAssessment:
    """组件安全评估"""
    
    def __init__(self, security_analyzer: CrewAISecurityAnalyzer):
        self.analyzer = security_analyzer
    
    def assess_task_security(self) -> Dict[str, Any]:
        """Task组件安全评估"""
        
        assessment = {
            'component': 'Task',
            'security_features': {
                'input_validation': {
                    'description_validation': True,  # 任务描述验证
                    'output_file_validation': True,  # 输出文件路径验证
                    'path_traversal_protection': True,  # 路径遍历防护
                    'template_injection_protection': False  # 模板注入防护需要改进
                },
                'access_control': {
                    'agent_assignment_validation': True,
                    'tool_access_restriction': True,
                    'context_isolation': False  # 上下文隔离需要改进
                },
                'data_protection': {
                    'sensitive_data_masking': False,  # 敏感数据脱敏
                    'output_sanitization': False,    # 输出清理
                    'secure_file_handling': True     # 安全文件处理
                }
            },
            'vulnerabilities': [
                {
                    'id': 'TASK-001',
                    'description': '任务描述中可能包含恶意内容',
                    'severity': SecurityLevel.MEDIUM,
                    'mitigation': '实施严格的输入验证和内容过滤'
                },
                {
                    'id': 'TASK-002',
                    'description': '输出文件路径可能被恶意利用',
                    'severity': SecurityLevel.HIGH,
                    'mitigation': '增强路径验证和沙箱限制'
                },
                {
                    'id': 'TASK-003',
                    'description': '上下文数据缺乏加密保护',
                    'severity': SecurityLevel.MEDIUM,
                    'mitigation': '对敏感上下文数据进行加密存储'
                }
            ],
            'recommendations': [
                '实施输入验证框架',
                '添加输出内容过滤',
                '增强文件操作安全控制',
                '实施任务执行沙箱',
                '添加敏感数据检测和保护'
            ]
        }
        
        return assessment
    
    def assess_agent_security(self) -> Dict[str, Any]:
        """Agent组件安全评估"""
        
        return {
            'component': 'Agent',
            'security_features': {
                'authentication': {
                    'role_based_access': True,
                    'capability_restrictions': True,
                    'tool_authorization': False  # 工具授权需要改进
                },
                'execution_control': {
                    'resource_limits': False,     # 资源限制
                    'timeout_enforcement': False,  # 超时强制执行
                    'sandbox_execution': False    # 沙箱执行
                },
                'communication_security': {
                    'llm_api_encryption': True,   # LLM API加密
                    'secure_context_passing': False,  # 安全上下文传递
                    'audit_logging': False       # 审计日志
                }
            },
            'vulnerabilities': [
                {
                    'id': 'AGENT-001',
                    'description': 'Agent可能执行恶意工具调用',
                    'severity': SecurityLevel.HIGH,
                    'mitigation': '实施工具白名单和权限验证'
                },
                {
                    'id': 'AGENT-002', 
                    'description': 'LLM响应可能包含恶意内容',
                    'severity': SecurityLevel.MEDIUM,
                    'mitigation': '对LLM输出进行安全过滤和验证'
                }
            ],
            'recommendations': [
                '实施严格的工具访问控制',
                '添加Agent执行监控',
                '增强LLM交互安全性',
                '实施Agent沙箱隔离',
                '添加行为异常检测'
            ]
        }
    
    def assess_tool_security(self) -> Dict[str, Any]:
        """工具安全评估"""
        
        return {
            'component': 'Tools',
            'security_features': {
                'authorization': {
                    'permission_checking': False,   # 权限检查
                    'capability_validation': False, # 能力验证
                    'usage_auditing': False        # 使用审计
                },
                'input_validation': {
                    'parameter_validation': True,   # 参数验证
                    'type_checking': True,         # 类型检查
                    'range_validation': False      # 范围验证
                },
                'execution_safety': {
                    'sandbox_execution': False,    # 沙箱执行
                    'resource_limiting': False,    # 资源限制
                    'timeout_control': False       # 超时控制
                }
            },
            'vulnerabilities': [
                {
                    'id': 'TOOL-001',
                    'description': '自定义工具可能执行危险操作',
                    'severity': SecurityLevel.CRITICAL,
                    'mitigation': '实施工具代码审查和沙箱执行'
                },
                {
                    'id': 'TOOL-002',
                    'description': '工具参数可能被注入攻击利用',
                    'severity': SecurityLevel.HIGH,
                    'mitigation': '严格的参数验证和清理'
                }
            ],
            'recommendations': [
                '建立工具审查流程',
                '实施工具权限管理',
                '添加工具执行监控',
                '创建安全工具开发指南',
                '实施工具签名验证'
            ]
        }
```

## 2. 输入验证与数据清理

### 2.1 全面输入验证框架

```python
import re
import html
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote, unquote
import bleach
from pathlib import Path, PurePath

class InputValidator:
    """输入验证器"""
    
    def __init__(self):
        # 恶意模式检测
        self.malicious_patterns = {
            'xss': [
                r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
                r'javascript:',
                r'on\w+\s*=',
                r'<iframe\b[^>]*>',
                r'<object\b[^>]*>',
                r'<embed\b[^>]*>'
            ],
            'sql_injection': [
                r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
                r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
                r'(\'|\"|`|;|--|\/\*|\*\/)',
                r'(\b(SLEEP|BENCHMARK|WAITFOR)\b)'
            ],
            'code_injection': [
                r'(\b(eval|exec|system|shell_exec|passthru|proc_open)\s*\()',
                r'(__import__|getattr|setattr|delattr)\s*\(',
                r'(compile|globals|locals|vars)\s*\(',
                r'\${.*}',  # Template injection
                r'<%.*%>'   # Template injection
            ],
            'path_traversal': [
                r'\.\.\/|\.\.\\',
                r'\/etc\/passwd',
                r'\/proc\/self\/environ',
                r'C:\\Windows\\System32'
            ],
            'command_injection': [
                r'(\||&|;|`|\$\(|\${)',
                r'(rm\s+-rf|format\s+c:|del\s+\/[qsf])',
                r'(wget|curl|nc|netcat)\s+',
                r'(cat|type|more|less)\s+\/\w+'
            ]
        }
        
        # 允许的HTML标签和属性
        self.allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li']
        self.allowed_attributes = {'*': ['class', 'id']}
        
    def validate_task_input(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证任务输入数据"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'sanitized_data': {}
        }
        
        try:
            # 验证任务描述
            if 'description' in task_data:
                desc_result = self._validate_text_input(
                    task_data['description'], 
                    'task_description',
                    max_length=10000
                )
                validation_result['sanitized_data']['description'] = desc_result['sanitized']
                validation_result['errors'].extend(desc_result['errors'])
                validation_result['warnings'].extend(desc_result['warnings'])
            
            # 验证期望输出
            if 'expected_output' in task_data:
                output_result = self._validate_text_input(
                    task_data['expected_output'],
                    'expected_output',
                    max_length=5000
                )
                validation_result['sanitized_data']['expected_output'] = output_result['sanitized']
                validation_result['errors'].extend(output_result['errors'])
            
            # 验证输出文件路径
            if 'output_file' in task_data and task_data['output_file']:
                path_result = self._validate_file_path(task_data['output_file'])
                validation_result['sanitized_data']['output_file'] = path_result['sanitized']
                validation_result['errors'].extend(path_result['errors'])
            
            # 验证工具参数
            if 'tools' in task_data:
                tools_result = self._validate_tools_config(task_data['tools'])
                validation_result['sanitized_data']['tools'] = tools_result['sanitized']
                validation_result['errors'].extend(tools_result['errors'])
            
            # 验证上下文数据
            if 'context' in task_data:
                context_result = self._validate_context_data(task_data['context'])
                validation_result['sanitized_data']['context'] = context_result['sanitized']
                validation_result['errors'].extend(context_result['errors'])
            
            validation_result['valid'] = len(validation_result['errors']) == 0
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _validate_text_input(self, text: str, field_name: str, 
                           max_length: int = 1000) -> Dict[str, Any]:
        """验证文本输入"""
        
        result = {
            'sanitized': text,
            'errors': [],
            'warnings': []
        }
        
        # 长度检查
        if len(text) > max_length:
            result['errors'].append(f"{field_name} exceeds maximum length of {max_length}")
            return result
        
        # 恶意模式检测
        for pattern_type, patterns in self.malicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    result['errors'].append(f"Potentially malicious {pattern_type} pattern detected in {field_name}")
        
        # HTML清理
        if '<' in text and '>' in text:
            cleaned_text = bleach.clean(text, tags=self.allowed_tags, attributes=self.allowed_attributes)
            if cleaned_text != text:
                result['warnings'].append(f"HTML content sanitized in {field_name}")
                result['sanitized'] = cleaned_text
        
        # URL编码检查
        if '%' in text:
            try:
                decoded = unquote(text)
                # 再次检查解码后的内容
                for pattern_type, patterns in self.malicious_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, decoded, re.IGNORECASE):
                            result['errors'].append(f"URL-encoded malicious {pattern_type} pattern detected")
            except Exception:
                pass
        
        return result
    
    def _validate_file_path(self, file_path: str) -> Dict[str, Any]:
        """验证文件路径"""
        
        result = {
            'sanitized': file_path,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 基础路径检查
            path = Path(file_path)
            
            # 检查路径遍历
            if '..' in str(path) or str(path).startswith('/'):
                result['errors'].append("Path traversal attempt detected")
                return result
            
            # 检查危险路径
            dangerous_paths = [
                '/etc', '/root', '/home', '/usr/bin', '/sys', '/proc',
                'C:\\Windows', 'C:\\Program Files', 'C:\\Users'
            ]
            
            for dangerous in dangerous_paths:
                if dangerous.lower() in str(path).lower():
                    result['errors'].append(f"Access to restricted path attempted: {dangerous}")
            
            # 检查文件扩展名
            allowed_extensions = ['.txt', '.json', '.csv', '.md', '.log', '.xml', '.yaml', '.yml']
            if path.suffix.lower() not in allowed_extensions:
                result['warnings'].append(f"Potentially unsafe file extension: {path.suffix}")
            
            # 规范化路径
            try:
                normalized = path.resolve()
                result['sanitized'] = str(normalized)
            except Exception as e:
                result['errors'].append(f"Path normalization failed: {str(e)}")
        
        except Exception as e:
            result['errors'].append(f"Path validation error: {str(e)}")
        
        return result
    
    def _validate_tools_config(self, tools: List[Any]) -> Dict[str, Any]:
        """验证工具配置"""
        
        result = {
            'sanitized': [],
            'errors': [],
            'warnings': []
        }
        
        for i, tool in enumerate(tools):
            # 检查工具类型
            tool_name = getattr(tool, '__class__', {}).get('__name__', 'Unknown')
            
            # 危险工具列表
            dangerous_tools = [
                'SystemCommand', 'ShellTool', 'FileWriter', 'FileReader',
                'DatabaseTool', 'NetworkTool', 'ProcessTool'
            ]
            
            if any(dangerous in tool_name for dangerous in dangerous_tools):
                result['warnings'].append(f"Potentially dangerous tool detected: {tool_name}")
            
            # 验证工具参数（如果有的话）
            if hasattr(tool, 'args') and tool.args:
                for arg_name, arg_value in tool.args.items():
                    if isinstance(arg_value, str):
                        arg_result = self._validate_text_input(arg_value, f"tool_{i}_{arg_name}")
                        if arg_result['errors']:
                            result['errors'].extend(arg_result['errors'])
            
            result['sanitized'].append(tool)
        
        return result
    
    def _validate_context_data(self, context: Any) -> Dict[str, Any]:
        """验证上下文数据"""
        
        result = {
            'sanitized': context,
            'errors': [],
            'warnings': []
        }
        
        # 检查上下文大小
        try:
            context_str = json.dumps(context) if not isinstance(context, str) else context
            if len(context_str) > 100000:  # 100KB limit
                result['errors'].append("Context data exceeds size limit")
            
            # 检查敏感信息模式
            sensitive_patterns = [
                r'\b(?:password|passwd|pwd|token|key|secret|api_key)\s*[:=]\s*\S+',
                r'\b(?:ssn|social.security|credit.card|account.number)\b',
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card pattern
                r'\b\d{3}-\d{2}-\d{4}\b'  # SSN pattern
            ]
            
            for pattern in sensitive_patterns:
                if re.search(pattern, context_str, re.IGNORECASE):
                    result['warnings'].append("Potentially sensitive information detected in context")
            
        except Exception as e:
            result['errors'].append(f"Context validation error: {str(e)}")
        
        return result
```

### 2.2 高级数据清理和脱敏

```python
class DataSanitizer:
    """数据清理和脱敏器"""
    
    def __init__(self):
        # 敏感数据模式
        self.sensitive_patterns = {
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'api_key': r'\b[A-Za-z0-9]{32,}\b',
            'password': r'(?i)(password|pwd|pass|secret|key)\s*[:=]\s*\S+',
            'token': r'\b[A-Za-z0-9+/]{20,}={0,2}\b',  # Base64 tokens
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'url_with_auth': r'https?://[^:]+:[^@]+@[^/]+',
        }
        
        # 脱敏替换策略
        self.masking_strategies = {
            'credit_card': lambda m: '**** **** **** ' + m.group()[-4:],
            'ssn': lambda m: '***-**-' + m.group()[-4:],
            'email': lambda m: m.group()[:2] + '*' * (len(m.group().split('@')[0]) - 2) + '@' + m.group().split('@')[1],
            'phone': lambda m: '***-***-' + m.group()[-4:],
            'api_key': lambda m: m.group()[:8] + '*' * (len(m.group()) - 8),
            'password': lambda m: m.group().split(':')[0] + ': [REDACTED]',
            'token': lambda m: m.group()[:10] + '*' * (len(m.group()) - 10),
            'ip_address': lambda m: '.'.join(m.group().split('.')[:-1]) + '.***',
            'url_with_auth': lambda m: re.sub(r'//[^:]+:[^@]+@', '//[REDACTED]@', m.group()),
        }
    
    def sanitize_for_logging(self, data: Any) -> str:
        """为日志记录清理数据"""
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if self._is_sensitive_key(key):
                    sanitized[key] = '[REDACTED]'
                else:
                    sanitized[key] = self.sanitize_for_logging(value)
            data_str = json.dumps(sanitized, default=str)
        else:
            data_str = str(data)
        
        # 应用敏感数据脱敏
        for pattern_name, pattern in self.sensitive_patterns.items():
            if pattern_name in self.masking_strategies:
                data_str = re.sub(pattern, self.masking_strategies[pattern_name], data_str)
        
        return data_str
    
    def sanitize_for_storage(self, data: Any) -> Any:
        """为存储清理数据"""
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if self._is_sensitive_key(key):
                    # 敏感字段加密或脱敏
                    sanitized[key] = self._encrypt_sensitive_data(str(value))
                else:
                    sanitized[key] = self.sanitize_for_storage(value)
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_for_storage(item) for item in data]
        elif isinstance(data, str):
            return self._sanitize_string_for_storage(data)
        else:
            return data
    
    def sanitize_for_output(self, data: Any) -> Any:
        """为输出清理数据"""
        
        if isinstance(data, str):
            # HTML转义
            data = html.escape(data)
            
            # 应用敏感数据脱敏
            for pattern_name, pattern in self.sensitive_patterns.items():
                if pattern_name in self.masking_strategies:
                    data = re.sub(pattern, self.masking_strategies[pattern_name], data)
        
        elif isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                sanitized[key] = self.sanitize_for_output(value)
            return sanitized
        
        elif isinstance(data, list):
            return [self.sanitize_for_output(item) for item in data]
        
        return data
    
    def _is_sensitive_key(self, key: str) -> bool:
        """检查键名是否为敏感字段"""
        
        sensitive_keys = [
            'password', 'pwd', 'pass', 'secret', 'key', 'token', 
            'api_key', 'auth', 'credential', 'private', 'ssn',
            'social_security', 'credit_card', 'account_number'
        ]
        
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in sensitive_keys)
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感数据（简化实现）"""
        
        # 这里应该使用真正的加密算法
        # 为了示例，我们使用简单的哈希
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()[:16] + '[ENCRYPTED]'
    
    def _sanitize_string_for_storage(self, text: str) -> str:
        """为存储清理字符串"""
        
        # 移除潜在的恶意内容
        for pattern_type, patterns in {
            'script_tags': [r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>'],
            'dangerous_functions': [r'(eval|exec|system|shell_exec)\s*\('],
        }.items():
            for pattern in patterns:
                text = re.sub(pattern, '[REMOVED]', text, flags=re.IGNORECASE)
        
        return text

class SecureDataHandler:
    """安全数据处理器"""
    
    def __init__(self):
        self.sanitizer = DataSanitizer()
        self.validator = InputValidator()
        
        # 数据分类配置
        self.data_classifications = {
            'public': {'encryption': False, 'masking': False},
            'internal': {'encryption': True, 'masking': True},
            'confidential': {'encryption': True, 'masking': True, 'audit': True},
            'restricted': {'encryption': True, 'masking': True, 'audit': True, 'approval': True}
        }
    
    def handle_task_data(self, task_data: Dict[str, Any], 
                        classification: str = 'internal') -> Dict[str, Any]:
        """安全处理任务数据"""
        
        # 验证输入
        validation_result = self.validator.validate_task_input(task_data)
        if not validation_result['valid']:
            raise ValueError(f"Invalid input data: {validation_result['errors']}")
        
        # 获取分类策略
        strategy = self.data_classifications.get(classification, self.data_classifications['internal'])
        
        # 处理数据
        processed_data = validation_result['sanitized_data']
        
        if strategy['masking']:
            processed_data = self.sanitizer.sanitize_for_storage(processed_data)
        
        if strategy['audit']:
            self._log_data_access(task_data, classification, 'processed')
        
        return {
            'data': processed_data,
            'classification': classification,
            'warnings': validation_result['warnings']
        }
    
    def _log_data_access(self, data: Any, classification: str, operation: str):
        """记录数据访问日志"""
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'classification': classification,
            'data_hash': hashlib.md5(str(data).encode()).hexdigest(),
            'user': 'system',  # 实际应用中应该是真实用户
            'success': True
        }
        
        # 这里应该写入审计日志系统
        logging.info(f"Data access: {json.dumps(log_entry)}")
```

## 3. 权限管理和访问控制

### 3.1 基于角色的访问控制 (RBAC)

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Set, Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import uuid
import json

class Permission(Enum):
    """权限枚举"""
    # 任务权限
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_EXECUTE = "task:execute"
    
    # Agent权限
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_ASSIGN = "agent:assign"
    
    # 工具权限
    TOOL_USE = "tool:use"
    TOOL_CREATE = "tool:create"
    TOOL_CONFIGURE = "tool:configure"
    TOOL_SYSTEM_ACCESS = "tool:system_access"
    TOOL_FILE_WRITE = "tool:file_write"
    TOOL_NETWORK_ACCESS = "tool:network_access"
    
    # 数据权限
    DATA_READ_PUBLIC = "data:read:public"
    DATA_READ_INTERNAL = "data:read:internal"
    DATA_READ_CONFIDENTIAL = "data:read:confidential"
    DATA_WRITE_PUBLIC = "data:write:public"
    DATA_WRITE_INTERNAL = "data:write:internal"
    DATA_WRITE_CONFIDENTIAL = "data:write:confidential"
    
    # 系统权限
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_AUDIT = "system:audit"

@dataclass
class Role:
    """角色定义"""
    name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

@dataclass
class User:
    """用户定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    email: str = ""
    roles: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True
    session_timeout: timedelta = field(default_factory=lambda: timedelta(hours=8))

@dataclass
class AccessRequest:
    """访问请求"""
    user_id: str
    resource: str
    action: Permission
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class AccessControlManager:
    """访问控制管理器"""
    
    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        self.access_log: List[Dict] = []
        
        # 初始化默认角色
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """初始化默认角色"""
        
        # 管理员角色 - 完全权限
        admin_role = Role(
            name="admin",
            description="系统管理员 - 完全访问权限",
            permissions=set(Permission)
        )
        
        # 开发者角色 - 开发相关权限
        developer_role = Role(
            name="developer", 
            description="开发者 - 任务和Agent管理权限",
            permissions={
                Permission.TASK_CREATE, Permission.TASK_READ, Permission.TASK_UPDATE, Permission.TASK_EXECUTE,
                Permission.AGENT_CREATE, Permission.AGENT_READ, Permission.AGENT_UPDATE, Permission.AGENT_ASSIGN,
                Permission.TOOL_USE, Permission.TOOL_CREATE, Permission.TOOL_CONFIGURE,
                Permission.DATA_READ_PUBLIC, Permission.DATA_READ_INTERNAL,
                Permission.DATA_WRITE_PUBLIC, Permission.DATA_WRITE_INTERNAL
            }
        )
        
        # 操作员角色 - 执行权限
        operator_role = Role(
            name="operator",
            description="操作员 - 任务执行权限",
            permissions={
                Permission.TASK_READ, Permission.TASK_EXECUTE,
                Permission.AGENT_READ,
                Permission.TOOL_USE,
                Permission.DATA_READ_PUBLIC, Permission.DATA_READ_INTERNAL,
                Permission.DATA_WRITE_PUBLIC
            }
        )
        
        # 只读用户角色
        readonly_role = Role(
            name="readonly",
            description="只读用户 - 查看权限",
            permissions={
                Permission.TASK_READ,
                Permission.AGENT_READ,
                Permission.DATA_READ_PUBLIC,
                Permission.SYSTEM_MONITOR
            }
        )
        
        # 安全审计员角色
        auditor_role = Role(
            name="auditor",
            description="安全审计员 - 审计和监控权限",
            permissions={
                Permission.TASK_READ,
                Permission.AGENT_READ,
                Permission.DATA_READ_PUBLIC, Permission.DATA_READ_INTERNAL, Permission.DATA_READ_CONFIDENTIAL,
                Permission.SYSTEM_MONITOR, Permission.SYSTEM_AUDIT
            }
        )
        
        # 注册角色
        for role in [admin_role, developer_role, operator_role, readonly_role, auditor_role]:
            self.roles[role.name] = role
    
    def create_user(self, username: str, email: str, roles: List[str] = None) -> User:
        """创建用户"""
        
        user = User(
            username=username,
            email=email,
            roles=set(roles or ['readonly'])
        )
        
        # 验证角色存在
        for role_name in user.roles:
            if role_name not in self.roles:
                raise ValueError(f"Role '{role_name}' does not exist")
        
        self.users[user.id] = user
        
        self._log_access("user_created", user.id, {"username": username, "roles": list(user.roles)})
        
        return user
    
    def check_permission(self, user_id: str, permission: Permission, 
                        resource_context: Dict[str, Any] = None) -> bool:
        """检查用户权限"""
        
        if user_id not in self.users:
            self._log_access("permission_denied", user_id, {"reason": "user_not_found", "permission": permission.value})
            return False
        
        user = self.users[user_id]
        
        if not user.is_active:
            self._log_access("permission_denied", user_id, {"reason": "user_inactive", "permission": permission.value})
            return False
        
        # 检查用户角色权限
        user_permissions = set()
        for role_name in user.roles:
            if role_name in self.roles and self.roles[role_name].is_active:
                user_permissions.update(self.roles[role_name].permissions)
        
        has_permission = permission in user_permissions
        
        # 记录访问日志
        self._log_access(
            "permission_check",
            user_id,
            {
                "permission": permission.value,
                "granted": has_permission,
                "resource_context": resource_context
            }
        )
        
        return has_permission
    
    def authorize_task_operation(self, user_id: str, operation: str, task_data: Dict[str, Any] = None) -> bool:
        """授权任务操作"""
        
        permission_mapping = {
            'create': Permission.TASK_CREATE,
            'read': Permission.TASK_READ,
            'update': Permission.TASK_UPDATE,
            'delete': Permission.TASK_DELETE,
            'execute': Permission.TASK_EXECUTE
        }
        
        if operation not in permission_mapping:
            return False
        
        permission = permission_mapping[operation]
        
        # 基础权限检查
        if not self.check_permission(user_id, permission, task_data):
            return False
        
        # 额外的上下文检查
        if task_data:
            # 检查工具使用权限
            if 'tools' in task_data and task_data['tools']:
                if not self.check_permission(user_id, Permission.TOOL_USE):
                    return False
                
                # 检查特殊工具权限
                for tool in task_data['tools']:
                    tool_name = getattr(tool, '__class__', {}).get('__name__', '')
                    
                    # 系统工具需要特殊权限
                    if any(dangerous in tool_name.lower() for dangerous in ['system', 'file', 'network', 'database']):
                        if not self.check_permission(user_id, Permission.TOOL_SYSTEM_ACCESS):
                            return False
            
            # 检查数据访问权限
            data_classification = task_data.get('data_classification', 'public')
            if data_classification == 'confidential':
                if not self.check_permission(user_id, Permission.DATA_READ_CONFIDENTIAL):
                    return False
        
        return True
    
    def create_security_context(self, user_id: str) -> Dict[str, Any]:
        """创建安全上下文"""
        
        if user_id not in self.users:
            return {}
        
        user = self.users[user_id]
        
        # 收集用户权限
        user_permissions = set()
        for role_name in user.roles:
            if role_name in self.roles and self.roles[role_name].is_active:
                user_permissions.update(self.roles[role_name].permissions)
        
        return {
            'user_id': user_id,
            'username': user.username,
            'roles': list(user.roles),
            'permissions': [p.value for p in user_permissions],
            'session_expires': datetime.now() + user.session_timeout,
            'created_at': datetime.now()
        }
    
    def validate_security_context(self, context: Dict[str, Any]) -> bool:
        """验证安全上下文"""
        
        required_fields = ['user_id', 'permissions', 'session_expires']
        if not all(field in context for field in required_fields):
            return False
        
        # 检查会话是否过期
        try:
            expires = datetime.fromisoformat(context['session_expires']) if isinstance(context['session_expires'], str) else context['session_expires']
            if datetime.now() > expires:
                return False
        except:
            return False
        
        # 验证用户仍然活跃
        user_id = context['user_id']
        if user_id not in self.users or not self.users[user_id].is_active:
            return False
        
        return True
    
    def _log_access(self, action: str, user_id: str, details: Dict[str, Any]):
        """记录访问日志"""
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'user_id': user_id,
            'details': details,
            'source_ip': details.get('source_ip', 'unknown')  # 实际应用中从请求中获取
        }
        
        self.access_log.append(log_entry)
        
        # 保持日志大小
        if len(self.access_log) > 10000:
            self.access_log = self.access_log[-10000:]
    
    def get_access_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成访问报告"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_logs = [
            log for log in self.access_log
            if datetime.fromisoformat(log['timestamp']) >= cutoff_time
        ]
        
        # 统计分析
        action_counts = {}
        user_activity = {}
        permission_requests = {}
        denied_attempts = []
        
        for log in recent_logs:
            action = log['action']
            user_id = log['user_id']
            
            # 行为统计
            action_counts[action] = action_counts.get(action, 0) + 1
            
            # 用户活动统计
            if user_id not in user_activity:
                user_activity[user_id] = {'total': 0, 'actions': {}}
            user_activity[user_id]['total'] += 1
            user_activity[user_id]['actions'][action] = user_activity[user_id]['actions'].get(action, 0) + 1
            
            # 权限请求统计
            if action == 'permission_check':
                permission = log['details'].get('permission', 'unknown')
                granted = log['details'].get('granted', False)
                
                if permission not in permission_requests:
                    permission_requests[permission] = {'granted': 0, 'denied': 0}
                
                if granted:
                    permission_requests[permission]['granted'] += 1
                else:
                    permission_requests[permission]['denied'] += 1
                    denied_attempts.append(log)
        
        return {
            'period_hours': hours,
            'total_events': len(recent_logs),
            'action_summary': action_counts,
            'user_activity': user_activity,
            'permission_requests': permission_requests,
            'security_incidents': {
                'denied_attempts': len(denied_attempts),
                'recent_denials': denied_attempts[-10:],  # 最近10个拒绝记录
                'suspicious_patterns': self._detect_suspicious_patterns(recent_logs)
            }
        }
    
    def _detect_suspicious_patterns(self, logs: List[Dict]) -> List[Dict]:
        """检测可疑模式"""
        
        suspicious = []
        
        # 检测频繁的权限拒绝
        user_denials = {}
        for log in logs:
            if log['action'] == 'permission_check' and not log['details'].get('granted', True):
                user_id = log['user_id']
                user_denials[user_id] = user_denials.get(user_id, 0) + 1
        
        for user_id, denial_count in user_denials.items():
            if denial_count > 10:  # 超过10次拒绝
                suspicious.append({
                    'type': 'excessive_denials',
                    'user_id': user_id,
                    'count': denial_count,
                    'severity': 'high' if denial_count > 50 else 'medium'
                })
        
        return suspicious
```

### 3.2 安全会话管理

```python
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import redis
import json

class SecureSessionManager:
    """安全会话管理器"""
    
    def __init__(self, redis_client: redis.Redis = None, jwt_secret: str = None):
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        
        # 会话配置
        self.session_config = {
            'default_timeout': timedelta(hours=8),
            'max_concurrent_sessions': 5,
            'require_reauth_for_sensitive': True,
            'track_session_activity': True,
            'secure_cookies': True
        }
    
    def create_session(self, user_id: str, permissions: List[str], 
                      additional_claims: Dict[str, Any] = None) -> str:
        """创建安全会话"""
        
        session_id = secrets.token_urlsafe(32)
        current_time = datetime.utcnow()
        
        # JWT载荷
        payload = {
            'session_id': session_id,
            'user_id': user_id,
            'permissions': permissions,
            'issued_at': current_time.timestamp(),
            'expires_at': (current_time + self.session_config['default_timeout']).timestamp(),
            'jti': session_id  # JWT ID
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        # 生成JWT令牌
        token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        
        # 在Redis中存储会话信息
        session_data = {
            'user_id': user_id,
            'permissions': permissions,
            'created_at': current_time.isoformat(),
            'last_activity': current_time.isoformat(),
            'active': True,
            'ip_address': additional_claims.get('ip_address', 'unknown') if additional_claims else 'unknown'
        }
        
        # 设置会话过期时间
        self.redis_client.setex(
            f"session:{session_id}",
            self.session_config['default_timeout'],
            json.dumps(session_data)
        )
        
        # 管理并发会话
        self._manage_concurrent_sessions(user_id, session_id)
        
        return token
    
    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """验证会话令牌"""
        
        try:
            # 解码JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            session_id = payload['session_id']
            
            # 检查会话是否在Redis中存在且活跃
            session_data_raw = self.redis_client.get(f"session:{session_id}")
            if not session_data_raw:
                return None
            
            session_data = json.loads(session_data_raw)
            if not session_data.get('active', False):
                return None
            
            # 更新最后活动时间
            session_data['last_activity'] = datetime.utcnow().isoformat()
            self.redis_client.setex(
                f"session:{session_id}",
                self.session_config['default_timeout'],
                json.dumps(session_data)
            )
            
            return {
                'session_id': session_id,
                'user_id': payload['user_id'],
                'permissions': payload['permissions'],
                'issued_at': datetime.fromtimestamp(payload['issued_at']),
                'expires_at': datetime.fromtimestamp(payload['expires_at'])
            }
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None
    
    def revoke_session(self, session_id: str) -> bool:
        """撤销会话"""
        
        try:
            session_data_raw = self.redis_client.get(f"session:{session_id}")
            if session_data_raw:
                session_data = json.loads(session_data_raw)
                session_data['active'] = False
                
                # 保留一段时间以便审计
                self.redis_client.setex(
                    f"session:{session_id}",
                    3600,  # 1小时后彻底删除
                    json.dumps(session_data)
                )
                
                return True
        except Exception:
            pass
        
        return False
    
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """撤销用户的所有会话"""
        
        revoked_count = 0
        
        # 获取用户的所有活跃会话
        pattern = "session:*"
        for key in self.redis_client.scan_iter(match=pattern):
            try:
                session_data_raw = self.redis_client.get(key)
                if session_data_raw:
                    session_data = json.loads(session_data_raw)
                    if session_data.get('user_id') == user_id and session_data.get('active'):
                        session_id = key.decode('utf-8').split(':')[1]
                        if self.revoke_session(session_id):
                            revoked_count += 1
            except Exception:
                continue
        
        return revoked_count
    
    def _manage_concurrent_sessions(self, user_id: str, new_session_id: str):
        """管理并发会话限制"""
        
        if self.session_config['max_concurrent_sessions'] <= 0:
            return
        
        # 获取用户的所有活跃会话
        active_sessions = []
        pattern = "session:*"
        
        for key in self.redis_client.scan_iter(match=pattern):
            try:
                session_data_raw = self.redis_client.get(key)
                if session_data_raw:
                    session_data = json.loads(session_data_raw)
                    if (session_data.get('user_id') == user_id and 
                        session_data.get('active') and 
                        key.decode('utf-8') != f"session:{new_session_id}"):
                        
                        active_sessions.append({
                            'session_id': key.decode('utf-8').split(':')[1],
                            'created_at': datetime.fromisoformat(session_data['created_at'])
                        })
            except Exception:
                continue
        
        # 如果超过限制，撤销最旧的会话
        if len(active_sessions) >= self.session_config['max_concurrent_sessions']:
            active_sessions.sort(key=lambda x: x['created_at'])
            sessions_to_revoke = len(active_sessions) - self.session_config['max_concurrent_sessions'] + 1
            
            for i in range(sessions_to_revoke):
                self.revoke_session(active_sessions[i]['session_id'])
    
    def get_session_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """获取会话分析数据"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        total_sessions = 0
        active_sessions = 0
        user_sessions = {}
        ip_sessions = {}
        
        # 扫描所有会话
        pattern = "session:*"
        for key in self.redis_client.scan_iter(match=pattern):
            try:
                session_data_raw = self.redis_client.get(key)
                if session_data_raw:
                    session_data = json.loads(session_data_raw)
                    created_at = datetime.fromisoformat(session_data['created_at'])
                    
                    if created_at >= cutoff_time:
                        total_sessions += 1
                        
                        if session_data.get('active'):
                            active_sessions += 1
                        
                        user_id = session_data.get('user_id', 'unknown')
                        user_sessions[user_id] = user_sessions.get(user_id, 0) + 1
                        
                        ip_address = session_data.get('ip_address', 'unknown')
                        ip_sessions[ip_address] = ip_sessions.get(ip_address, 0) + 1
                        
            except Exception:
                continue
        
        return {
            'period_hours': hours,
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'users_with_sessions': len(user_sessions),
            'top_users_by_sessions': sorted(user_sessions.items(), key=lambda x: x[1], reverse=True)[:10],
            'sessions_by_ip': dict(sorted(ip_sessions.items(), key=lambda x: x[1], reverse=True)[:20]),
            'session_security_events': self._detect_session_anomalies()
        }
    
    def _detect_session_anomalies(self) -> List[Dict[str, Any]]:
        """检测会话异常"""
        
        anomalies = []
        
        # 检测来自同一IP的多个用户会话
        ip_users = {}
        pattern = "session:*"
        
        for key in self.redis_client.scan_iter(match=pattern):
            try:
                session_data_raw = self.redis_client.get(key)
                if session_data_raw:
                    session_data = json.loads(session_data_raw)
                    if session_data.get('active'):
                        ip = session_data.get('ip_address', 'unknown')
                        user = session_data.get('user_id', 'unknown')
                        
                        if ip not in ip_users:
                            ip_users[ip] = set()
                        ip_users[ip].add(user)
                        
            except Exception:
                continue
        
        # 报告异常
        for ip, users in ip_users.items():
            if len(users) > 3:  # 同一IP超过3个用户
                anomalies.append({
                    'type': 'multiple_users_same_ip',
                    'ip_address': ip,
                    'user_count': len(users),
                    'severity': 'medium'
                })
        
        return anomalies
```

## 4. 生产环境安全最佳实践

### 4.1 安全部署配置

```python
from pathlib import Path
from typing import Dict, List, Any, Optional
import os
import yaml
import logging
from cryptography.fernet import Fernet
import ssl
import socket

class SecureDeploymentManager:
    """安全部署管理器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "security_config.yaml"
        self.security_config = self._load_security_config()
        
        # 设置安全日志
        self._setup_security_logging()
    
    def _load_security_config(self) -> Dict[str, Any]:
        """加载安全配置"""
        
        default_config = {
            'encryption': {
                'algorithm': 'AES-256-GCM',
                'key_rotation_days': 30,
                'encrypt_at_rest': True,
                'encrypt_in_transit': True
            },
            'network': {
                'allowed_hosts': ['127.0.0.1', 'localhost'],
                'use_https': True,
                'ssl_verify': True,
                'cors_origins': [],
                'rate_limiting': {
                    'enabled': True,
                    'requests_per_minute': 60
                }
            },
            'authentication': {
                'require_mfa': False,
                'password_policy': {
                    'min_length': 12,
                    'require_uppercase': True,
                    'require_lowercase': True,
                    'require_digits': True,
                    'require_symbols': True
                },
                'session_timeout': 3600,
                'max_login_attempts': 5,
                'lockout_duration': 900
            },
            'audit': {
                'log_all_requests': True,
                'log_sensitive_operations': True,
                'retention_days': 90,
                'log_level': 'INFO'
            },
            'compliance': {
                'gdpr_enabled': False,
                'data_retention_days': 365,
                'anonymize_logs': True,
                'consent_required': True
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    # 合并默认配置
                    self._merge_configs(default_config, loaded_config)
            else:
                # 创建默认配置文件
                with open(self.config_path, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
        except Exception as e:
            logging.warning(f"Failed to load security config: {e}")
        
        return default_config
    
    def _merge_configs(self, default: Dict, loaded: Dict):
        """递归合并配置"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(default[key], dict) and isinstance(value, dict):
                    self._merge_configs(default[key], value)
                else:
                    default[key] = value
            else:
                default[key] = value
    
    def _setup_security_logging(self):
        """设置安全日志"""
        
        # 创建安全日志记录器
        security_logger = logging.getLogger('crewai.security')
        security_logger.setLevel(getattr(logging, self.security_config['audit']['log_level']))
        
        # 创建安全日志文件处理器
        security_handler = logging.FileHandler('logs/security.log')
        security_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        security_logger.addHandler(security_handler)
        
        # 创建审计日志记录器
        audit_logger = logging.getLogger('crewai.audit')
        audit_logger.setLevel(logging.INFO)
        
        audit_handler = logging.FileHandler('logs/audit.log')
        audit_formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        audit_logger.addHandler(audit_handler)
    
    def generate_security_checklist(self) -> List[Dict[str, Any]]:
        """生成安全检查清单"""
        
        checklist = [
            {
                'category': '加密配置',
                'items': [
                    {
                        'check': '启用数据静态加密',
                        'status': self.security_config['encryption']['encrypt_at_rest'],
                        'recommendation': '启用敏感数据的静态加密保护'
                    },
                    {
                        'check': '启用传输加密',
                        'status': self.security_config['encryption']['encrypt_in_transit'],
                        'recommendation': '确保所有网络通信都使用TLS加密'
                    },
                    {
                        'check': '密钥轮换策略',
                        'status': self.security_config['encryption']['key_rotation_days'] <= 90,
                        'recommendation': '定期轮换加密密钥（建议30-90天）'
                    }
                ]
            },
            {
                'category': '网络安全',
                'items': [
                    {
                        'check': 'HTTPS强制使用',
                        'status': self.security_config['network']['use_https'],
                        'recommendation': '在生产环境中强制使用HTTPS'
                    },
                    {
                        'check': 'SSL证书验证',
                        'status': self.security_config['network']['ssl_verify'],
                        'recommendation': '启用SSL证书验证以防止中间人攻击'
                    },
                    {
                        'check': '速率限制',
                        'status': self.security_config['network']['rate_limiting']['enabled'],
                        'recommendation': '实施API速率限制以防止滥用'
                    }
                ]
            },
            {
                'category': '身份认证',
                'items': [
                    {
                        'check': '强密码策略',
                        'status': self._check_password_policy(),
                        'recommendation': '实施严格的密码复杂度要求'
                    },
                    {
                        'check': '会话超时',
                        'status': self.security_config['authentication']['session_timeout'] <= 3600,
                        'recommendation': '设置合理的会话超时时间'
                    },
                    {
                        'check': '多因子认证',
                        'status': self.security_config['authentication']['require_mfa'],
                        'recommendation': '为敏感操作启用多因子认证'
                    }
                ]
            },
            {
                'category': '审计日志',
                'items': [
                    {
                        'check': '请求日志记录',
                        'status': self.security_config['audit']['log_all_requests'],
                        'recommendation': '记录所有API请求以便安全审计'
                    },
                    {
                        'check': '敏感操作日志',
                        'status': self.security_config['audit']['log_sensitive_operations'],
                        'recommendation': '详细记录敏感操作的审计日志'
                    },
                    {
                        'check': '日志保留策略',
                        'status': self.security_config['audit']['retention_days'] >= 90,
                        'recommendation': '保留足够长的审计日志（至少90天）'
                    }
                ]
            }
        ]
        
        return checklist
    
    def _check_password_policy(self) -> bool:
        """检查密码策略配置"""
        policy = self.security_config['authentication']['password_policy']
        
        return (
            policy['min_length'] >= 12 and
            policy['require_uppercase'] and
            policy['require_lowercase'] and
            policy['require_digits'] and
            policy['require_symbols']
        )
    
    def validate_deployment_security(self) -> Dict[str, Any]:
        """验证部署安全性"""
        
        validation_results = {
            'overall_score': 0,
            'critical_issues': [],
            'warnings': [],
            'recommendations': [],
            'compliant': False
        }
        
        checklist = self.generate_security_checklist()
        total_checks = 0
        passed_checks = 0
        
        for category in checklist:
            for item in category['items']:
                total_checks += 1
                if item['status']:
                    passed_checks += 1
                else:
                    # 分类问题严重性
                    if category['category'] in ['加密配置', '身份认证']:
                        validation_results['critical_issues'].append({
                            'category': category['category'],
                            'issue': item['check'],
                            'recommendation': item['recommendation']
                        })
                    else:
                        validation_results['warnings'].append({
                            'category': category['category'],
                            'issue': item['check'],
                            'recommendation': item['recommendation']
                        })
        
        # 计算总分
        validation_results['overall_score'] = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # 判断是否合规
        validation_results['compliant'] = (
            validation_results['overall_score'] >= 80 and
            len(validation_results['critical_issues']) == 0
        )
        
        # 生成建议
        if not validation_results['compliant']:
            validation_results['recommendations'].extend([
                '解决所有关键安全问题',
                '提高安全配置覆盖率至80%以上',
                '定期进行安全评估和渗透测试',
                '建立安全事件响应流程'
            ])
        
        return validation_results
    
    def generate_security_report(self) -> str:
        """生成安全评估报告"""
        
        validation = self.validate_deployment_security()
        checklist = self.generate_security_checklist()
        
        report = f"""
# CrewAI 安全评估报告

## 总体评分
**安全分数**: {validation['overall_score']:.1f}/100
**合规状态**: {'✅ 合规' if validation['compliant'] else '❌ 不合规'}

## 关键问题 ({len(validation['critical_issues'])})
"""
        
        for issue in validation['critical_issues']:
            report += f"- **{issue['category']}**: {issue['issue']}\n  📋 {issue['recommendation']}\n\n"
        
        report += f"\n## 警告事项 ({len(validation['warnings'])})\n"
        
        for warning in validation['warnings']:
            report += f"- **{warning['category']}**: {warning['issue']}\n  💡 {warning['recommendation']}\n\n"
        
        report += "\n## 详细检查结果\n"
        
        for category in checklist:
            report += f"\n### {category['category']}\n"
            for item in category['items']:
                status = '✅' if item['status'] else '❌'
                report += f"{status} {item['check']}\n"
        
        report += f"\n## 改进建议\n"
        for rec in validation['recommendations']:
            report += f"- {rec}\n"
        
        return report
```

## 结论

通过本文档的深度安全分析，我们全面评估了 CrewAI 框架的安全特性和潜在风险。安全是多智能体系统的基础，需要从架构设计到生产部署的全生命周期安全考虑。

### 核心安全能力

1. **威胁识别与风险评估**
   - 系统性的威胁建模和风险量化
   - 多维度安全评估框架
   - 持续的安全监控和异常检测

2. **多层次防护体系**
   - 输入验证和数据清理
   - 基于角色的访问控制
   - 安全会话管理和认证

3. **合规性和审计**
   - 全面的审计日志记录
   - 数据隐私保护和脱敏
   - 合规性检查和报告

### 最佳实践建议

1. **开发阶段**：实施安全编码标准，进行代码安全审查
2. **测试阶段**：进行渗透测试和安全漏洞扫描
3. **部署阶段**：使用安全配置和环境隔离
4. **运行阶段**：持续监控和及时响应安全事件

### 持续改进

安全是一个持续演进的过程，建议：

1. **定期安全评估**：每季度进行全面安全审查
2. **威胁情报更新**：跟踪最新的安全威胁和攻击向量
3. **安全培训**：提高团队的安全意识和技能
4. **应急预案**：建立完善的安全事件响应流程

通过实施本文档提供的安全框架和最佳实践，可以显著提升 CrewAI 应用的安全性，确保多智能体协作系统在复杂环境中的安全稳定运行。