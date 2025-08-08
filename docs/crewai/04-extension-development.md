# CrewAI 扩展开发指南

## 概述

本文档提供了 CrewAI 框架扩展开发的完整指南，基于对源码架构的深度分析，详细说明如何创建自定义组件、扩展框架功能以及集成企业级特性。无论是开发自定义工具、创建特殊的 Agent 类型，还是集成第三方服务，本指南都将为您提供实践性的技术方案。

## 1. 自定义 Agent 开发

### 1.1 创建专业化 Agent 类型

#### 1.1.1 基础 Agent 扩展模式

```python
from crewai import BaseAgent, Agent
from crewai.agent import CrewAgentExecutor
from typing import Any, Dict, List, Optional, Union
from pydantic import Field, PrivateAttr
import asyncio
import logging

class SpecializedAgent(BaseAgent):
    """专业化智能体基类 - 展示高级扩展模式"""
    
    # 专业化配置
    specialization: str = Field(description="智能体的专业化领域")
    expertise_level: int = Field(default=5, description="专业技能等级 (1-10)")
    knowledge_domains: List[str] = Field(default_factory=list, description="知识领域列表")
    
    # 行为控制参数
    creativity_level: float = Field(default=0.7, description="创造性水平 (0.0-1.0)")
    risk_tolerance: float = Field(default=0.5, description="风险容忍度 (0.0-1.0)")
    collaboration_preference: str = Field(default="balanced", description="协作偏好")
    
    # 私有状态管理
    _performance_metrics: Dict[str, float] = PrivateAttr(default_factory=dict)
    _learning_history: List[Dict] = PrivateAttr(default_factory=list)
    _specialization_cache: Dict[str, Any] = PrivateAttr(default_factory=dict)
    
    class Config:
        extra = "allow"
        arbitrary_types_allowed = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initialize_specialization()
    
    def _initialize_specialization(self):
        """初始化专业化配置"""
        
        # 根据专业化领域调整默认配置
        specialization_configs = {
            "creative_writer": {
                "creativity_level": 0.9,
                "risk_tolerance": 0.7,
                "max_iter": 15
            },
            "data_analyst": {
                "creativity_level": 0.3,
                "risk_tolerance": 0.2,
                "max_iter": 10
            },
            "research_scientist": {
                "creativity_level": 0.6,
                "risk_tolerance": 0.4,
                "max_iter": 20
            }
        }
        
        if self.specialization in specialization_configs:
            config = specialization_configs[self.specialization]
            for key, value in config.items():
                if hasattr(self, key):
                    setattr(self, key, value)
    
    def enhance_prompt_with_specialization(self, original_prompt: str) -> str:
        """使用专业化知识增强提示"""
        
        specialization_context = self._build_specialization_context()
        
        enhanced_prompt = f"""
        {original_prompt}
        
        专业化背景：
        领域：{self.specialization}
        专业级别：{self.expertise_level}/10
        知识领域：{', '.join(self.knowledge_domains)}
        
        专业化指导：
        {specialization_context}
        
        请基于您的专业知识和经验来回应，确保答案的专业性和准确性。
        """
        
        return enhanced_prompt
    
    def _build_specialization_context(self) -> str:
        """构建专业化上下文"""
        
        context_templates = {
            "creative_writer": """
            作为创意写作专家，请：
            1. 运用丰富的文学技巧和创意表达
            2. 注重故事性和情感共鸣
            3. 保持独特的写作风格和声音
            """,
            "data_analyst": """
            作为数据分析专家，请：
            1. 基于数据事实进行分析
            2. 使用统计学方法验证结论
            3. 提供量化的洞察和建议
            """,
            "research_scientist": """
            作为研究科学家，请：
            1. 遵循科学方法和严谨逻辑
            2. 引用权威资料和最新研究
            3. 保持客观中立的分析态度
            """
        }
        
        return context_templates.get(self.specialization, "请运用您的专业知识进行分析。")
    
    async def execute_specialized_task(self, task: Any) -> Any:
        """执行专业化任务"""
        
        # 记录任务开始
        task_start_time = asyncio.get_event_loop().time()
        
        try:
            # 应用专业化增强
            if hasattr(task, 'description'):
                task.description = self.enhance_prompt_with_specialization(task.description)
            
            # 执行任务
            result = await self._execute_with_specialization(task)
            
            # 记录性能指标
            execution_time = asyncio.get_event_loop().time() - task_start_time
            self._update_performance_metrics(task, result, execution_time)
            
            return result
            
        except Exception as e:
            self._handle_execution_error(task, e)
            raise
    
    def _update_performance_metrics(self, task: Any, result: Any, execution_time: float):
        """更新性能指标"""
        
        metrics = {
            "execution_time": execution_time,
            "task_complexity": self._assess_task_complexity(task),
            "result_quality": self._assess_result_quality(result),
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # 更新累计指标
        self._performance_metrics.update(metrics)
        
        # 记录学习历史
        self._learning_history.append({
            "task_type": getattr(task, 'type', 'unknown'),
            "performance": metrics,
            "lessons_learned": self._extract_lessons(task, result)
        })
    
    def get_specialization_insights(self) -> Dict[str, Any]:
        """获取专业化洞察"""
        
        return {
            "specialization": self.specialization,
            "expertise_level": self.expertise_level,
            "knowledge_domains": self.knowledge_domains,
            "performance_summary": self._summarize_performance(),
            "learning_insights": self._generate_learning_insights(),
            "optimization_suggestions": self._suggest_optimizations()
        }
```

#### 1.1.2 领域特定 Agent 实现

```python
class CreativeWriterAgent(SpecializedAgent):
    """创意写作专家 Agent"""
    
    specialization: str = Field(default="creative_writer")
    writing_styles: List[str] = Field(default_factory=lambda: ["narrative", "descriptive", "persuasive"])
    target_audiences: List[str] = Field(default_factory=lambda: ["general", "professional", "academic"])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.knowledge_domains = ["creative_writing", "storytelling", "content_strategy"]
        self.creativity_level = 0.9
    
    def adapt_writing_style(self, content_type: str, audience: str) -> Dict[str, Any]:
        """根据内容类型和受众调整写作风格"""
        
        style_adaptations = {
            ("blog_post", "general"): {
                "tone": "conversational",
                "complexity": "medium",
                "examples": True,
                "call_to_action": True
            },
            ("technical_doc", "professional"): {
                "tone": "formal",
                "complexity": "high",
                "examples": True,
                "call_to_action": False
            },
            ("marketing_copy", "business"): {
                "tone": "persuasive",
                "complexity": "low",
                "examples": True,
                "call_to_action": True
            }
        }
        
        return style_adaptations.get((content_type, audience), {
            "tone": "neutral",
            "complexity": "medium",
            "examples": False,
            "call_to_action": False
        })

class DataAnalystAgent(SpecializedAgent):
    """数据分析专家 Agent"""
    
    specialization: str = Field(default="data_analyst")
    analysis_methods: List[str] = Field(default_factory=lambda: ["descriptive", "inferential", "predictive"])
    visualization_preferences: List[str] = Field(default_factory=lambda: ["charts", "graphs", "dashboards"])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.knowledge_domains = ["statistics", "data_science", "business_intelligence"]
        self.creativity_level = 0.3
        self.risk_tolerance = 0.2
    
    def configure_analysis_approach(self, data_characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """根据数据特征配置分析方法"""
        
        approach_config = {
            "statistical_tests": [],
            "visualization_types": [],
            "validation_methods": [],
            "confidence_level": 0.95
        }
        
        # 根据数据类型选择方法
        if data_characteristics.get("data_type") == "time_series":
            approach_config["statistical_tests"].extend(["trend_analysis", "seasonality_test"])
            approach_config["visualization_types"].append("line_chart")
        
        if data_characteristics.get("sample_size", 0) > 1000:
            approach_config["validation_methods"].append("cross_validation")
        
        return approach_config
```

### 1.2 Agent 行为定制

#### 1.2.1 自定义决策逻辑

```python
from crewai.agents.agent_executor import CrewAgentExecutor
from langchain.schema import AgentAction, AgentFinish
from typing import Tuple, Union, List

class CustomDecisionAgent(SpecializedAgent):
    """自定义决策逻辑的 Agent"""
    
    decision_strategy: str = Field(default="conservative", description="决策策略")
    confidence_threshold: float = Field(default=0.8, description="置信度阈值")
    
    def create_custom_executor(self) -> CrewAgentExecutor:
        """创建自定义执行器"""
        
        class CustomAgentExecutor(CrewAgentExecutor):
            def __init__(self, agent_instance, **kwargs):
                super().__init__(**kwargs)
                self.agent_instance = agent_instance
            
            def _should_continue(self, iterations: int, time_elapsed: float) -> bool:
                """自定义继续条件"""
                
                # 基于置信度的早停策略
                if hasattr(self, 'last_confidence') and \
                   self.last_confidence > self.agent_instance.confidence_threshold:
                    return False
                
                # 保守策略的迭代控制
                if self.agent_instance.decision_strategy == "conservative":
                    return iterations < (self.max_iterations * 0.7)
                
                return super()._should_continue(iterations, time_elapsed)
            
            def _take_next_step(self) -> Union[AgentFinish, List[Tuple[AgentAction, str]]]:
                """自定义下一步决策"""
                
                # 执行标准决策流程
                next_step = super()._take_next_step()
                
                # 应用自定义决策逻辑
                if isinstance(next_step, list) and len(next_step) > 0:
                    action, observation = next_step[0]
                    
                    # 评估动作的风险和收益
                    risk_score = self._assess_action_risk(action)
                    
                    if risk_score > (1 - self.agent_instance.risk_tolerance):
                        # 高风险动作，寻找替代方案
                        alternative_action = self._find_safer_alternative(action)
                        if alternative_action:
                            next_step = [(alternative_action, observation)]
                
                return next_step
            
            def _assess_action_risk(self, action: AgentAction) -> float:
                """评估动作风险"""
                
                risk_indicators = {
                    "external_api_call": 0.6,
                    "data_modification": 0.8,
                    "file_system_access": 0.7,
                    "network_request": 0.5
                }
                
                # 基于动作类型评估风险
                action_type = self._classify_action(action)
                base_risk = risk_indicators.get(action_type, 0.3)
                
                # 根据输入复杂度调整风险
                complexity_factor = len(str(action.tool_input)) / 1000
                adjusted_risk = min(base_risk + complexity_factor, 1.0)
                
                return adjusted_risk
        
        return CustomAgentExecutor(self)
```

## 2. 自定义工具开发

### 2.1 高级工具创建模式

#### 2.1.1 企业级工具基类

```python
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Type, Union
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
import hashlib
import json

class EnterpriseBaseTool(BaseTool):
    """企业级工具基类 - 提供通用的企业特性"""
    
    # 企业配置
    api_key: Optional[str] = Field(default=None, description="API密钥")
    rate_limit: int = Field(default=100, description="每分钟请求限制")
    cache_ttl: int = Field(default=300, description="缓存过期时间（秒）")
    retry_attempts: int = Field(default=3, description="重试次数")
    timeout: int = Field(default=30, description="超时时间（秒）")
    
    # 监控和审计
    enable_logging: bool = Field(default=True, description="启用日志记录")
    enable_metrics: bool = Field(default=True, description="启用指标收集")
    enable_audit: bool = Field(default=False, description="启用审计追踪")
    
    class Config:
        extra = "allow"
        arbitrary_types_allowed = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._request_count = 0
        self._last_request_time = datetime.now()
        self._cache = {}
    
    async def _execute_with_enterprise_features(self, *args, **kwargs) -> Any:
        """执行工具调用并应用企业特性"""
        
        start_time = datetime.now()
        request_id = self._generate_request_id()
        
        try:
            # 速率限制检查
            await self._check_rate_limit()
            
            # 缓存检查
            cache_key = self._generate_cache_key(*args, **kwargs)
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                self._log_cache_hit(request_id, cache_key)
                return cached_result
            
            # 执行实际工具逻辑
            result = await self._execute_core_logic(*args, **kwargs)
            
            # 缓存结果
            self._cache_result(cache_key, result)
            
            # 记录指标
            if self.enable_metrics:
                self._record_metrics(request_id, start_time, "success")
            
            # 审计日志
            if self.enable_audit:
                self._write_audit_log(request_id, args, kwargs, result)
            
            return result
            
        except Exception as e:
            # 错误处理和重试
            if self.retry_attempts > 0:
                self.logger.warning(f"Tool execution failed, retrying: {e}")
                return await self._retry_execution(*args, **kwargs)
            
            # 记录错误指标
            if self.enable_metrics:
                self._record_metrics(request_id, start_time, "error")
            
            self.logger.error(f"Tool execution failed: {e}")
            raise
    
    async def _check_rate_limit(self):
        """检查速率限制"""
        
        current_time = datetime.now()
        time_diff = (current_time - self._last_request_time).total_seconds()
        
        if time_diff < 60:  # 一分钟内
            if self._request_count >= self.rate_limit:
                wait_time = 60 - time_diff
                self.logger.warning(f"Rate limit exceeded, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._last_request_time = datetime.now()
        else:
            self._request_count = 0
            self._last_request_time = current_time
        
        self._request_count += 1
    
    def _generate_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        
        # 创建基于参数的哈希键
        content = json.dumps({
            "args": args,
            "kwargs": kwargs,
            "tool": self.__class__.__name__
        }, sort_keys=True, default=str)
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """获取缓存结果"""
        
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return result
            else:
                del self._cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Any):
        """缓存结果"""
        
        self._cache[cache_key] = (result, datetime.now())
        
        # 清理过期缓存
        self._cleanup_expired_cache()
    
    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        
        current_time = datetime.now()
        expired_keys = []
        
        for key, (result, timestamp) in self._cache.items():
            if current_time - timestamp > timedelta(seconds=self.cache_ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
    
    async def _execute_core_logic(self, *args, **kwargs) -> Any:
        """核心逻辑执行 - 子类需要实现"""
        raise NotImplementedError("Subclasses must implement _execute_core_logic")
    
    def run(self, *args, **kwargs) -> str:
        """同步执行入口"""
        return asyncio.run(self._execute_with_enterprise_features(*args, **kwargs))
    
    async def arun(self, *args, **kwargs) -> str:
        """异步执行入口"""
        return await self._execute_with_enterprise_features(*args, **kwargs)
```

#### 2.1.2 具体工具实现示例

```python
class EnterpriseWebSearchTool(EnterpriseBaseTool):
    """企业级网络搜索工具"""
    
    name: str = "enterprise_web_search"
    description: str = "执行安全的企业级网络搜索，支持结果过滤和内容审查"
    
    search_engine: str = Field(default="google", description="搜索引擎类型")
    content_filter: bool = Field(default=True, description="启用内容过滤")
    result_limit: int = Field(default=10, description="结果数量限制")
    allowed_domains: Optional[List[str]] = Field(default=None, description="允许的域名列表")
    blocked_domains: Optional[List[str]] = Field(default=None, description="禁止的域名列表")
    
    class SearchInput(BaseModel):
        query: str = Field(description="搜索查询词")
        language: Optional[str] = Field(default="zh-cn", description="搜索语言")
        region: Optional[str] = Field(default="cn", description="搜索地区")
        safe_search: Optional[str] = Field(default="moderate", description="安全搜索级别")
    
    args_schema: Type[BaseModel] = SearchInput
    
    async def _execute_core_logic(self, query: str, language: str = "zh-cn", 
                                 region: str = "cn", safe_search: str = "moderate") -> str:
        """执行搜索逻辑"""
        
        # 构建搜索参数
        search_params = {
            "q": query,
            "hl": language,
            "gl": region,
            "safe": safe_search,
            "num": self.result_limit
        }
        
        try:
            # 使用异步HTTP客户端执行搜索
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                search_results = await self._perform_search(session, search_params)
            
            # 过滤和处理结果
            filtered_results = self._filter_search_results(search_results)
            
            # 格式化结果
            formatted_results = self._format_search_results(filtered_results)
            
            return formatted_results
            
        except asyncio.TimeoutError:
            raise Exception(f"Search timeout after {self.timeout} seconds")
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")
    
    async def _perform_search(self, session: aiohttp.ClientSession, params: Dict) -> List[Dict]:
        """执行实际搜索请求"""
        
        # 这里可以集成实际的搜索API
        # 示例使用模拟数据
        mock_results = [
            {
                "title": f"搜索结果: {params['q']}",
                "url": f"https://example.com/search/{params['q']}",
                "snippet": f"关于 '{params['q']}' 的详细信息...",
                "domain": "example.com"
            }
        ]
        
        return mock_results
    
    def _filter_search_results(self, results: List[Dict]) -> List[Dict]:
        """过滤搜索结果"""
        
        filtered = []
        
        for result in results:
            domain = result.get("domain", "")
            
            # 域名白名单检查
            if self.allowed_domains and domain not in self.allowed_domains:
                continue
            
            # 域名黑名单检查
            if self.blocked_domains and domain in self.blocked_domains:
                continue
            
            # 内容过滤
            if self.content_filter:
                if self._contains_inappropriate_content(result):
                    continue
            
            filtered.append(result)
        
        return filtered
    
    def _contains_inappropriate_content(self, result: Dict) -> bool:
        """检查不当内容"""
        
        inappropriate_keywords = ["spam", "adult", "illegal"]
        content = f"{result.get('title', '')} {result.get('snippet', '')}"
        
        return any(keyword in content.lower() for keyword in inappropriate_keywords)
    
    def _format_search_results(self, results: List[Dict]) -> str:
        """格式化搜索结果"""
        
        if not results:
            return "没有找到相关结果。"
        
        formatted = "搜索结果：\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"{i}. {result['title']}\n"
            formatted += f"   网址: {result['url']}\n"
            formatted += f"   摘要: {result['snippet']}\n\n"
        
        return formatted

class DatabaseQueryTool(EnterpriseBaseTool):
    """企业数据库查询工具"""
    
    name: str = "database_query"
    description: str = "执行安全的数据库查询操作，支持SQL注入防护"
    
    connection_string: str = Field(description="数据库连接字符串")
    allowed_tables: List[str] = Field(description="允许查询的表名列表")
    query_timeout: int = Field(default=30, description="查询超时时间")
    max_rows: int = Field(default=1000, description="最大返回行数")
    
    class QueryInput(BaseModel):
        sql_query: str = Field(description="SQL查询语句")
        parameters: Optional[Dict[str, Any]] = Field(default=None, description="查询参数")
    
    args_schema: Type[BaseModel] = QueryInput
    
    async def _execute_core_logic(self, sql_query: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """执行数据库查询"""
        
        # SQL注入检查
        if not self._is_safe_query(sql_query):
            raise Exception("Unsafe SQL query detected")
        
        # 表名权限检查
        if not self._check_table_permissions(sql_query):
            raise Exception("Access to specified tables not allowed")
        
        try:
            # 执行查询（这里使用模拟实现）
            results = await self._execute_query(sql_query, parameters)
            
            # 格式化结果
            return self._format_query_results(results)
            
        except Exception as e:
            raise Exception(f"Database query failed: {str(e)}")
    
    def _is_safe_query(self, query: str) -> bool:
        """检查SQL查询安全性"""
        
        # 基本的SQL注入检查
        dangerous_keywords = [
            "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE",
            "EXEC", "EXECUTE", "SCRIPT", "--", "/*", "*/"
        ]
        
        query_upper = query.upper()
        return not any(keyword in query_upper for keyword in dangerous_keywords)
    
    def _check_table_permissions(self, query: str) -> bool:
        """检查表访问权限"""
        
        # 提取查询中的表名（简化实现）
        import re
        table_pattern = r'FROM\s+(\w+)|JOIN\s+(\w+)'
        matches = re.findall(table_pattern, query, re.IGNORECASE)
        
        query_tables = set()
        for match in matches:
            query_tables.update(filter(None, match))
        
        return query_tables.issubset(set(self.allowed_tables))
```

### 2.2 工具组合和编排

#### 2.2.1 复合工具创建

```python
class CompositeAnalysisTool(EnterpriseBaseTool):
    """复合分析工具 - 组合多个子工具"""
    
    name: str = "composite_analysis"
    description: str = "执行复合数据分析，结合多种分析方法"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 初始化子工具
        self.web_search_tool = EnterpriseWebSearchTool()
        self.database_tool = DatabaseQueryTool(
            connection_string="sqlite:///example.db",
            allowed_tables=["users", "products", "orders"]
        )
    
    class AnalysisInput(BaseModel):
        analysis_type: str = Field(description="分析类型：market, customer, product")
        keywords: List[str] = Field(description="分析关键词")
        data_sources: List[str] = Field(description="数据源列表")
        depth_level: int = Field(default=3, description="分析深度等级 1-5")
    
    args_schema: Type[BaseModel] = AnalysisInput
    
    async def _execute_core_logic(self, analysis_type: str, keywords: List[str], 
                                 data_sources: List[str], depth_level: int = 3) -> str:
        """执行复合分析"""
        
        analysis_results = {
            "web_data": None,
            "database_data": None,
            "analysis_insights": None
        }
        
        try:
            # 并行执行数据收集
            tasks = []
            
            if "web" in data_sources:
                search_query = " ".join(keywords)
                tasks.append(self._collect_web_data(search_query))
            
            if "database" in data_sources:
                db_query = self._build_database_query(analysis_type, keywords)
                tasks.append(self._collect_database_data(db_query))
            
            # 等待所有数据收集任务完成
            if tasks:
                data_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(data_results):
                    if not isinstance(result, Exception):
                        source_type = data_sources[i]
                        analysis_results[f"{source_type}_data"] = result
            
            # 执行综合分析
            analysis_results["analysis_insights"] = await self._perform_composite_analysis(
                analysis_results, analysis_type, depth_level
            )
            
            return self._format_composite_results(analysis_results)
            
        except Exception as e:
            raise Exception(f"Composite analysis failed: {str(e)}")
    
    async def _collect_web_data(self, query: str) -> Dict:
        """收集网络数据"""
        
        try:
            result = await self.web_search_tool._execute_core_logic(query)
            return {"source": "web", "data": result, "status": "success"}
        except Exception as e:
            return {"source": "web", "error": str(e), "status": "error"}
    
    async def _collect_database_data(self, query: str) -> Dict:
        """收集数据库数据"""
        
        try:
            result = await self.database_tool._execute_core_logic(query)
            return {"source": "database", "data": result, "status": "success"}
        except Exception as e:
            return {"source": "database", "error": str(e), "status": "error"}
```

## 3. 自定义 LLM 集成

### 3.1 LLM 适配器开发

#### 3.1.1 企业级 LLM 适配器

```python
from crewai.llm import BaseLLM
from typing import Any, Dict, List, Optional, Union, Iterator
from pydantic import Field
import aiohttp
import asyncio
import json

class EnterpriseLLMAdapter(BaseLLM):
    """企业级LLM适配器基类"""
    
    # 企业配置
    api_endpoint: str = Field(description="API端点URL")
    api_key: str = Field(description="API密钥")
    model_name: str = Field(description="模型名称")
    
    # 高级配置
    temperature: float = Field(default=0.7, description="生成温度")
    max_tokens: int = Field(default=2048, description="最大token数")
    top_p: float = Field(default=0.9, description="Top-p采样")
    frequency_penalty: float = Field(default=0.0, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, description="存在惩罚")
    
    # 企业特性
    content_filter: bool = Field(default=True, description="启用内容过滤")
    audit_logging: bool = Field(default=True, description="启用审计日志")
    encryption_enabled: bool = Field(default=True, description="启用加密传输")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "CrewAI-Enterprise/1.0"
            }
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
        
        return self._session
    
    async def call(self, messages: Union[str, List[Dict]], 
                   tools: Optional[List] = None, 
                   callbacks: Optional[List] = None, **kwargs) -> str:
        """调用LLM API"""
        
        # 格式化消息
        formatted_messages = self._format_messages(messages)
        
        # 构建请求体
        request_body = self._build_request_body(
            formatted_messages, tools, **kwargs
        )
        
        # 内容安全检查
        if self.content_filter:
            self._check_content_safety(formatted_messages)
        
        try:
            session = await self._get_session()
            
            async with session.post(self.api_endpoint, json=request_body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM API error {response.status}: {error_text}")
                
                response_data = await response.json()
                result = self._extract_response(response_data)
                
                # 审计日志
                if self.audit_logging:
                    self._log_api_call(formatted_messages, result)
                
                return result
                
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise
    
    def _format_messages(self, messages: Union[str, List[Dict]]) -> List[Dict]:
        """格式化消息"""
        
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        
        return messages
    
    def _build_request_body(self, messages: List[Dict], 
                           tools: Optional[List] = None, **kwargs) -> Dict:
        """构建请求体"""
        
        request_body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty)
        }
        
        # 添加工具调用支持
        if tools:
            request_body["tools"] = self._format_tools(tools)
            request_body["tool_choice"] = "auto"
        
        return request_body
    
    def _format_tools(self, tools: List) -> List[Dict]:
        """格式化工具定义"""
        
        formatted_tools = []
        
        for tool in tools:
            if hasattr(tool, 'name') and hasattr(tool, 'description'):
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description
                    }
                }
                
                # 添加参数模式
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    tool_def["function"]["parameters"] = self._convert_pydantic_to_json_schema(
                        tool.args_schema
                    )
                
                formatted_tools.append(tool_def)
        
        return formatted_tools
    
    def _extract_response(self, response_data: Dict) -> str:
        """提取响应内容"""
        
        try:
            # 标准OpenAI格式
            if "choices" in response_data:
                choice = response_data["choices"][0]
                
                if "message" in choice:
                    message = choice["message"]
                    
                    # 处理工具调用
                    if "tool_calls" in message:
                        return self._handle_tool_calls(message["tool_calls"])
                    
                    return message.get("content", "")
                
                return choice.get("text", "")
            
            # 自定义格式适配
            return response_data.get("response", str(response_data))
            
        except KeyError as e:
            raise Exception(f"Unexpected response format: {e}")
    
    def _check_content_safety(self, messages: List[Dict]):
        """检查内容安全性"""
        
        # 基础的内容安全检查
        unsafe_patterns = [
            "恶意代码", "网络攻击", "个人信息泄露",
            "暴力内容", "仇恨言论", "非法活动"
        ]
        
        for message in messages:
            content = message.get("content", "")
            if any(pattern in content for pattern in unsafe_patterns):
                raise Exception("Content safety violation detected")
    
    def _log_api_call(self, messages: List[Dict], response: str):
        """记录API调用日志"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model_name,
            "message_count": len(messages),
            "response_length": len(response),
            "content_filtered": self.content_filter
        }
        
        # 这里可以集成企业日志系统
        self.logger.info(f"LLM API call: {log_entry}")

class CustomOpenAIAdapter(EnterpriseLLMAdapter):
    """自定义OpenAI适配器"""
    
    api_endpoint: str = Field(default="https://api.openai.com/v1/chat/completions")
    model_name: str = Field(default="gpt-3.5-turbo")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class LocalLLMAdapter(EnterpriseLLMAdapter):
    """本地部署LLM适配器"""
    
    api_endpoint: str = Field(description="本地LLM服务端点")
    model_name: str = Field(default="local-llm")
    
    async def call(self, messages: Union[str, List[Dict]], 
                   tools: Optional[List] = None, 
                   callbacks: Optional[List] = None, **kwargs) -> str:
        """调用本地LLM"""
        
        # 本地LLM的特殊处理逻辑
        formatted_messages = self._format_messages(messages)
        
        # 本地模型可能需要不同的请求格式
        request_body = {
            "inputs": self._merge_messages_for_local(formatted_messages),
            "parameters": {
                "temperature": kwargs.get("temperature", self.temperature),
                "max_new_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "do_sample": True
            }
        }
        
        try:
            session = await self._get_session()
            
            async with session.post(self.api_endpoint, json=request_body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Local LLM error {response.status}: {error_text}")
                
                response_data = await response.json()
                
                # 本地模型响应格式处理
                if isinstance(response_data, list) and len(response_data) > 0:
                    return response_data[0].get("generated_text", "")
                
                return response_data.get("generated_text", str(response_data))
                
        except Exception as e:
            self.logger.error(f"Local LLM call failed: {e}")
            raise
    
    def _merge_messages_for_local(self, messages: List[Dict]) -> str:
        """将消息合并为适合本地模型的格式"""
        
        merged = ""
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                merged += f"System: {content}\n"
            elif role == "user":
                merged += f"Human: {content}\n"
            elif role == "assistant":
                merged += f"Assistant: {content}\n"
        
        merged += "Assistant: "  # 提示模型开始回答
        return merged
```

## 4. 知识源扩展开发

### 4.1 自定义知识源适配器

#### 4.1.1 企业文档知识源

```python
from crewai.knowledge import BaseKnowledgeSource
from typing import Any, Dict, List, Optional, Union
import os
import pickle
from datetime import datetime
import hashlib

class EnterpriseDocumentKnowledge(BaseKnowledgeSource):
    """企业文档知识源"""
    
    document_paths: List[str] = Field(description="文档路径列表")
    supported_formats: List[str] = Field(
        default_factory=lambda: [".txt", ".md", ".pdf", ".docx", ".xlsx"]
    )
    index_cache_path: str = Field(default="./knowledge_cache", description="索引缓存路径")
    auto_refresh: bool = Field(default=True, description="自动刷新索引")
    refresh_interval: int = Field(default=3600, description="刷新间隔（秒）")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._document_index: Dict[str, Dict] = {}
        self._last_refresh = datetime.min
        self._ensure_cache_directory()
    
    def _ensure_cache_directory(self):
        """确保缓存目录存在"""
        
        os.makedirs(self.index_cache_path, exist_ok=True)
    
    async def search(self, query: str, limit: int = 10, 
                    score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """搜索相关文档"""
        
        # 检查是否需要刷新索引
        if self._should_refresh_index():
            await self._refresh_document_index()
        
        # 执行搜索
        search_results = self._perform_semantic_search(query, limit, score_threshold)
        
        # 格式化结果
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "content": result["content"],
                "source": result["source"],
                "score": result["score"],
                "metadata": result.get("metadata", {})
            })
        
        return formatted_results
    
    def _should_refresh_index(self) -> bool:
        """检查是否应该刷新索引"""
        
        if not self.auto_refresh:
            return False
        
        time_since_refresh = (datetime.now() - self._last_refresh).total_seconds()
        return time_since_refresh > self.refresh_interval
    
    async def _refresh_document_index(self):
        """刷新文档索引"""
        
        self.logger.info("Refreshing document index...")
        
        new_index = {}
        
        for doc_path in self.document_paths:
            if os.path.isfile(doc_path):
                await self._index_single_document(doc_path, new_index)
            elif os.path.isdir(doc_path):
                await self._index_directory(doc_path, new_index)
        
        self._document_index = new_index
        self._last_refresh = datetime.now()
        
        # 保存索引到缓存
        await self._save_index_to_cache()
        
        self.logger.info(f"Indexed {len(new_index)} documents")
    
    async def _index_single_document(self, file_path: str, index: Dict):
        """索引单个文档"""
        
        try:
            # 检查文件格式
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in self.supported_formats:
                return
            
            # 获取文件信息
            file_stat = os.stat(file_path)
            file_hash = self._calculate_file_hash(file_path)
            
            # 检查文件是否已经索引且未修改
            if file_path in self._document_index:
                existing_entry = self._document_index[file_path]
                if existing_entry.get("file_hash") == file_hash:
                    index[file_path] = existing_entry
                    return
            
            # 提取文档内容
            content = await self._extract_document_content(file_path, file_ext)
            
            if content:
                # 分段处理
                chunks = self._split_content_into_chunks(content)
                
                # 生成嵌入向量（这里使用模拟实现）
                embeddings = await self._generate_embeddings(chunks)
                
                # 创建索引条目
                index[file_path] = {
                    "file_path": file_path,
                    "file_hash": file_hash,
                    "last_modified": file_stat.st_mtime,
                    "content_chunks": chunks,
                    "embeddings": embeddings,
                    "metadata": {
                        "file_size": file_stat.st_size,
                        "file_type": file_ext,
                        "indexed_at": datetime.now().isoformat()
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to index document {file_path}: {e}")
    
    async def _extract_document_content(self, file_path: str, file_ext: str) -> str:
        """提取文档内容"""
        
        try:
            if file_ext == ".txt" or file_ext == ".md":
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            
            elif file_ext == ".pdf":
                # 使用PyPDF2或类似库
                return self._extract_pdf_content(file_path)
            
            elif file_ext == ".docx":
                # 使用python-docx
                return self._extract_docx_content(file_path)
            
            elif file_ext == ".xlsx":
                # 使用openpyxl
                return self._extract_xlsx_content(file_path)
            
            else:
                self.logger.warning(f"Unsupported file format: {file_ext}")
                return ""
                
        except Exception as e:
            self.logger.error(f"Failed to extract content from {file_path}: {e}")
            return ""
    
    def _split_content_into_chunks(self, content: str, chunk_size: int = 1000, 
                                  overlap: int = 200) -> List[str]:
        """将内容分割成块"""
        
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # 尝试在句号或段落处分割
            if end < len(content):
                for i in range(end, start + chunk_size // 2, -1):
                    if content[i] in ".。\n":
                        end = i + 1
                        break
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end - overlap > start else end
        
        return chunks
    
    async def _generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """生成嵌入向量（模拟实现）"""
        
        # 这里应该集成真实的嵌入模型
        # 例如使用sentence-transformers或OpenAI embeddings
        
        embeddings = []
        for chunk in chunks:
            # 模拟嵌入向量
            mock_embedding = [0.1] * 384  # 模拟384维向量
            embeddings.append(mock_embedding)
        
        return embeddings
    
    def _perform_semantic_search(self, query: str, limit: int, 
                                score_threshold: float) -> List[Dict]:
        """执行语义搜索"""
        
        # 简化的关键词匹配实现
        # 实际应该使用向量相似度搜索
        
        results = []
        query_lower = query.lower()
        
        for file_path, doc_info in self._document_index.items():
            for i, chunk in enumerate(doc_info["content_chunks"]):
                chunk_lower = chunk.lower()
                
                # 简单的关键词匹配评分
                score = self._calculate_text_similarity(query_lower, chunk_lower)
                
                if score >= score_threshold:
                    results.append({
                        "content": chunk,
                        "source": file_path,
                        "score": score,
                        "chunk_index": i,
                        "metadata": doc_info["metadata"]
                    })
        
        # 按分数排序并限制数量
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def _calculate_text_similarity(self, query: str, text: str) -> float:
        """计算文本相似度（简化实现）"""
        
        query_words = set(query.split())
        text_words = set(text.split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(text_words)
        similarity = len(intersection) / len(query_words)
        
        return similarity
```

## 5. 事件系统高级应用

### 5.1 自定义事件和处理器

#### 5.1.1 企业级事件系统扩展

```python
from crewai.utilities.events import BaseEvent, crewai_event_bus
from typing import Any, Dict, Optional, Callable
from datetime import datetime
import json
import asyncio

class CustomBusinessEvent(BaseEvent):
    """自定义业务事件基类"""
    
    event_category: str
    business_context: Dict[str, Any]
    priority_level: int
    correlation_id: Optional[str] = None
    
    def __init__(self, event_category: str, business_context: Dict[str, Any], 
                 priority_level: int = 1, correlation_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.event_category = event_category
        self.business_context = business_context
        self.priority_level = priority_level
        self.correlation_id = correlation_id

class TaskExecutionMetricsEvent(CustomBusinessEvent):
    """任务执行指标事件"""
    
    def __init__(self, task_name: str, execution_time: float, 
                 success: bool, metrics: Dict[str, Any], **kwargs):
        super().__init__(
            event_category="task_metrics",
            business_context={
                "task_name": task_name,
                "execution_time": execution_time,
                "success": success,
                "metrics": metrics
            },
            **kwargs
        )

class AgentCollaborationEvent(CustomBusinessEvent):
    """智能体协作事件"""
    
    def __init__(self, collaboration_type: str, agents_involved: List[str], 
                 interaction_data: Dict[str, Any], **kwargs):
        super().__init__(
            event_category="agent_collaboration",
            business_context={
                "collaboration_type": collaboration_type,
                "agents_involved": agents_involved,
                "interaction_data": interaction_data
            },
            **kwargs
        )

class EnterpriseEventHandler:
    """企业级事件处理器"""
    
    def __init__(self):
        self.metrics_storage = {}
        self.alert_thresholds = {
            "execution_time": 30.0,  # 秒
            "error_rate": 0.1,       # 10%
            "memory_usage": 0.8      # 80%
        }
        
        # 注册事件处理器
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        
        @crewai_event_bus.on(TaskExecutionMetricsEvent)
        def handle_task_metrics(source: Any, event: TaskExecutionMetricsEvent):
            self._handle_task_metrics_event(source, event)
        
        @crewai_event_bus.on(AgentCollaborationEvent)
        def handle_agent_collaboration(source: Any, event: AgentCollaborationEvent):
            self._handle_collaboration_event(source, event)
    
    def _handle_task_metrics_event(self, source: Any, event: TaskExecutionMetricsEvent):
        """处理任务指标事件"""
        
        task_name = event.business_context["task_name"]
        execution_time = event.business_context["execution_time"]
        success = event.business_context["success"]
        
        # 更新指标存储
        if task_name not in self.metrics_storage:
            self.metrics_storage[task_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "total_time": 0,
                "max_time": 0,
                "min_time": float('inf')
            }
        
        metrics = self.metrics_storage[task_name]
        metrics["total_executions"] += 1
        metrics["total_time"] += execution_time
        metrics["max_time"] = max(metrics["max_time"], execution_time)
        metrics["min_time"] = min(metrics["min_time"], execution_time)
        
        if success:
            metrics["successful_executions"] += 1
        
        # 检查告警条件
        self._check_alert_conditions(task_name, metrics)
        
        # 异步存储到外部系统
        asyncio.create_task(self._store_metrics_externally(task_name, event))
    
    def _handle_collaboration_event(self, source: Any, event: AgentCollaborationEvent):
        """处理协作事件"""
        
        collaboration_type = event.business_context["collaboration_type"]
        agents_involved = event.business_context["agents_involved"]
        
        # 分析协作模式
        collaboration_pattern = self._analyze_collaboration_pattern(
            collaboration_type, agents_involved
        )
        
        # 记录协作历史
        self._record_collaboration_history(event, collaboration_pattern)
        
        # 优化建议
        optimization_suggestions = self._generate_collaboration_optimizations(
            collaboration_pattern
        )
        
        if optimization_suggestions:
            # 发送优化建议事件
            self._emit_optimization_suggestions(optimization_suggestions)
    
    def _check_alert_conditions(self, task_name: str, metrics: Dict[str, Any]):
        """检查告警条件"""
        
        avg_time = metrics["total_time"] / metrics["total_executions"]
        success_rate = metrics["successful_executions"] / metrics["total_executions"]
        error_rate = 1 - success_rate
        
        alerts = []
        
        if avg_time > self.alert_thresholds["execution_time"]:
            alerts.append({
                "type": "performance",
                "message": f"Task {task_name} average execution time ({avg_time:.2f}s) exceeds threshold",
                "severity": "warning"
            })
        
        if error_rate > self.alert_thresholds["error_rate"]:
            alerts.append({
                "type": "reliability",
                "message": f"Task {task_name} error rate ({error_rate:.2%}) exceeds threshold",
                "severity": "critical"
            })
        
        for alert in alerts:
            self._send_alert(alert)
    
    async def _store_metrics_externally(self, task_name: str, event: TaskExecutionMetricsEvent):
        """异步存储指标到外部系统"""
        
        # 这里可以集成Prometheus、InfluxDB等监控系统
        try:
            # 模拟外部存储
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            # 实际实现中可以发送到监控系统
            print(f"Stored metrics for {task_name} to external system")
            
        except Exception as e:
            print(f"Failed to store metrics externally: {e}")

# 使用示例
def setup_enterprise_monitoring():
    """设置企业监控"""
    
    # 初始化事件处理器
    event_handler = EnterpriseEventHandler()
    
    # 发布自定义事件的示例函数
    def publish_task_metrics(task_name: str, execution_time: float, success: bool):
        """发布任务指标事件"""
        
        event = TaskExecutionMetricsEvent(
            task_name=task_name,
            execution_time=execution_time,
            success=success,
            metrics={
                "cpu_usage": 0.5,
                "memory_usage": 0.3,
                "network_io": 1024
            }
        )
        
        crewai_event_bus.emit(None, event)
    
    return publish_task_metrics

# 实际使用
publish_metrics = setup_enterprise_monitoring()

# 在任务执行后发布指标
publish_metrics("data_analysis_task", 15.5, True)
```

## 6. Flow 工作流扩展

### 6.1 自定义 Flow 类型

#### 6.1.1 企业级工作流定义

```python
from crewai.flow import Flow, start, listen, or_, and_
from crewai import Agent, Task, Crew
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime

class EnterpriseFlowState(BaseModel):
    """企业级工作流状态"""
    
    flow_id: str = Field(description="工作流ID")
    current_stage: str = Field(description="当前阶段")
    business_context: Dict[str, Any] = Field(default_factory=dict)
    approvals: Dict[str, bool] = Field(default_factory=dict)
    audit_trail: List[Dict] = Field(default_factory=list)
    error_count: int = Field(default=0)
    retry_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ApprovalWorkflow(Flow[EnterpriseFlowState]):
    """需要审批的企业工作流"""
    
    def __init__(self):
        super().__init__()
        self.approval_agents = self._create_approval_agents()
        self.execution_agents = self._create_execution_agents()
    
    def _create_approval_agents(self) -> Dict[str, Agent]:
        """创建审批智能体"""
        
        return {
            "business_reviewer": Agent(
                role="业务审核专员",
                goal="审核业务需求的合理性和可行性",
                backstory="你是经验丰富的业务分析师，能够准确评估业务需求。"
            ),
            "technical_reviewer": Agent(
                role="技术审核专员", 
                goal="审核技术方案的可行性和风险",
                backstory="你是资深技术专家，能够识别技术风险和挑战。"
            ),
            "compliance_officer": Agent(
                role="合规审查官",
                goal="确保所有活动符合法规和公司政策",
                backstory="你是合规专家，熟悉相关法规和公司政策。"
            )
        }
    
    def _create_execution_agents(self) -> Dict[str, Agent]:
        """创建执行智能体"""
        
        return {
            "project_manager": Agent(
                role="项目经理",
                goal="协调和管理项目执行过程",
                backstory="你是经验丰富的项目经理，擅长协调资源和管理进度。"
            ),
            "developer": Agent(
                role="开发工程师", 
                goal="实施具体的技术解决方案",
                backstory="你是技能全面的开发工程师，能够解决复杂的技术问题。"
            )
        }
    
    @start()
    def initiate_request(self, request_data: Dict[str, Any]) -> EnterpriseFlowState:
        """启动审批流程"""
        
        flow_state = EnterpriseFlowState(
            flow_id=f"FLOW_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            current_stage="initiated",
            business_context=request_data
        )
        
        # 记录启动事件
        flow_state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "flow_initiated",
            "details": {"request_type": request_data.get("type", "unknown")}
        })
        
        print(f"工作流已启动: {flow_state.flow_id}")
        return flow_state
    
    @listen(initiate_request)
    def business_review(self, state: EnterpriseFlowState) -> EnterpriseFlowState:
        """业务审核阶段"""
        
        state.current_stage = "business_review"
        
        # 创建业务审核任务
        review_task = Task(
            description=f"""
            请审核以下业务请求：
            
            请求类型: {state.business_context.get('type', '未指定')}
            业务描述: {state.business_context.get('description', '未提供')}
            预期收益: {state.business_context.get('expected_benefits', '未说明')}
            资源需求: {state.business_context.get('resource_requirements', '未评估')}
            
            请评估：
            1. 业务需求的合理性和必要性
            2. 预期收益是否现实可行
            3. 资源投入是否合理
            4. 是否符合公司战略方向
            
            请给出明确的审批建议：通过/拒绝/需要修改
            """,
            expected_output="详细的业务审核报告和审批建议",
            agent=self.approval_agents["business_reviewer"]
        )
        
        # 执行业务审核
        crew = Crew(
            agents=[self.approval_agents["business_reviewer"]],
            tasks=[review_task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # 解析审批结果
        approval_status = self._parse_approval_result(str(result))
        state.approvals["business_review"] = approval_status
        
        # 更新审计记录
        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "business_review_completed",
            "result": approval_status,
            "details": {"reviewer": "business_reviewer"}
        })
        
        state.updated_at = datetime.now()
        
        return state
    
    @listen(business_review)
    def technical_review(self, state: EnterpriseFlowState) -> EnterpriseFlowState:
        """技术审核阶段"""
        
        # 只有业务审核通过才进行技术审核
        if not state.approvals.get("business_review", False):
            state.current_stage = "rejected"
            print("业务审核未通过，工作流终止")
            return state
        
        state.current_stage = "technical_review"
        
        # 创建技术审核任务
        tech_review_task = Task(
            description=f"""
            请对以下项目进行技术审核：
            
            项目描述: {state.business_context.get('description', '未提供')}
            技术需求: {state.business_context.get('technical_requirements', '未详细说明')}
            架构要求: {state.business_context.get('architecture', '未指定')}
            性能要求: {state.business_context.get('performance', '未明确')}
            
            请评估：
            1. 技术方案的可行性和复杂度
            2. 潜在的技术风险和挑战
            3. 所需的技术资源和技能
            4. 预估的开发时间和成本
            5. 技术选型的合理性
            
            请给出技术审批建议：通过/拒绝/需要修改
            """,
            expected_output="详细的技术审核报告和技术风险评估",
            agent=self.approval_agents["technical_reviewer"]
        )
        
        crew = Crew(
            agents=[self.approval_agents["technical_reviewer"]],
            tasks=[tech_review_task],
            verbose=True
        )
        
        result = crew.kickoff()
        approval_status = self._parse_approval_result(str(result))
        state.approvals["technical_review"] = approval_status
        
        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "technical_review_completed",
            "result": approval_status,
            "details": {"reviewer": "technical_reviewer"}
        })
        
        state.updated_at = datetime.now()
        
        return state
    
    @listen(technical_review)
    def compliance_check(self, state: EnterpriseFlowState) -> EnterpriseFlowState:
        """合规检查阶段"""
        
        # 检查前续审核结果
        if not all([
            state.approvals.get("business_review", False),
            state.approvals.get("technical_review", False)
        ]):
            state.current_stage = "rejected"
            print("前续审核未通过，工作流终止")
            return state
        
        state.current_stage = "compliance_check"
        
        # 合规检查任务
        compliance_task = Task(
            description=f"""
            请对以下项目进行合规性审查：
            
            项目类型: {state.business_context.get('type', '未指定')}
            涉及数据: {state.business_context.get('data_involved', '未说明')}
            用户群体: {state.business_context.get('target_users', '未明确')}
            地理范围: {state.business_context.get('geographic_scope', '未指定')}
            
            请检查：
            1. 是否符合数据保护法规（GDPR、个人信息保护法等）
            2. 是否符合行业监管要求
            3. 是否符合公司内部政策
            4. 是否存在法律风险
            5. 是否需要额外的合规措施
            
            请给出合规审查结果：通过/拒绝/需要补充合规措施
            """,
            expected_output="详细的合规审查报告和合规建议",
            agent=self.approval_agents["compliance_officer"]
        )
        
        crew = Crew(
            agents=[self.approval_agents["compliance_officer"]],
            tasks=[compliance_task],
            verbose=True
        )
        
        result = crew.kickoff()
        approval_status = self._parse_approval_result(str(result))
        state.approvals["compliance_check"] = approval_status
        
        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "compliance_check_completed", 
            "result": approval_status,
            "details": {"reviewer": "compliance_officer"}
        })
        
        state.updated_at = datetime.now()
        
        return state
    
    @listen(compliance_check)
    def final_approval_decision(self, state: EnterpriseFlowState) -> EnterpriseFlowState:
        """最终审批决定"""
        
        all_approvals = all([
            state.approvals.get("business_review", False),
            state.approvals.get("technical_review", False),
            state.approvals.get("compliance_check", False)
        ])
        
        if all_approvals:
            state.current_stage = "approved"
            print(f"🎉 工作流 {state.flow_id} 已获得完全批准！")
            
            # 可以在这里触发执行阶段
            return self.initiate_execution(state)
        else:
            state.current_stage = "rejected"
            rejected_stages = [
                stage for stage, approved in state.approvals.items() 
                if not approved
            ]
            print(f"❌ 工作流 {state.flow_id} 被拒绝。拒绝阶段: {rejected_stages}")
        
        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "final_decision",
            "result": state.current_stage,
            "details": {"all_approvals": state.approvals}
        })
        
        return state
    
    def initiate_execution(self, state: EnterpriseFlowState) -> EnterpriseFlowState:
        """启动执行阶段"""
        
        state.current_stage = "execution"
        
        print(f"🚀 开始执行已批准的项目: {state.flow_id}")
        
        # 这里可以触发实际的项目执行逻辑
        # 例如创建开发任务、分配资源等
        
        execution_task = Task(
            description=f"""
            项目已获得全面批准，请开始执行：
            
            项目信息: {state.business_context}
            
            请制定详细的执行计划，包括：
            1. 项目里程碑和时间计划
            2. 资源分配和团队组建
            3. 风险管控措施
            4. 质量保证流程
            5. 进度监控机制
            """,
            expected_output="详细的项目执行计划",
            agent=self.execution_agents["project_manager"]
        )
        
        crew = Crew(
            agents=[self.execution_agents["project_manager"]],
            tasks=[execution_task],
            verbose=True
        )
        
        execution_plan = crew.kickoff()
        
        state.business_context["execution_plan"] = str(execution_plan)
        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "execution_initiated",
            "details": {"project_manager": "assigned"}
        })
        
        return state
    
    def _parse_approval_result(self, result_text: str) -> bool:
        """解析审批结果"""
        
        # 简化的结果解析逻辑
        approval_keywords = ["通过", "批准", "同意", "approve", "pass", "accept"]
        rejection_keywords = ["拒绝", "驳回", "不通过", "reject", "deny", "refuse"]
        
        result_lower = result_text.lower()
        
        # 检查明确的批准信号
        if any(keyword in result_lower for keyword in approval_keywords):
            return True
        
        # 检查明确的拒绝信号    
        if any(keyword in result_lower for keyword in rejection_keywords):
            return False
        
        # 默认情况下需要人工审核
        print("⚠️  审批结果不明确，默认为拒绝状态")
        return False

# 使用示例
def run_approval_workflow():
    """运行审批工作流示例"""
    
    # 创建工作流实例
    workflow = ApprovalWorkflow()
    
    # 准备请求数据
    request_data = {
        "type": "新产品开发",
        "description": "开发AI驱动的客户服务系统",
        "expected_benefits": "提升客户满意度20%，减少人工成本30%",
        "resource_requirements": "5名开发工程师，3个月开发周期",
        "technical_requirements": "使用Python、FastAPI、PostgreSQL",
        "data_involved": "客户对话记录、服务历史数据",
        "target_users": "内部客服团队",
        "geographic_scope": "中国大陆"
    }
    
    # 启动工作流
    result = workflow.kickoff(request_data)
    
    return result

# 执行工作流
if __name__ == "__main__":
    final_state = run_approval_workflow()
    
    print("\n" + "="*50)
    print("工作流执行完成!")
    print(f"最终状态: {final_state.current_stage}")
    print(f"审批结果: {final_state.approvals}")
    print("\n审计轨迹:")
    for entry in final_state.audit_trail:
        print(f"  {entry['timestamp']}: {entry['action']} - {entry.get('result', 'N/A')}")
```

## 结论

本扩展开发指南提供了 CrewAI 框架的全面扩展方案，涵盖了从基础组件定制到企业级特性集成的完整开发路径。通过这些扩展模式和最佳实践，开发者可以：

### 关键收获

1. **组件扩展能力**
   - 创建高度专业化的 Agent 类型
   - 开发企业级工具和集成
   - 实现自定义 LLM 适配器
   - 构建专业知识源系统

2. **企业级特性**
   - 完整的监控和审计体系
   - 安全和合规性保障
   - 高可用性和性能优化
   - 复杂工作流编排能力

3. **最佳实践模式**
   - 模块化和可复用的设计
   - 类型安全和错误处理
   - 异步和并发优化
   - 企业级监控集成

### 扩展开发建议

1. **从简单开始**：先掌握基础扩展模式，再逐步添加企业特性
2. **重视测试**：为所有自定义组件编写全面的测试用例
3. **文档先行**：为扩展组件提供清晰的使用文档和示例
4. **性能监控**：在开发过程中持续关注性能表现
5. **社区贡献**：将通用的扩展组件贡献回开源社区

通过合理运用本指南提供的扩展模式，开发者可以构建满足特定业务需求的 CrewAI 应用，实现从原型验证到生产部署的完整技术路径。