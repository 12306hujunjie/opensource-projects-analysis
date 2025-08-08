# CrewAI 性能与监控深度分析

## 概述

本文档深入分析 CrewAI 框架的性能特征和监控体系，基于对框架核心实现的深度理解，提供企业级性能优化策略和全面的可观测性解决方案。通过系统性的性能分析和监控实践，帮助开发者构建高性能、可监控的多智能体协作系统。

## 1. 性能分析架构

### 1.1 性能分析层次模型

#### 1.1.1 四层性能分析框架

```python
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import psutil
import threading
import time
import asyncio
from collections import defaultdict, deque
import statistics

@dataclass
class PerformanceMetrics:
    """性能指标数据结构"""
    
    # 应用层指标
    task_execution_time: float
    agent_response_time: float
    crew_throughput: int
    success_rate: float
    
    # 框架层指标
    context_window_usage: float
    cache_hit_rate: float
    event_processing_latency: float
    memory_pool_efficiency: float
    
    # 系统层指标
    cpu_usage: float
    memory_usage: float
    network_io: int
    disk_io: int
    
    # 外部服务层指标
    llm_api_latency: float
    llm_api_error_rate: float
    tool_execution_time: float
    database_query_time: float
    
    # 元数据
    timestamp: datetime
    measurement_duration: float

class PerformanceAnalyzer:
    """多层次性能分析器"""
    
    def __init__(self, measurement_window: int = 60):
        self.measurement_window = measurement_window
        self.metrics_history: deque = deque(maxlen=1000)  # 保留最近1000个测量点
        self.real_time_metrics: Dict[str, Any] = {}
        self.performance_baselines: Dict[str, float] = {}
        self.alert_thresholds: Dict[str, Dict] = {}
        
        # 性能分析组件
        self.application_profiler = ApplicationLayerProfiler()
        self.framework_profiler = FrameworkLayerProfiler()
        self.system_profiler = SystemLayerProfiler()
        self.service_profiler = ExternalServiceProfiler()
        
        # 启动监控线程
        self.monitoring_thread = threading.Thread(
            target=self._continuous_monitoring, 
            daemon=True
        )
        self.monitoring_active = True
        self.monitoring_thread.start()
    
    def _continuous_monitoring(self):
        """持续性能监控循环"""
        
        while self.monitoring_active:
            try:
                start_time = time.time()
                
                # 收集各层性能数据
                app_metrics = self.application_profiler.collect_metrics()
                framework_metrics = self.framework_profiler.collect_metrics()
                system_metrics = self.system_profiler.collect_metrics()
                service_metrics = self.service_profiler.collect_metrics()
                
                # 组合性能指标
                combined_metrics = PerformanceMetrics(
                    # 应用层
                    task_execution_time=app_metrics.get('avg_task_time', 0.0),
                    agent_response_time=app_metrics.get('avg_agent_time', 0.0),
                    crew_throughput=app_metrics.get('tasks_per_minute', 0),
                    success_rate=app_metrics.get('success_rate', 1.0),
                    
                    # 框架层
                    context_window_usage=framework_metrics.get('context_usage', 0.0),
                    cache_hit_rate=framework_metrics.get('cache_hit_rate', 0.0),
                    event_processing_latency=framework_metrics.get('event_latency', 0.0),
                    memory_pool_efficiency=framework_metrics.get('memory_efficiency', 1.0),
                    
                    # 系统层
                    cpu_usage=system_metrics.get('cpu_percent', 0.0),
                    memory_usage=system_metrics.get('memory_percent', 0.0),
                    network_io=system_metrics.get('network_bytes', 0),
                    disk_io=system_metrics.get('disk_bytes', 0),
                    
                    # 外部服务层
                    llm_api_latency=service_metrics.get('llm_latency', 0.0),
                    llm_api_error_rate=service_metrics.get('llm_error_rate', 0.0),
                    tool_execution_time=service_metrics.get('tool_time', 0.0),
                    database_query_time=service_metrics.get('db_time', 0.0),
                    
                    # 元数据
                    timestamp=datetime.now(),
                    measurement_duration=time.time() - start_time
                )
                
                # 存储指标历史
                self.metrics_history.append(combined_metrics)
                
                # 更新实时指标
                self._update_real_time_metrics(combined_metrics)
                
                # 检查异常和告警
                self._check_performance_anomalies(combined_metrics)
                
                # 控制监控频率
                time.sleep(max(0, 1.0 - (time.time() - start_time)))
                
            except Exception as e:
                print(f"Performance monitoring error: {e}")
                time.sleep(1.0)
    
    def _update_real_time_metrics(self, metrics: PerformanceMetrics):
        """更新实时性能指标"""
        
        self.real_time_metrics.update({
            'current_cpu': metrics.cpu_usage,
            'current_memory': metrics.memory_usage,
            'current_throughput': metrics.crew_throughput,
            'current_success_rate': metrics.success_rate,
            'current_llm_latency': metrics.llm_api_latency,
            'last_update': metrics.timestamp
        })
        
        # 计算趋势指标
        if len(self.metrics_history) >= 10:
            recent_metrics = list(self.metrics_history)[-10:]
            
            self.real_time_metrics.update({
                'cpu_trend': self._calculate_trend([m.cpu_usage for m in recent_metrics]),
                'memory_trend': self._calculate_trend([m.memory_usage for m in recent_metrics]),
                'latency_trend': self._calculate_trend([m.llm_api_latency for m in recent_metrics]),
                'throughput_trend': self._calculate_trend([m.crew_throughput for m in recent_metrics])
            })
    
    def get_performance_report(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """生成性能报告"""
        
        if time_range is None:
            time_range = timedelta(minutes=30)
        
        cutoff_time = datetime.now() - time_range
        relevant_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not relevant_metrics:
            return {"error": "No metrics available for the specified time range"}
        
        report = {
            "analysis_period": {
                "start": relevant_metrics[0].timestamp,
                "end": relevant_metrics[-1].timestamp,
                "duration_minutes": time_range.total_seconds() / 60,
                "sample_count": len(relevant_metrics)
            },
            
            "application_performance": self._analyze_application_performance(relevant_metrics),
            "framework_performance": self._analyze_framework_performance(relevant_metrics),
            "system_performance": self._analyze_system_performance(relevant_metrics),
            "service_performance": self._analyze_service_performance(relevant_metrics),
            
            "performance_insights": self._generate_performance_insights(relevant_metrics),
            "optimization_recommendations": self._generate_optimization_recommendations(relevant_metrics)
        }
        
        return report
```

#### 1.1.2 应用层性能分析器

```python
class ApplicationLayerProfiler:
    """应用层性能分析器"""
    
    def __init__(self):
        self.task_metrics: Dict[str, List[float]] = defaultdict(list)
        self.agent_metrics: Dict[str, List[float]] = defaultdict(list)
        self.crew_metrics: Dict[str, List[float]] = defaultdict(list)
        self.execution_history: deque = deque(maxlen=1000)
    
    def track_task_execution(self, task_id: str, execution_time: float, 
                           success: bool, complexity_score: float = 1.0):
        """跟踪任务执行指标"""
        
        self.task_metrics[task_id].append(execution_time)
        
        # 记录执行历史
        self.execution_history.append({
            'timestamp': datetime.now(),
            'type': 'task',
            'id': task_id,
            'execution_time': execution_time,
            'success': success,
            'complexity_score': complexity_score
        })
        
        # 维护历史数据大小
        if len(self.task_metrics[task_id]) > 100:
            self.task_metrics[task_id] = self.task_metrics[task_id][-100:]
    
    def track_agent_interaction(self, agent_id: str, response_time: float, 
                              token_count: int, tool_calls: int = 0):
        """跟踪智能体交互指标"""
        
        self.agent_metrics[agent_id].append(response_time)
        
        self.execution_history.append({
            'timestamp': datetime.now(),
            'type': 'agent',
            'id': agent_id,
            'response_time': response_time,
            'token_count': token_count,
            'tool_calls': tool_calls
        })
    
    def track_crew_execution(self, crew_id: str, total_time: float, 
                           task_count: int, success_rate: float):
        """跟踪团队执行指标"""
        
        self.crew_metrics[crew_id].append(total_time)
        
        self.execution_history.append({
            'timestamp': datetime.now(),
            'type': 'crew',
            'id': crew_id,
            'total_time': total_time,
            'task_count': task_count,
            'success_rate': success_rate
        })
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集应用层指标"""
        
        recent_executions = [
            ex for ex in self.execution_history 
            if ex['timestamp'] > datetime.now() - timedelta(minutes=1)
        ]
        
        task_executions = [ex for ex in recent_executions if ex['type'] == 'task']
        agent_interactions = [ex for ex in recent_executions if ex['type'] == 'agent']
        crew_executions = [ex for ex in recent_executions if ex['type'] == 'crew']
        
        metrics = {
            'tasks_per_minute': len(task_executions),
            'agents_per_minute': len(agent_interactions),
            'crews_per_minute': len(crew_executions),
            
            'avg_task_time': statistics.mean([ex['execution_time'] for ex in task_executions]) if task_executions else 0.0,
            'avg_agent_time': statistics.mean([ex['response_time'] for ex in agent_interactions]) if agent_interactions else 0.0,
            'avg_crew_time': statistics.mean([ex['total_time'] for ex in crew_executions]) if crew_executions else 0.0,
            
            'success_rate': statistics.mean([ex.get('success', True) for ex in recent_executions]) if recent_executions else 1.0,
            
            'complexity_distribution': self._analyze_complexity_distribution(task_executions),
            'performance_trends': self._calculate_performance_trends()
        }
        
        return metrics
    
    def _analyze_complexity_distribution(self, executions: List[Dict]) -> Dict[str, int]:
        """分析任务复杂度分布"""
        
        distribution = {'low': 0, 'medium': 0, 'high': 0}
        
        for execution in executions:
            complexity = execution.get('complexity_score', 1.0)
            if complexity < 0.5:
                distribution['low'] += 1
            elif complexity < 1.5:
                distribution['medium'] += 1
            else:
                distribution['high'] += 1
        
        return distribution
```

### 1.2 框架层性能分析

#### 1.2.1 CrewAI 核心组件性能监控

```python
class FrameworkLayerProfiler:
    """框架层性能分析器"""
    
    def __init__(self):
        self.context_usage_history: deque = deque(maxlen=200)
        self.cache_statistics: Dict[str, int] = defaultdict(int)
        self.event_processing_times: deque = deque(maxlen=500)
        self.memory_pool_stats: Dict[str, Any] = {}
        
        # 挂钩到CrewAI事件系统
        self._setup_framework_hooks()
    
    def _setup_framework_hooks(self):
        """设置框架性能监控挂钩"""
        
        # 这里需要与CrewAI的事件系统集成
        # 监控关键框架事件的性能
        pass
    
    def track_context_usage(self, agent_id: str, context_size: int, 
                          max_context: int, compression_applied: bool = False):
        """跟踪上下文窗口使用情况"""
        
        usage_ratio = context_size / max_context if max_context > 0 else 0
        
        self.context_usage_history.append({
            'timestamp': datetime.now(),
            'agent_id': agent_id,
            'context_size': context_size,
            'max_context': max_context,
            'usage_ratio': usage_ratio,
            'compression_applied': compression_applied
        })
    
    def track_cache_operation(self, operation: str, hit: bool, 
                            cache_type: str = 'default'):
        """跟踪缓存操作"""
        
        key = f"{cache_type}_{operation}_{'hit' if hit else 'miss'}"
        self.cache_statistics[key] += 1
        
        # 记录缓存操作时间戳用于计算命中率
        self.cache_statistics[f"{cache_type}_total"] += 1
        if hit:
            self.cache_statistics[f"{cache_type}_hits"] += 1
    
    def track_event_processing(self, event_type: str, processing_time: float, 
                             handler_count: int, success: bool):
        """跟踪事件处理性能"""
        
        self.event_processing_times.append({
            'timestamp': datetime.now(),
            'event_type': event_type,
            'processing_time': processing_time,
            'handler_count': handler_count,
            'success': success
        })
    
    def track_memory_pool_usage(self, pool_type: str, allocated: int, 
                               total: int, fragmentation: float):
        """跟踪内存池使用情况"""
        
        self.memory_pool_stats[pool_type] = {
            'timestamp': datetime.now(),
            'allocated': allocated,
            'total': total,
            'utilization': allocated / total if total > 0 else 0,
            'fragmentation': fragmentation
        }
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集框架层指标"""
        
        # 计算上下文使用率
        recent_context = [
            ctx for ctx in self.context_usage_history 
            if ctx['timestamp'] > datetime.now() - timedelta(minutes=5)
        ]
        
        avg_context_usage = statistics.mean([
            ctx['usage_ratio'] for ctx in recent_context
        ]) if recent_context else 0.0
        
        # 计算缓存命中率
        cache_hit_rates = {}
        for cache_type in set(key.split('_')[0] for key in self.cache_statistics.keys()):
            total = self.cache_statistics.get(f"{cache_type}_total", 0)
            hits = self.cache_statistics.get(f"{cache_type}_hits", 0)
            cache_hit_rates[cache_type] = hits / total if total > 0 else 0.0
        
        overall_cache_hit_rate = statistics.mean(cache_hit_rates.values()) if cache_hit_rates else 0.0
        
        # 计算事件处理延迟
        recent_events = [
            evt for evt in self.event_processing_times 
            if evt['timestamp'] > datetime.now() - timedelta(minutes=5)
        ]
        
        avg_event_latency = statistics.mean([
            evt['processing_time'] for evt in recent_events
        ]) if recent_events else 0.0
        
        # 计算内存池效率
        total_utilization = 0.0
        active_pools = 0
        
        for pool_type, stats in self.memory_pool_stats.items():
            if stats['timestamp'] > datetime.now() - timedelta(minutes=1):
                total_utilization += stats['utilization']
                active_pools += 1
        
        avg_memory_efficiency = total_utilization / active_pools if active_pools > 0 else 1.0
        
        return {
            'context_usage': avg_context_usage,
            'cache_hit_rate': overall_cache_hit_rate,
            'cache_hit_rates_by_type': cache_hit_rates,
            'event_latency': avg_event_latency,
            'memory_efficiency': avg_memory_efficiency,
            
            'context_compression_rate': len([ctx for ctx in recent_context if ctx['compression_applied']]) / len(recent_context) if recent_context else 0.0,
            'event_success_rate': len([evt for evt in recent_events if evt['success']]) / len(recent_events) if recent_events else 1.0,
            'memory_fragmentation': statistics.mean([stats['fragmentation'] for stats in self.memory_pool_stats.values()]) if self.memory_pool_stats else 0.0
        }
```

## 2. 关键性能指标 (KPI) 体系

### 2.1 多维度 KPI 框架

#### 2.1.1 业务关键指标

```python
class BusinessKPITracker:
    """业务关键绩效指标跟踪器"""
    
    def __init__(self):
        self.kpi_definitions = {
            # 效率指标
            "task_completion_rate": {
                "description": "任务完成率",
                "unit": "percentage",
                "target": 0.95,
                "critical_threshold": 0.85,
                "calculation": "completed_tasks / total_tasks"
            },
            
            "average_task_duration": {
                "description": "平均任务执行时间",
                "unit": "seconds", 
                "target": 120.0,
                "critical_threshold": 300.0,
                "calculation": "sum(task_durations) / count(tasks)"
            },
            
            "crew_throughput": {
                "description": "团队吞吐量",
                "unit": "tasks_per_hour",
                "target": 50.0,
                "critical_threshold": 20.0,
                "calculation": "completed_tasks_per_hour"
            },
            
            # 质量指标
            "output_quality_score": {
                "description": "输出质量评分",
                "unit": "score_0_to_10",
                "target": 8.0,
                "critical_threshold": 6.0,
                "calculation": "average_quality_ratings"
            },
            
            "error_rate": {
                "description": "错误率",
                "unit": "percentage",
                "target": 0.02,
                "critical_threshold": 0.10,
                "calculation": "failed_executions / total_executions"
            },
            
            "retry_rate": {
                "description": "重试率",
                "unit": "percentage", 
                "target": 0.05,
                "critical_threshold": 0.20,
                "calculation": "retry_attempts / total_attempts"
            },
            
            # 成本指标
            "cost_per_task": {
                "description": "单任务成本",
                "unit": "currency",
                "target": 0.50,
                "critical_threshold": 2.00,
                "calculation": "total_costs / completed_tasks"
            },
            
            "token_efficiency": {
                "description": "Token使用效率", 
                "unit": "tokens_per_task",
                "target": 5000.0,
                "critical_threshold": 15000.0,
                "calculation": "total_tokens / completed_tasks"
            },
            
            # 用户体验指标
            "response_time_p95": {
                "description": "95分位响应时间",
                "unit": "seconds",
                "target": 30.0,
                "critical_threshold": 120.0,
                "calculation": "95th_percentile(response_times)"
            },
            
            "user_satisfaction": {
                "description": "用户满意度",
                "unit": "score_1_to_5",
                "target": 4.2,
                "critical_threshold": 3.0,
                "calculation": "average_user_ratings"
            }
        }
        
        self.current_values: Dict[str, float] = {}
        self.historical_data: Dict[str, deque] = {
            kpi: deque(maxlen=1440)  # 24小时数据，按分钟
            for kpi in self.kpi_definitions
        }
        self.alerts: List[Dict] = []
    
    def update_kpi(self, kpi_name: str, value: float, timestamp: Optional[datetime] = None):
        """更新KPI值"""
        
        if kpi_name not in self.kpi_definitions:
            raise ValueError(f"Unknown KPI: {kpi_name}")
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # 更新当前值
        self.current_values[kpi_name] = value
        
        # 添加到历史数据
        self.historical_data[kpi_name].append({
            'timestamp': timestamp,
            'value': value
        })
        
        # 检查告警条件
        self._check_kpi_thresholds(kpi_name, value)
    
    def _check_kpi_thresholds(self, kpi_name: str, value: float):
        """检查KPI阈值告警"""
        
        definition = self.kpi_definitions[kpi_name]
        target = definition['target']
        critical_threshold = definition['critical_threshold']
        
        # 确定是否超出临界阈值
        is_critical = False
        
        # 对于"越小越好"的指标（如错误率、响应时间）
        if kpi_name in ['error_rate', 'retry_rate', 'cost_per_task', 'token_efficiency', 'average_task_duration', 'response_time_p95']:
            if value > critical_threshold:
                is_critical = True
                severity = "critical"
            elif value > target:
                severity = "warning"
            else:
                return  # 正常范围内
        
        # 对于"越大越好"的指标（如完成率、质量评分）
        else:
            if value < critical_threshold:
                is_critical = True
                severity = "critical"
            elif value < target:
                severity = "warning"
            else:
                return  # 正常范围内
        
        # 创建告警
        alert = {
            'timestamp': datetime.now(),
            'kpi_name': kpi_name,
            'current_value': value,
            'target_value': target,
            'critical_threshold': critical_threshold,
            'severity': severity,
            'message': f"{definition['description']} ({value:.2f}) {'低于' if not is_critical else '超出'}{'目标' if severity == 'warning' else '临界'}阈值"
        }
        
        self.alerts.append(alert)
        
        # 保持告警历史长度
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
    
    def get_kpi_dashboard(self) -> Dict[str, Any]:
        """获取KPI仪表板数据"""
        
        dashboard = {
            'overview': {
                'total_kpis': len(self.kpi_definitions),
                'healthy_kpis': 0,
                'warning_kpis': 0,
                'critical_kpis': 0,
                'last_updated': max([
                    data[-1]['timestamp'] for data in self.historical_data.values() 
                    if data
                ]) if any(self.historical_data.values()) else None
            },
            'current_status': {},
            'trends': {},
            'recent_alerts': self.alerts[-10:] if self.alerts else []
        }
        
        # 分析每个KPI的当前状态
        for kpi_name, definition in self.kpi_definitions.items():
            current_value = self.current_values.get(kpi_name, 0.0)
            target = definition['target']
            critical_threshold = definition['critical_threshold']
            
            # 计算状态
            if kpi_name in ['error_rate', 'retry_rate', 'cost_per_task', 'token_efficiency', 'average_task_duration', 'response_time_p95']:
                if current_value > critical_threshold:
                    status = "critical"
                    dashboard['overview']['critical_kpis'] += 1
                elif current_value > target:
                    status = "warning"
                    dashboard['overview']['warning_kpis'] += 1
                else:
                    status = "healthy"
                    dashboard['overview']['healthy_kpis'] += 1
            else:
                if current_value < critical_threshold:
                    status = "critical"
                    dashboard['overview']['critical_kpis'] += 1
                elif current_value < target:
                    status = "warning"
                    dashboard['overview']['warning_kpis'] += 1
                else:
                    status = "healthy"
                    dashboard['overview']['healthy_kpis'] += 1
            
            dashboard['current_status'][kpi_name] = {
                'value': current_value,
                'status': status,
                'target': target,
                'description': definition['description'],
                'unit': definition['unit']
            }
            
            # 计算趋势
            historical_values = [
                point['value'] for point in self.historical_data[kpi_name][-60:]  # 最近60分钟
            ]
            
            if len(historical_values) >= 2:
                trend = self._calculate_trend(historical_values)
                dashboard['trends'][kpi_name] = trend
        
        return dashboard
```

### 2.2 实时监控体系

#### 2.2.1 实时指标收集器

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from prometheus_client import Counter, Histogram, Gauge, start_http_server

class RealTimeMetricsCollector:
    """实时指标收集器"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Prometheus指标定义
        self.task_counter = Counter('crewai_tasks_total', 'Total number of tasks', ['status', 'agent_type'])
        self.task_duration = Histogram('crewai_task_duration_seconds', 'Task execution duration')
        self.agent_response_time = Histogram('crewai_agent_response_seconds', 'Agent response time')
        self.memory_usage = Gauge('crewai_memory_usage_bytes', 'Memory usage in bytes')
        self.active_tasks = Gauge('crewai_active_tasks', 'Number of active tasks')
        self.llm_api_calls = Counter('crewai_llm_api_calls_total', 'Total LLM API calls', ['model', 'status'])
        self.llm_latency = Histogram('crewai_llm_latency_seconds', 'LLM API latency')
        self.cache_operations = Counter('crewai_cache_operations_total', 'Cache operations', ['type', 'result'])
        
        # 自定义指标收集
        self.custom_metrics: Dict[str, Any] = {}
        self.metric_callbacks: List[callable] = []
        
        # 启动Prometheus服务器
        start_http_server(self.port)
        
        # 启动实时收集循环
        self.collection_active = True
        asyncio.create_task(self._real_time_collection_loop())
    
    async def _real_time_collection_loop(self):
        """实时指标收集循环"""
        
        while self.collection_active:
            try:
                # 收集系统指标
                await self._collect_system_metrics()
                
                # 执行自定义回调
                for callback in self.metric_callbacks:
                    try:
                        await callback()
                    except Exception as e:
                        print(f"Metric callback error: {e}")
                
                # 每秒收集一次
                await asyncio.sleep(1.0)
                
            except Exception as e:
                print(f"Real-time collection error: {e}")
                await asyncio.sleep(5.0)
    
    async def _collect_system_metrics(self):
        """收集系统级指标"""
        
        # 内存使用情况
        memory_info = psutil.virtual_memory()
        self.memory_usage.set(memory_info.used)
        
        # 进程信息
        process = psutil.Process()
        process_memory = process.memory_info().rss
        
        # 更新自定义指标
        self.custom_metrics.update({
            'system_memory_percent': memory_info.percent,
            'process_memory_mb': process_memory / 1024 / 1024,
            'cpu_count': psutil.cpu_count(),
            'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
        })
    
    def record_task_execution(self, duration: float, success: bool, agent_type: str = "default"):
        """记录任务执行指标"""
        
        status = "success" if success else "failure"
        self.task_counter.labels(status=status, agent_type=agent_type).inc()
        self.task_duration.observe(duration)
    
    def record_agent_response(self, response_time: float):
        """记录智能体响应时间"""
        
        self.agent_response_time.observe(response_time)
    
    def record_llm_api_call(self, model: str, latency: float, success: bool):
        """记录LLM API调用"""
        
        status = "success" if success else "failure"
        self.llm_api_calls.labels(model=model, status=status).inc()
        self.llm_latency.observe(latency)
    
    def record_cache_operation(self, operation_type: str, hit: bool):
        """记录缓存操作"""
        
        result = "hit" if hit else "miss"
        self.cache_operations.labels(type=operation_type, result=result).inc()
    
    def set_active_tasks(self, count: int):
        """设置当前活跃任务数"""
        
        self.active_tasks.set(count)
    
    def add_custom_metric_callback(self, callback: callable):
        """添加自定义指标回调"""
        
        self.metric_callbacks.append(callback)
    
    def get_current_metrics_summary(self) -> Dict[str, Any]:
        """获取当前指标摘要"""
        
        return {
            'timestamp': datetime.now(),
            'system_metrics': self.custom_metrics,
            'active_tasks': self.active_tasks._value._value,
            'prometheus_metrics_url': f'http://localhost:{self.port}/metrics'
        }
```

## 3. 性能瓶颈识别与优化

### 3.1 智能瓶颈检测

#### 3.1.1 多层次瓶颈分析器

```python
class PerformanceBottleneckDetector:
    """性能瓶颈检测器"""
    
    def __init__(self, analyzer: PerformanceAnalyzer):
        self.analyzer = analyzer
        self.bottleneck_patterns = self._initialize_bottleneck_patterns()
        self.optimization_strategies = self._initialize_optimization_strategies()
    
    def _initialize_bottleneck_patterns(self) -> Dict[str, Dict]:
        """初始化瓶颈识别模式"""
        
        return {
            "high_cpu_usage": {
                "condition": lambda metrics: metrics.cpu_usage > 80,
                "severity": "high",
                "category": "system",
                "description": "CPU使用率过高",
                "potential_causes": [
                    "计算密集型任务过多",
                    "并发执行过度",
                    "算法效率问题",
                    "无限循环或死循环"
                ]
            },
            
            "memory_exhaustion": {
                "condition": lambda metrics: metrics.memory_usage > 85,
                "severity": "critical",
                "category": "system", 
                "description": "内存使用率接近极限",
                "potential_causes": [
                    "内存泄漏",
                    "大对象未释放",
                    "缓存策略不当",
                    "批处理数据过大"
                ]
            },
            
            "llm_api_latency": {
                "condition": lambda metrics: metrics.llm_api_latency > 10.0,
                "severity": "medium",
                "category": "external_service",
                "description": "LLM API响应延迟过高", 
                "potential_causes": [
                    "网络连接问题",
                    "API服务器负载过高",
                    "请求参数设置不当",
                    "模型选择不合适"
                ]
            },
            
            "low_cache_hit_rate": {
                "condition": lambda metrics: metrics.cache_hit_rate < 0.5,
                "severity": "medium",
                "category": "framework",
                "description": "缓存命中率过低",
                "potential_causes": [
                    "缓存策略设置错误",
                    "缓存键设计问题",
                    "缓存过期时间过短",
                    "数据变化频率过高"
                ]
            },
            
            "high_context_usage": {
                "condition": lambda metrics: metrics.context_window_usage > 0.9,
                "severity": "high",
                "category": "framework",
                "description": "上下文窗口使用率过高",
                "potential_causes": [
                    "对话历史过长",
                    "任务描述过于详细",
                    "上下文压缩不足",
                    "模型选择不当"
                ]
            },
            
            "low_success_rate": {
                "condition": lambda metrics: metrics.success_rate < 0.8,
                "severity": "critical",
                "category": "application",
                "description": "任务成功率过低",
                "potential_causes": [
                    "任务设计问题",
                    "智能体能力不足",
                    "工具配置错误",
                    "外部依赖不稳定"
                ]
            },
            
            "poor_throughput": {
                "condition": lambda metrics: metrics.crew_throughput < 5,
                "severity": "high",
                "category": "application", 
                "description": "系统吞吐量过低",
                "potential_causes": [
                    "任务执行时间过长",
                    "并发度设置过低",
                    "资源争用问题",
                    "依赖服务响应慢"
                ]
            }
        }
    
    def _initialize_optimization_strategies(self) -> Dict[str, Dict]:
        """初始化优化策略"""
        
        return {
            "high_cpu_usage": {
                "immediate_actions": [
                    "降低并发任务数量",
                    "暂停非关键任务",
                    "启用任务队列缓冲"
                ],
                "short_term_solutions": [
                    "优化算法实现",
                    "添加任务优先级管理",
                    "实施负载均衡"
                ],
                "long_term_solutions": [
                    "升级硬件配置",
                    "重构计算密集型模块",
                    "实施分布式处理"
                ]
            },
            
            "memory_exhaustion": {
                "immediate_actions": [
                    "强制垃圾回收",
                    "清理缓存数据",
                    "终止内存占用大的任务"
                ],
                "short_term_solutions": [
                    "优化数据结构使用",
                    "实施内存池管理",
                    "添加内存使用监控"
                ],
                "long_term_solutions": [
                    "重构内存使用模式",
                    "实施数据流式处理",
                    "升级服务器内存"
                ]
            },
            
            "llm_api_latency": {
                "immediate_actions": [
                    "启用请求缓存",
                    "降低并发请求数",
                    "切换到更快的模型"
                ],
                "short_term_solutions": [
                    "优化请求参数",
                    "实施请求批处理",
                    "添加连接池管理"
                ],
                "long_term_solutions": [
                    "部署本地LLM服务",
                    "实施多LLM负载均衡",
                    "优化网络架构"
                ]
            },
            
            "low_cache_hit_rate": {
                "immediate_actions": [
                    "调整缓存过期时间",
                    "优化缓存键策略",
                    "增加缓存容量"
                ],
                "short_term_solutions": [
                    "实施多级缓存",
                    "优化缓存数据结构",
                    "添加缓存预热机制"
                ],
                "long_term_solutions": [
                    "重设计缓存架构",
                    "实施分布式缓存",
                    "优化数据访问模式"
                ]
            }
        }
    
    def detect_bottlenecks(self, time_window: timedelta = timedelta(minutes=5)) -> List[Dict[str, Any]]:
        """检测性能瓶颈"""
        
        # 获取性能报告
        report = self.analyzer.get_performance_report(time_window)
        
        if "error" in report:
            return []
        
        # 提取关键指标
        recent_metrics = self.analyzer.metrics_history[-1] if self.analyzer.metrics_history else None
        
        if not recent_metrics:
            return []
        
        detected_bottlenecks = []
        
        # 检查每个瓶颈模式
        for pattern_name, pattern_config in self.bottleneck_patterns.items():
            try:
                if pattern_config["condition"](recent_metrics):
                    bottleneck = {
                        "name": pattern_name,
                        "severity": pattern_config["severity"],
                        "category": pattern_config["category"],
                        "description": pattern_config["description"],
                        "potential_causes": pattern_config["potential_causes"],
                        "detected_at": datetime.now(),
                        "current_metrics": {
                            "cpu_usage": recent_metrics.cpu_usage,
                            "memory_usage": recent_metrics.memory_usage,
                            "llm_api_latency": recent_metrics.llm_api_latency,
                            "cache_hit_rate": recent_metrics.cache_hit_rate,
                            "context_window_usage": recent_metrics.context_window_usage,
                            "success_rate": recent_metrics.success_rate,
                            "crew_throughput": recent_metrics.crew_throughput
                        }
                    }
                    
                    # 添加优化建议
                    if pattern_name in self.optimization_strategies:
                        bottleneck["optimization_suggestions"] = self.optimization_strategies[pattern_name]
                    
                    detected_bottlenecks.append(bottleneck)
                    
            except Exception as e:
                print(f"Error checking bottleneck pattern {pattern_name}: {e}")
        
        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        detected_bottlenecks.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return detected_bottlenecks
    
    def generate_optimization_plan(self, bottlenecks: List[Dict]) -> Dict[str, Any]:
        """生成优化计划"""
        
        if not bottlenecks:
            return {"status": "healthy", "message": "未检测到性能瓶颈"}
        
        plan = {
            "analysis_timestamp": datetime.now(),
            "bottlenecks_detected": len(bottlenecks),
            "severity_distribution": {},
            "immediate_actions": [],
            "short_term_plan": [],
            "long_term_strategy": [],
            "estimated_impact": {}
        }
        
        # 统计严重程度分布
        for bottleneck in bottlenecks:
            severity = bottleneck["severity"]
            plan["severity_distribution"][severity] = plan["severity_distribution"].get(severity, 0) + 1
        
        # 收集优化建议
        immediate_actions = set()
        short_term_solutions = set()
        long_term_solutions = set()
        
        for bottleneck in bottlenecks:
            suggestions = bottleneck.get("optimization_suggestions", {})
            
            immediate_actions.update(suggestions.get("immediate_actions", []))
            short_term_solutions.update(suggestions.get("short_term_solutions", []))
            long_term_solutions.update(suggestions.get("long_term_solutions", []))
        
        plan["immediate_actions"] = list(immediate_actions)
        plan["short_term_plan"] = list(short_term_solutions)
        plan["long_term_strategy"] = list(long_term_solutions)
        
        # 评估优化影响
        plan["estimated_impact"] = self._estimate_optimization_impact(bottlenecks)
        
        return plan
    
    def _estimate_optimization_impact(self, bottlenecks: List[Dict]) -> Dict[str, Any]:
        """估算优化影响"""
        
        impact_scores = {
            "performance_improvement": 0,
            "cost_reduction": 0,
            "reliability_improvement": 0,
            "user_experience_improvement": 0
        }
        
        impact_weights = {
            "critical": {"performance": 0.8, "cost": 0.6, "reliability": 0.9, "ux": 0.7},
            "high": {"performance": 0.6, "cost": 0.4, "reliability": 0.7, "ux": 0.5},
            "medium": {"performance": 0.4, "cost": 0.3, "reliability": 0.5, "ux": 0.3},
            "low": {"performance": 0.2, "cost": 0.1, "reliability": 0.3, "ux": 0.2}
        }
        
        for bottleneck in bottlenecks:
            severity = bottleneck["severity"]
            weights = impact_weights.get(severity, impact_weights["low"])
            
            impact_scores["performance_improvement"] += weights["performance"]
            impact_scores["cost_reduction"] += weights["cost"] 
            impact_scores["reliability_improvement"] += weights["reliability"]
            impact_scores["user_experience_improvement"] += weights["ux"]
        
        # 归一化分数 (0-100)
        max_possible_score = len(bottlenecks) * 0.9
        for key in impact_scores:
            impact_scores[key] = min(100, (impact_scores[key] / max_possible_score) * 100) if max_possible_score > 0 else 0
        
        return impact_scores
```

### 3.2 自动优化引擎

#### 3.2.1 智能参数调优

```python
class AutoOptimizationEngine:
    """自动优化引擎"""
    
    def __init__(self, performance_analyzer: PerformanceAnalyzer, 
                 bottleneck_detector: PerformanceBottleneckDetector):
        self.analyzer = performance_analyzer
        self.detector = bottleneck_detector
        
        # 优化参数范围
        self.parameter_ranges = {
            "max_iterations": (5, 50),
            "temperature": (0.1, 1.0), 
            "cache_ttl": (60, 3600),
            "batch_size": (1, 20),
            "concurrent_tasks": (1, 10),
            "context_window_threshold": (0.5, 0.9)
        }
        
        # 优化历史
        self.optimization_history: List[Dict] = []
        self.current_config: Dict[str, Any] = {}
        self.baseline_metrics: Optional[Dict] = None
        
        # 启动自动优化
        self.auto_optimization_enabled = False
        asyncio.create_task(self._auto_optimization_loop())
    
    async def _auto_optimization_loop(self):
        """自动优化循环"""
        
        while True:
            try:
                if self.auto_optimization_enabled:
                    # 检测瓶颈
                    bottlenecks = self.detector.detect_bottlenecks()
                    
                    if bottlenecks:
                        # 执行自动优化
                        await self._execute_auto_optimization(bottlenecks)
                
                # 每5分钟检查一次
                await asyncio.sleep(300)
                
            except Exception as e:
                print(f"Auto-optimization error: {e}")
                await asyncio.sleep(60)
    
    async def _execute_auto_optimization(self, bottlenecks: List[Dict]):
        """执行自动优化"""
        
        print(f"🔧 检测到 {len(bottlenecks)} 个性能瓶颈，开始自动优化...")
        
        # 备份当前配置
        previous_config = self.current_config.copy()
        
        # 根据瓶颈类型选择优化策略
        optimization_applied = False
        
        for bottleneck in bottlenecks:
            if bottleneck["name"] == "high_cpu_usage":
                # 降低并发度和迭代次数
                if "concurrent_tasks" in self.current_config:
                    new_value = max(1, int(self.current_config["concurrent_tasks"] * 0.7))
                    self.current_config["concurrent_tasks"] = new_value
                    optimization_applied = True
                
                if "max_iterations" in self.current_config:
                    new_value = max(5, int(self.current_config["max_iterations"] * 0.8))
                    self.current_config["max_iterations"] = new_value
                    optimization_applied = True
            
            elif bottleneck["name"] == "memory_exhaustion":
                # 减少批处理大小和缓存时间
                if "batch_size" in self.current_config:
                    new_value = max(1, int(self.current_config["batch_size"] * 0.5))
                    self.current_config["batch_size"] = new_value
                    optimization_applied = True
                
                if "cache_ttl" in self.current_config:
                    new_value = max(60, int(self.current_config["cache_ttl"] * 0.6))
                    self.current_config["cache_ttl"] = new_value
                    optimization_applied = True
            
            elif bottleneck["name"] == "llm_api_latency":
                # 调整温度参数和上下文阈值
                if "temperature" in self.current_config:
                    new_value = min(1.0, self.current_config["temperature"] * 0.8)
                    self.current_config["temperature"] = new_value
                    optimization_applied = True
                
                if "context_window_threshold" in self.current_config:
                    new_value = max(0.5, self.current_config["context_window_threshold"] * 0.9)
                    self.current_config["context_window_threshold"] = new_value
                    optimization_applied = True
        
        if optimization_applied:
            # 应用新配置
            await self._apply_configuration(self.current_config)
            
            # 等待配置生效
            await asyncio.sleep(60)
            
            # 评估优化效果
            improvement = await self._evaluate_optimization_impact(previous_config)
            
            # 记录优化历史
            self.optimization_history.append({
                "timestamp": datetime.now(),
                "bottlenecks": bottlenecks,
                "previous_config": previous_config,
                "new_config": self.current_config.copy(),
                "improvement": improvement,
                "success": improvement.get("overall_improvement", 0) > 0.05
            })
            
            print(f"✅ 自动优化完成，总体改进: {improvement.get('overall_improvement', 0):.2%}")
        
        else:
            print("⚠️ 未找到适用的自动优化策略")
    
    async def _apply_configuration(self, config: Dict[str, Any]):
        """应用配置更改"""
        
        # 这里需要与CrewAI的配置系统集成
        # 应用新的参数配置
        print(f"应用新配置: {config}")
    
    async def _evaluate_optimization_impact(self, previous_config: Dict) -> Dict[str, float]:
        """评估优化影响"""
        
        # 收集优化前后的性能数据
        current_report = self.analyzer.get_performance_report(timedelta(minutes=5))
        
        if "error" in current_report:
            return {"error": "无法获取性能数据"}
        
        # 计算关键指标的改进情况
        improvements = {}
        
        # 获取当前指标
        current_metrics = self.analyzer.real_time_metrics
        
        if self.baseline_metrics:
            # 计算各项指标的改进
            for metric_name in ["cpu_usage", "memory_usage", "llm_api_latency", "success_rate", "crew_throughput"]:
                if metric_name in current_metrics and metric_name in self.baseline_metrics:
                    current_value = current_metrics[metric_name]
                    baseline_value = self.baseline_metrics[metric_name]
                    
                    if baseline_value != 0:
                        # 对于"越小越好"的指标（CPU、内存、延迟）
                        if metric_name in ["cpu_usage", "memory_usage", "llm_api_latency"]:
                            improvement = (baseline_value - current_value) / baseline_value
                        else:  # 对于"越大越好"的指标（成功率、吞吐量）
                            improvement = (current_value - baseline_value) / baseline_value
                        
                        improvements[f"{metric_name}_improvement"] = improvement
        
        # 计算总体改进分数
        if improvements:
            overall_improvement = statistics.mean(improvements.values())
            improvements["overall_improvement"] = overall_improvement
        
        return improvements
    
    def enable_auto_optimization(self, baseline_collection_time: int = 300):
        """启用自动优化"""
        
        print(f"🚀 启用自动优化，收集基线数据 {baseline_collection_time} 秒...")
        
        # 收集基线指标
        asyncio.create_task(self._collect_baseline_metrics(baseline_collection_time))
        
        self.auto_optimization_enabled = True
    
    async def _collect_baseline_metrics(self, collection_time: int):
        """收集基线指标"""
        
        await asyncio.sleep(collection_time)
        
        # 设置基线指标
        self.baseline_metrics = self.analyzer.real_time_metrics.copy()
        
        print("✅ 基线指标收集完成，自动优化已激活")
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        
        if not self.optimization_history:
            return {"message": "暂无优化历史"}
        
        successful_optimizations = [opt for opt in self.optimization_history if opt["success"]]
        
        report = {
            "total_optimizations": len(self.optimization_history),
            "successful_optimizations": len(successful_optimizations),
            "success_rate": len(successful_optimizations) / len(self.optimization_history),
            "average_improvement": statistics.mean([
                opt["improvement"].get("overall_improvement", 0)
                for opt in successful_optimizations
            ]) if successful_optimizations else 0,
            "recent_optimizations": self.optimization_history[-5:],
            "current_config": self.current_config,
            "auto_optimization_enabled": self.auto_optimization_enabled
        }
        
        return report
```

## 4. 可观测性最佳实践

### 4.1 分布式链路追踪

#### 4.1.1 CrewAI 任务链路追踪

```python
import uuid
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

class CrewAITracer:
    """CrewAI专用链路追踪器"""
    
    def __init__(self, service_name: str = "crewai-service", jaeger_endpoint: str = "http://localhost:14268/api/traces"):
        self.service_name = service_name
        
        # 设置追踪提供者
        trace.set_tracer_provider(TracerProvider())
        
        # 配置Jaeger导出器
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
            collector_endpoint=jaeger_endpoint,
        )
        
        # 添加span处理器
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        # 获取追踪器
        self.tracer = trace.get_tracer(service_name)
        
        # 自动化HTTP请求追踪
        RequestsInstrumentor().instrument()
        
        # 存储活跃span
        self.active_spans: Dict[str, Any] = {}
    
    def start_crew_execution(self, crew_id: str, inputs: Dict[str, Any]) -> str:
        """开始Crew执行追踪"""
        
        span = self.tracer.start_span(
            f"crew_execution",
            attributes={
                "crew.id": crew_id,
                "crew.input_size": len(str(inputs)),
                "crew.agents_count": inputs.get("agents_count", 0),
                "crew.tasks_count": inputs.get("tasks_count", 0)
            }
        )
        
        trace_id = str(uuid.uuid4())
        self.active_spans[trace_id] = span
        
        return trace_id
    
    def start_agent_execution(self, trace_id: str, agent_id: str, task_description: str) -> str:
        """开始Agent执行追踪"""
        
        parent_span = self.active_spans.get(trace_id)
        
        with self.tracer.start_as_current_span(
            f"agent_execution",
            context=trace.set_span_in_context(parent_span) if parent_span else None,
            attributes={
                "agent.id": agent_id,
                "agent.task_length": len(task_description),
                "agent.task_hash": hash(task_description)
            }
        ) as span:
            
            agent_trace_id = f"{trace_id}_agent_{agent_id}"
            self.active_spans[agent_trace_id] = span
            
            return agent_trace_id
    
    def track_llm_call(self, trace_id: str, model: str, prompt_tokens: int, 
                      completion_tokens: int, latency: float):
        """追踪LLM调用"""
        
        parent_span = self.active_spans.get(trace_id)
        
        with self.tracer.start_as_current_span(
            f"llm_api_call",
            context=trace.set_span_in_context(parent_span) if parent_span else None,
            attributes={
                "llm.model": model,
                "llm.prompt_tokens": prompt_tokens,
                "llm.completion_tokens": completion_tokens,
                "llm.total_tokens": prompt_tokens + completion_tokens,
                "llm.latency_ms": latency * 1000
            }
        ):
            pass  # Span会自动完成
    
    def track_tool_execution(self, trace_id: str, tool_name: str, 
                           execution_time: float, success: bool, error_message: str = None):
        """追踪工具执行"""
        
        parent_span = self.active_spans.get(trace_id)
        
        with self.tracer.start_as_current_span(
            f"tool_execution",
            context=trace.set_span_in_context(parent_span) if parent_span else None,
            attributes={
                "tool.name": tool_name,
                "tool.execution_time_ms": execution_time * 1000,
                "tool.success": success,
                "tool.error_message": error_message or ""
            }
        ):
            pass
    
    def end_execution_trace(self, trace_id: str, success: bool = True, 
                          result_summary: str = "", error_message: str = ""):
        """结束执行追踪"""
        
        if trace_id in self.active_spans:
            span = self.active_spans[trace_id]
            
            # 添加结果信息
            span.set_attributes({
                "execution.success": success,
                "execution.result_length": len(result_summary),
                "execution.error_message": error_message
            })
            
            # 设置状态
            if not success:
                span.set_status(trace.Status(trace.StatusCode.ERROR, error_message))
            else:
                span.set_status(trace.Status(trace.StatusCode.OK))
            
            # 结束span
            span.end()
            
            # 清理
            del self.active_spans[trace_id]
    
    def get_trace_context(self, trace_id: str) -> Dict[str, str]:
        """获取追踪上下文用于传播"""
        
        if trace_id in self.active_spans:
            span = self.active_spans[trace_id]
            span_context = span.get_span_context()
            
            return {
                "trace_id": format(span_context.trace_id, '032x'),
                "span_id": format(span_context.span_id, '016x'),
                "trace_flags": f"{span_context.trace_flags:02x}"
            }
        
        return {}

# 使用示例
tracer = CrewAITracer()

def instrumented_crew_execution(crew, inputs):
    """带追踪的Crew执行"""
    
    # 开始追踪
    trace_id = tracer.start_crew_execution(
        crew_id=getattr(crew, 'id', 'unknown'),
        inputs=inputs
    )
    
    try:
        # 执行Crew
        result = crew.kickoff(inputs)
        
        # 成功结束追踪
        tracer.end_execution_trace(
            trace_id=trace_id,
            success=True,
            result_summary=str(result)[:500]  # 截取前500字符
        )
        
        return result
        
    except Exception as e:
        # 错误结束追踪
        tracer.end_execution_trace(
            trace_id=trace_id,
            success=False,
            error_message=str(e)
        )
        raise
```

### 4.2 结构化日志系统

#### 4.2.1 企业级日志架构

```python
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import threading
from contextlib import contextmanager

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, service_name: str, log_level: str = "INFO"):
        self.service_name = service_name
        self.session_context: Dict[str, Any] = {}
        self.context_lock = threading.RLock()
        
        # 配置结构化日志格式
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 创建结构化处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = StructuredFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    @contextmanager
    def context(self, **context_data):
        """日志上下文管理器"""
        
        with self.context_lock:
            # 保存当前上下文
            previous_context = self.session_context.copy()
            
            # 更新上下文
            self.session_context.update(context_data)
            
            try:
                yield
            finally:
                # 恢复上下文
                self.session_context = previous_context
    
    def _create_log_record(self, level: str, message: str, **extra_data) -> Dict[str, Any]:
        """创建结构化日志记录"""
        
        with self.context_lock:
            record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "service": self.service_name,
                "level": level,
                "message": message,
                "thread": threading.current_thread().name,
                "context": self.session_context.copy()
            }
            
            # 添加额外数据
            if extra_data:
                record["data"] = extra_data
            
            return record
    
    def info(self, message: str, **extra_data):
        """记录信息日志"""
        record = self._create_log_record("INFO", message, **extra_data)
        self.logger.info(json.dumps(record, ensure_ascii=False))
    
    def warning(self, message: str, **extra_data):
        """记录警告日志"""
        record = self._create_log_record("WARNING", message, **extra_data)
        self.logger.warning(json.dumps(record, ensure_ascii=False))
    
    def error(self, message: str, **extra_data):
        """记录错误日志"""
        record = self._create_log_record("ERROR", message, **extra_data)
        self.logger.error(json.dumps(record, ensure_ascii=False))
    
    def debug(self, message: str, **extra_data):
        """记录调试日志"""
        record = self._create_log_record("DEBUG", message, **extra_data)
        self.logger.debug(json.dumps(record, ensure_ascii=False))

class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record):
        # 直接返回消息，因为我们已经在消息中包含了JSON
        return record.getMessage()

class CrewAILogger:
    """CrewAI专用日志记录器"""
    
    def __init__(self):
        self.structured_logger = StructuredLogger("crewai")
        self.performance_logger = StructuredLogger("crewai-performance")
        self.audit_logger = StructuredLogger("crewai-audit")
        self.security_logger = StructuredLogger("crewai-security")
    
    def log_crew_start(self, crew_id: str, agents: List[str], tasks: List[str], inputs: Dict[str, Any]):
        """记录Crew开始执行"""
        
        with self.structured_logger.context(crew_id=crew_id):
            self.structured_logger.info(
                "Crew execution started",
                agents=agents,
                tasks=tasks,
                input_keys=list(inputs.keys()),
                agent_count=len(agents),
                task_count=len(tasks)
            )
    
    def log_agent_action(self, agent_id: str, action_type: str, details: Dict[str, Any]):
        """记录Agent动作"""
        
        with self.structured_logger.context(agent_id=agent_id):
            self.structured_logger.info(
                f"Agent {action_type}",
                action_type=action_type,
                **details
            )
    
    def log_performance_metric(self, metric_name: str, value: float, 
                             category: str = "general", **context):
        """记录性能指标"""
        
        self.performance_logger.info(
            f"Performance metric: {metric_name}",
            metric_name=metric_name,
            value=value,
            category=category,
            **context
        )
    
    def log_security_event(self, event_type: str, severity: str, 
                          details: Dict[str, Any], user_id: str = None):
        """记录安全事件"""
        
        with self.security_logger.context(user_id=user_id, event_type=event_type):
            self.security_logger.info(
                f"Security event: {event_type}",
                severity=severity,
                **details
            )
    
    def log_audit_trail(self, action: str, resource: str, user_id: str = None, 
                       success: bool = True, **metadata):
        """记录审计轨迹"""
        
        with self.audit_logger.context(user_id=user_id):
            self.audit_logger.info(
                f"Audit: {action} on {resource}",
                action=action,
                resource=resource,
                success=success,
                **metadata
            )
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any]):
        """带上下文记录错误"""
        
        self.structured_logger.error(
            f"Error occurred: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            traceback=str(error.__traceback__) if error.__traceback__ else None
        )

# 全局日志实例
crewai_logger = CrewAILogger()

# 使用示例装饰器
def log_execution(log_category: str = "general"):
    """执行日志装饰器"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            with crewai_logger.structured_logger.context(
                function=func.__name__,
                category=log_category
            ):
                crewai_logger.structured_logger.info(
                    f"Function execution started: {func.__name__}",
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    crewai_logger.structured_logger.info(
                        f"Function execution completed: {func.__name__}",
                        execution_time=execution_time,
                        success=True
                    )
                    
                    # 记录性能指标
                    crewai_logger.log_performance_metric(
                        metric_name=f"{func.__name__}_execution_time",
                        value=execution_time,
                        category=log_category
                    )
                    
                    return result
                    
                except Exception as e:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    crewai_logger.log_error_with_context(
                        error=e,
                        context={
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "category": log_category
                        }
                    )
                    raise
        
        return wrapper
    return decorator
```

## 4.3 基于CrewAI Task实现的深度任务监控

### 4.3.1 Task生命周期深度分析

基于对CrewAI Task源码的深入分析，我们可以构建更精确的任务性能监控系统，充分利用Task的内置特性：

```python
from crewai import Task
from crewai.tasks.task_output import TaskOutput
from crewai.utilities.events import TaskStartedEvent, TaskCompletedEvent, TaskFailedEvent
from crewai.utilities.events.crewai_event_bus import crewai_event_bus
from datetime import datetime, timedelta
import threading
import psutil
import time
import hashlib
from typing import Dict, Any, Optional, List, Set
from concurrent.futures import Future

class TaskPerformanceMonitor:
    """基于CrewAI Task实现的高精度任务性能监控器"""
    
    def __init__(self):
        self.task_metrics: Dict[str, Dict] = {}  # 按task.key索引
        self.active_tasks: Dict[str, Dict] = {}  # 正在执行的任务
        self.completed_tasks: List[Dict] = []    # 已完成任务历史
        
        # 增强的性能阈值配置
        self.performance_thresholds = {
            'execution_time': 30.0,        # 秒
            'memory_usage': 512,           # MB
            'tool_errors': 3,              # 最大工具错误数
            'retry_limit': 3,              # 最大重试次数
            'guardrail_failures': 2,       # 最大守护失败数
            'delegation_limit': 5,         # 最大委托次数
            'context_overflow_threshold': 0.9,  # 上下文溢出阈值
        }
        
        # 注册CrewAI事件监听器
        self._register_event_listeners()
        
        # 启动后台监控线程
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._background_monitoring,
            daemon=True
        )
        self.monitor_thread.start()
    
    def _register_event_listeners(self):
        """注册CrewAI事件监听器"""
        
        # 监听任务开始事件
        crewai_event_bus.subscribe(
            TaskStartedEvent,
            self._on_task_started
        )
        
        # 监听任务完成事件
        crewai_event_bus.subscribe(
            TaskCompletedEvent,
            self._on_task_completed
        )
        
        # 监听任务失败事件
        crewai_event_bus.subscribe(
            TaskFailedEvent,
            self._on_task_failed
        )
    
    def _on_task_started(self, event: TaskStartedEvent):
        """处理任务开始事件"""
        
        task = event.task
        task_key = task.key  # 使用MD5哈希键作为唯一标识
        
        metrics = {
            'task_id': str(task.id),
            'task_key': task_key,
            'task_name': task.name or f"Task-{str(task.id)[:8]}",
            'agent_role': task.agent.role if task.agent else "unknown",
            'start_time': task.start_time or datetime.now(),
            'description_hash': hashlib.md5(task.description.encode()).hexdigest()[:8],
            
            # 任务配置信息
            'tools_count': len(task.tools) if task.tools else 0,
            'async_execution': task.async_execution,
            'has_context': task.context is not None and task.context != [],
            'context_tasks_count': len(task.context) if isinstance(task.context, list) else 0,
            'has_guardrail': task._guardrail is not None,
            'max_retries': task.max_retries,
            'human_input_required': task.human_input,
            'markdown_output': task.markdown,
            'has_output_file': task.output_file is not None,
            
            # 输出格式配置
            'output_format': {
                'json': task.output_json is not None,
                'pydantic': task.output_pydantic is not None,
                'file': task.output_file is not None,
                'create_directory': task.create_directory
            },
            
            # 实时状态追踪
            'current_retries': task.retry_count,
            'tools_used': task.used_tools,
            'tools_errors': task.tools_errors,
            'delegations': task.delegations,
            'processed_by_agents': list(task.processed_by_agents),
            
            # 系统指标
            'memory_before': self._get_memory_usage(),
            'cpu_before': psutil.cpu_percent(),
            'thread_id': threading.current_thread().ident,
            'process_id': psutil.Process().pid
        }
        
        # 存储到活跃任务追踪
        self.active_tasks[task_key] = metrics
        
        print(f"📊 Task started monitoring: {metrics['task_name']} [{task_key[:8]}]")
    
    def _on_task_completed(self, event: TaskCompletedEvent):
        """处理任务完成事件"""
        
        task = event.task
        task_output = event.output
        task_key = task.key
        
        if task_key in self.active_tasks:
            metrics = self.active_tasks[task_key]
            
            # 更新完成指标
            end_time = task.end_time or datetime.now()
            execution_duration = task.execution_duration or (
                end_time - metrics['start_time']
            ).total_seconds()
            
            metrics.update({
                'end_time': end_time,
                'execution_duration': execution_duration,
                'success': True,
                'error_message': None,
                
                # 任务输出信息
                'output_size': len(str(task_output.raw)) if task_output else 0,
                'output_format_actual': task_output.output_format.value if task_output else 'none',
                'has_pydantic_output': task_output.pydantic is not None if task_output else False,
                'has_json_output': task_output.json_dict is not None if task_output else False,
                
                # 最终状态统计
                'final_retries': task.retry_count,
                'final_tools_used': task.used_tools,
                'final_tools_errors': task.tools_errors,
                'final_delegations': task.delegations,
                'final_processed_agents': list(task.processed_by_agents),
                
                # 系统指标差异
                'memory_after': self._get_memory_usage(),
                'cpu_after': psutil.cpu_percent(),
                'memory_delta': self._get_memory_usage() - metrics['memory_before'],
                'cpu_delta': psutil.cpu_percent() - metrics['cpu_before']
            })
            
            # 性能分析
            metrics['performance_analysis'] = self._analyze_task_performance(metrics)
            
            # 移动到完成列表
            self.completed_tasks.append(metrics)
            del self.active_tasks[task_key]
            
            # 维护历史记录大小
            if len(self.completed_tasks) > 10000:
                self.completed_tasks = self.completed_tasks[-10000:]
            
            print(f"✅ Task completed: {metrics['task_name']} in {execution_duration:.2f}s")
    
    def _background_monitoring(self):
        """后台监控循环"""
        
        while self.monitoring_active:
            try:
                # 检查长时间运行的任务
                current_time = datetime.now()
                for task_key, metrics in list(self.active_tasks.items()):
                    elapsed = (current_time - metrics['start_time']).total_seconds()
                    
                    # 长时间运行警告
                    if elapsed > self.performance_thresholds['execution_time'] * 2:
                        print(f"⚠️ 长时间运行任务: {metrics['task_name']} ({elapsed:.1f}s)")
                    
                    # 更新实时指标
                    metrics['elapsed_time'] = elapsed
                    metrics['current_memory'] = self._get_memory_usage()
                
                # 检查系统资源
                self._check_system_resources()
                
                time.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                print(f"Background monitoring error: {e}")
                time.sleep(30)
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用情况（MB）"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能报告"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_tasks = [
            task for task in self.completed_tasks 
            if task['start_time'] >= cutoff_time
        ]
        
        if not recent_tasks:
            return {'message': f'过去{hours}小时无完成任务'}
        
        # 基础统计
        total_tasks = len(recent_tasks)
        successful_tasks = [t for t in recent_tasks if t['success']]
        failed_tasks = [t for t in recent_tasks if not t['success']]
        
        success_rate = len(successful_tasks) / total_tasks if total_tasks > 0 else 0
        
        # 性能统计
        execution_times = [t['execution_duration'] for t in recent_tasks]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # 工具和错误统计
        total_tool_errors = sum(t.get('final_tools_errors', 0) for t in recent_tasks)
        total_retries = sum(t.get('final_retries', 0) for t in recent_tasks)
        
        return {
            'period': f'{hours}小时',
            'total_tasks': total_tasks,
            'success_rate': success_rate,
            'failed_tasks': len(failed_tasks),
            
            'performance_metrics': {
                'avg_execution_time': avg_execution_time,
                'min_execution_time': min(execution_times) if execution_times else 0,
                'max_execution_time': max(execution_times) if execution_times else 0,
                'total_tool_errors': total_tool_errors,
                'total_retries': total_retries,
            },
            
            'recent_failures': [
                {
                    'task_name': t['task_name'],
                    'error_message': t['error_message'],
                    'duration': t['execution_duration']
                }
                for t in failed_tasks[-5:]  # 最近5个失败任务
            ]
        }

    def shutdown(self):
        """关闭监控器"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        print("📊 Task performance monitor shut down")
```

### 4.3.2 Task守护规则性能影响分析

基于Task.py中的守护规则实现，监控守护规则对性能的影响：

```python
class GuardrailPerformanceAnalyzer:
    """守护规则性能分析器"""
    
    def __init__(self):
        self.guardrail_metrics = {}
        self.validation_history = []
    
    def track_guardrail_validation(self, task: Any, validation_time: float, 
                                  retry_count: int, success: bool):
        """跟踪守护规则验证性能"""
        
        guardrail_type = "callable" if callable(task.guardrail) else "llm_based"
        task_key = getattr(task, 'key', str(id(task)))
        
        metrics = {
            'timestamp': datetime.now(),
            'task_key': task_key,
            'guardrail_type': guardrail_type,
            'validation_time': validation_time,
            'retry_count': retry_count,
            'success': success,
            'max_retries': task.max_retries,
            'exhausted_retries': retry_count >= task.max_retries
        }
        
        self.validation_history.append(metrics)
        
        # 维护历史大小
        if len(self.validation_history) > 1000:
            self.validation_history = self.validation_history[-1000:]
    
    def get_guardrail_performance_report(self) -> Dict[str, Any]:
        """生成守护规则性能报告"""
        
        if not self.validation_history:
            return {'message': '无守护规则验证历史'}
        
        # 按类型分组统计
        callable_validations = [v for v in self.validation_history if v['guardrail_type'] == 'callable']
        llm_validations = [v for v in self.validation_history if v['guardrail_type'] == 'llm_based']
        
        report = {
            'total_validations': len(self.validation_history),
            'callable_guardrails': {
                'count': len(callable_validations),
                'avg_time': sum(v['validation_time'] for v in callable_validations) / len(callable_validations) if callable_validations else 0,
                'success_rate': sum(v['success'] for v in callable_validations) / len(callable_validations) if callable_validations else 0
            },
            'llm_guardrails': {
                'count': len(llm_validations),
                'avg_time': sum(v['validation_time'] for v in llm_validations) / len(llm_validations) if llm_validations else 0,
                'success_rate': sum(v['success'] for v in llm_validations) / len(llm_validations) if llm_validations else 0
            },
            'retry_analysis': {
                'avg_retries': sum(v['retry_count'] for v in self.validation_history) / len(self.validation_history),
                'exhausted_retries_rate': sum(v['exhausted_retries'] for v in self.validation_history) / len(self.validation_history)
            }
        }
        
        return report
```

## 5. 生产环境监控系统

### 5.1 告警和通知系统

#### 5.1.1 多渠道告警管理

```python
import smtplib
import requests
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertChannel(ABC):
    """告警通道抽象基类"""
    
    @abstractmethod
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        pass

class EmailAlertChannel(AlertChannel):
    """邮件告警通道"""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """发送邮件告警"""
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ", ".join(alert['recipients'])
            msg['Subject'] = f"[{alert['severity'].upper()}] CrewAI Alert: {alert['title']}"
            
            # 构建邮件内容
            body = self._build_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # 发送邮件
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            
            text = msg.as_string()
            server.sendmail(self.username, alert['recipients'], text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False
    
    def _build_email_body(self, alert: Dict[str, Any]) -> str:
        """构建邮件内容"""
        
        severity_colors = {
            "low": "#28a745",
            "medium": "#ffc107", 
            "high": "#fd7e14",
            "critical": "#dc3545"
        }
        
        color = severity_colors.get(alert['severity'], "#6c757d")
        
        body = f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">CrewAI 系统告警</h2>
                    <p style="margin: 5px 0 0 0;">严重程度: {alert['severity'].upper()}</p>
                </div>
                
                <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
                    <h3>{alert['title']}</h3>
                    <p><strong>时间:</strong> {alert['timestamp']}</p>
                    <p><strong>描述:</strong> {alert['message']}</p>
                    
                    {self._format_metrics_table(alert.get('metrics', {}))}
                    
                    {self._format_recommendations(alert.get('recommendations', []))}
                </div>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def _format_metrics_table(self, metrics: Dict[str, Any]) -> str:
        """格式化指标表格"""
        
        if not metrics:
            return ""
        
        rows = ""
        for key, value in metrics.items():
            rows += f"<tr><td>{key}</td><td>{value}</td></tr>"
        
        return f"""
        <h4>相关指标:</h4>
        <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
            <thead>
                <tr style="background-color: #f8f9fa;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">指标</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">值</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
    
    def _format_recommendations(self, recommendations: List[str]) -> str:
        """格式化建议列表"""
        
        if not recommendations:
            return ""
        
        items = "".join([f"<li>{rec}</li>" for rec in recommendations])
        
        return f"""
        <h4>建议操作:</h4>
        <ul style="margin: 10px 0; padding-left: 20px;">
            {items}
        </ul>
        """

class SlackAlertChannel(AlertChannel):
    """Slack告警通道"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """发送Slack告警"""
        
        try:
            # 构建Slack消息
            payload = self._build_slack_payload(alert)
            
            # 发送到Slack
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return False
    
    def _build_slack_payload(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """构建Slack消息载荷"""
        
        severity_colors = {
            "low": "good",
            "medium": "warning",
            "high": "warning", 
            "critical": "danger"
        }
        
        color = severity_colors.get(alert['severity'], "good")
        
        fields = []
        
        # 添加指标字段
        for key, value in alert.get('metrics', {}).items():
            fields.append({
                "title": key,
                "value": str(value),
                "short": True
            })
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"[{alert['severity'].upper()}] {alert['title']}",
                "text": alert['message'],
                "fields": fields,
                "footer": "CrewAI Monitoring",
                "ts": int(alert['timestamp'].timestamp()) if hasattr(alert['timestamp'], 'timestamp') else None
            }]
        }
        
        return payload

class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.channels: List[AlertChannel] = []
        self.alert_rules: Dict[str, Dict] = {}
        self.alert_history: List[Dict] = []
        self.suppression_rules: Dict[str, Dict] = {}
        
        # 默认收件人配置
        self.default_recipients = {
            "low": ["monitoring@company.com"],
            "medium": ["devops@company.com", "monitoring@company.com"],
            "high": ["devops@company.com", "management@company.com"],
            "critical": ["devops@company.com", "management@company.com", "cto@company.com"]
        }
    
    def add_channel(self, channel: AlertChannel):
        """添加告警通道"""
        self.channels.append(channel)
    
    def add_alert_rule(self, rule_name: str, condition: callable, 
                      severity: AlertSeverity, title: str, message: str,
                      recommendations: List[str] = None):
        """添加告警规则"""
        
        self.alert_rules[rule_name] = {
            "condition": condition,
            "severity": severity,
            "title": title, 
            "message": message,
            "recommendations": recommendations or [],
            "last_triggered": None,
            "trigger_count": 0
        }
    
    async def evaluate_alerts(self, metrics: PerformanceMetrics):
        """评估告警条件"""
        
        for rule_name, rule_config in self.alert_rules.items():
            try:
                if rule_config["condition"](metrics):
                    await self._trigger_alert(rule_name, rule_config, metrics)
                    
            except Exception as e:
                print(f"Error evaluating alert rule {rule_name}: {e}")
    
    async def _trigger_alert(self, rule_name: str, rule_config: Dict, metrics: PerformanceMetrics):
        """触发告警"""
        
        # 检查是否被抑制
        if self._is_suppressed(rule_name):
            return
        
        # 更新规则统计
        rule_config["last_triggered"] = datetime.now()
        rule_config["trigger_count"] += 1
        
        # 构建告警消息
        alert = {
            "id": str(uuid.uuid4()),
            "rule_name": rule_name,
            "severity": rule_config["severity"].value,
            "title": rule_config["title"],
            "message": rule_config["message"],
            "timestamp": datetime.now(),
            "metrics": {
                "cpu_usage": f"{metrics.cpu_usage:.1f}%",
                "memory_usage": f"{metrics.memory_usage:.1f}%", 
                "llm_api_latency": f"{metrics.llm_api_latency:.2f}s",
                "success_rate": f"{metrics.success_rate:.2%}",
                "crew_throughput": f"{metrics.crew_throughput} tasks/min"
            },
            "recommendations": rule_config["recommendations"],
            "recipients": self.default_recipients.get(rule_config["severity"].value, [])
        }
        
        # 发送到所有通道
        success_count = 0
        for channel in self.channels:
            try:
                if await channel.send_alert(alert):
                    success_count += 1
            except Exception as e:
                print(f"Failed to send alert via channel: {e}")
        
        # 记录告警历史
        alert["channels_notified"] = success_count
        alert["total_channels"] = len(self.channels)
        self.alert_history.append(alert)
        
        # 清理历史记录
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        print(f"🚨 Alert triggered: {alert['title']} (sent to {success_count}/{len(self.channels)} channels)")
    
    def _is_suppressed(self, rule_name: str) -> bool:
        """检查告警是否被抑制"""
        
        if rule_name in self.suppression_rules:
            suppression = self.suppression_rules[rule_name]
            
            # 检查抑制时间窗口
            if "until" in suppression and datetime.now() < suppression["until"]:
                return True
            
            # 检查抑制条件
            if "condition" in suppression and suppression["condition"]():
                return True
        
        return False
    
    def suppress_alert(self, rule_name: str, duration_minutes: int = 60, reason: str = ""):
        """临时抑制告警"""
        
        self.suppression_rules[rule_name] = {
            "until": datetime.now() + timedelta(minutes=duration_minutes),
            "reason": reason,
            "suppressed_at": datetime.now()
        }
        
        print(f"🔇 Alert {rule_name} suppressed for {duration_minutes} minutes: {reason}")
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        
        recent_alerts = [
            alert for alert in self.alert_history
            if alert['timestamp'] > datetime.now() - timedelta(hours=24)
        ]
        
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for alert in recent_alerts:
            severity_counts[alert['severity']] += 1
        
        return {
            "total_rules": len(self.alert_rules),
            "active_suppressions": len(self.suppression_rules),
            "recent_alerts_24h": len(recent_alerts),
            "severity_breakdown": severity_counts,
            "most_triggered_rules": sorted(
                [(name, config["trigger_count"]) for name, config in self.alert_rules.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "recent_alerts": recent_alerts[-10:]
        }

# 使用示例
def setup_production_monitoring():
    """设置生产环境监控"""
    
    # 创建告警管理器
    alert_manager = AlertManager()
    
    # 添加告警通道
    email_channel = EmailAlertChannel(
        smtp_host="smtp.company.com",
        smtp_port=587,
        username="monitoring@company.com",
        password="password"
    )
    
    slack_channel = SlackAlertChannel(
        webhook_url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    )
    
    alert_manager.add_channel(email_channel)
    alert_manager.add_channel(slack_channel)
    
    # 添加告警规则
    alert_manager.add_alert_rule(
        "high_cpu_usage",
        condition=lambda m: m.cpu_usage > 80,
        severity=AlertSeverity.HIGH,
        title="CPU使用率过高",
        message="系统CPU使用率超过80%，可能影响性能",
        recommendations=[
            "检查当前运行的任务数量",
            "考虑降低并发度", 
            "监控进程资源使用情况"
        ]
    )
    
    alert_manager.add_alert_rule(
        "low_success_rate",
        condition=lambda m: m.success_rate < 0.9,
        severity=AlertSeverity.CRITICAL,
        title="任务成功率过低",
        message="任务执行成功率低于90%，需要立即关注",
        recommendations=[
            "检查错误日志",
            "验证外部服务状态",
            "检查任务配置是否正确"
        ]
    )
    
    return alert_manager
```

## 结论

CrewAI 的性能与监控体系是确保生产环境稳定运行的关键基础设施。通过本文档提供的深度分析和实践指导，开发者可以：

### 核心能力建设

1. **全方位性能监控**
   - 四层性能分析架构（应用层、框架层、系统层、外部服务层）
   - 实时指标收集和历史趋势分析
   - 智能瓶颈检测和自动优化

2. **企业级可观测性**  
   - 分布式链路追踪系统
   - 结构化日志管理
   - 多维度 KPI 跟踪体系

3. **智能运维能力**
   - 自动化性能优化引擎
   - 多渠道告警通知系统
   - 预测性故障预防

### 生产环境最佳实践

1. **监控策略**: 采用分层监控模式，从业务指标到系统资源的全栈覆盖
2. **告警设计**: 基于 SLI/SLO 的智能告警，减少误报提高响应效率
3. **性能优化**: 数据驱动的持续优化，建立性能基线和改进闭环
4. **故障处理**: 完整的事件响应流程，快速定位和恢复能力

### 持续改进建议

1. **指标演进**: 根据业务发展持续完善监控指标体系
2. **自动化提升**: 逐步提高监控、告警、恢复的自动化水平  
3. **成本优化**: 建立性能与成本的平衡机制，实现最佳性价比
4. **团队能力**: 培养团队的可观测性思维和故障处理能力

通过系统性地实施本文档提供的性能监控方案，可以为 CrewAI 应用构建起企业级的可观测性基础设施，确保系统在复杂生产环境中的稳定高效运行。