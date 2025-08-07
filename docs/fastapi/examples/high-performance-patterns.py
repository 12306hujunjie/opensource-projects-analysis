"""
FastAPI High-Performance Optimization Patterns
Ultra-Deep Performance Implementation Examples

This module demonstrates advanced performance optimization techniques including:
- Async-first architecture with optimal coroutine management
- Multi-level caching strategies with intelligent invalidation
- Request/response optimization with zero-copy techniques  
- Background task processing with error recovery and batching
- Database query optimization with connection pooling
- Memory management patterns with object pooling
- CPU-intensive workload optimization with thread pools
- JSON serialization optimization with orjson integration
- Response streaming for large datasets
- Performance monitoring and profiling integration
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable, Union
from uuid import UUID, uuid4
import weakref

import orjson
from fastapi import FastAPI, Request, Response, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

# ===============================================================================
# Advanced Object Pooling for Memory Optimization
# ===============================================================================

class ObjectPool:
    """High-performance object pool with automatic sizing and cleanup"""
    
    def __init__(self, factory: Callable, max_size: int = 1000, cleanup_interval: int = 300):
        self.factory = factory
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self._pool = deque(maxlen=max_size)
        self._created_count = 0
        self._reused_count = 0
        self._last_cleanup = time.time()
        self._active_objects = weakref.WeakSet()
    
    def acquire(self) -> Any:
        """Acquire object from pool or create new one"""
        # Periodic cleanup
        if time.time() - self._last_cleanup > self.cleanup_interval:
            self._cleanup_expired_objects()
        
        if self._pool:
            obj = self._pool.popleft()
            self._reset_object(obj)
            self._reused_count += 1
        else:
            obj = self.factory()
            self._created_count += 1
        
        self._active_objects.add(obj)
        return obj
    
    def release(self, obj: Any) -> None:
        """Return object to pool"""
        if len(self._pool) < self.max_size and obj in self._active_objects:
            self._pool.append(obj)
    
    def _reset_object(self, obj: Any) -> None:
        """Reset object to clean state"""
        if hasattr(obj, 'reset'):
            obj.reset()
        elif hasattr(obj, 'clear'):
            obj.clear()
    
    def _cleanup_expired_objects(self) -> None:
        """Remove expired objects from pool"""
        self._last_cleanup = time.time()
        # Remove objects that haven't been used recently
        current_pool_size = len(self._pool)
        if current_pool_size > self.max_size // 2:
            # Remove half of the objects to prevent memory bloat
            for _ in range(current_pool_size // 2):
                if self._pool:
                    self._pool.popleft()
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool performance statistics"""
        return {
            "pool_size": len(self._pool),
            "active_objects": len(self._active_objects),
            "created_count": self._created_count,
            "reused_count": self._reused_count,
            "reuse_ratio": self._reused_count / max(self._created_count, 1)
        }

# Response object pool for high-traffic endpoints
class PooledResponse:
    """Pooled response object to reduce allocation overhead"""
    def __init__(self):
        self.data = {}
        self.status_code = 200
        self.headers = {}
    
    def reset(self):
        self.data.clear()
        self.status_code = 200
        self.headers.clear()

response_pool = ObjectPool(factory=PooledResponse, max_size=2000)

# ===============================================================================
# Advanced Caching with Intelligent Invalidation
# ===============================================================================

class MultiLevelCache:
    """High-performance multi-level caching system"""
    
    def __init__(self, 
                 l1_size: int = 10000,
                 l2_size: int = 50000, 
                 default_ttl: int = 300):
        self.l1_size = l1_size
        self.l2_size = l2_size
        self.default_ttl = default_ttl
        
        # L1 Cache: Hot data (LRU with timestamps)
        self.l1_cache: Dict[str, Dict[str, Any]] = {}
        self.l1_access_times: Dict[str, float] = {}
        
        # L2 Cache: Warm data (LRU)
        self.l2_cache: Dict[str, Dict[str, Any]] = {}
        self.l2_access_times: Dict[str, float] = {}
        
        # Cache statistics
        self.stats = {
            "l1_hits": 0, "l1_misses": 0,
            "l2_hits": 0, "l2_misses": 0,
            "evictions": 0, "invalidations": 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with L1 -> L2 fallback"""
        current_time = time.time()
        
        # Try L1 cache first
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if current_time < entry["expires_at"]:
                self.l1_access_times[key] = current_time
                self.stats["l1_hits"] += 1
                return entry["value"]
            else:
                # Expired entry
                del self.l1_cache[key]
                self.l1_access_times.pop(key, None)
        
        # Try L2 cache
        if key in self.l2_cache:
            entry = self.l2_cache[key]
            if current_time < entry["expires_at"]:
                # Promote to L1
                await self._promote_to_l1(key, entry)
                self.stats["l2_hits"] += 1
                return entry["value"]
            else:
                # Expired entry
                del self.l2_cache[key]
                self.l2_access_times.pop(key, None)
        
        self.stats["l1_misses"] += 1
        self.stats["l2_misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with intelligent placement"""
        ttl = ttl or self.default_ttl
        current_time = time.time()
        expires_at = current_time + ttl
        
        entry = {
            "value": value,
            "expires_at": expires_at,
            "created_at": current_time,
            "access_count": 1
        }
        
        # Always start in L1 for new entries
        await self._ensure_l1_space()
        self.l1_cache[key] = entry
        self.l1_access_times[key] = current_time
    
    async def _promote_to_l1(self, key: str, entry: Dict[str, Any]) -> None:
        """Promote L2 entry to L1"""
        await self._ensure_l1_space()
        self.l1_cache[key] = entry
        self.l1_access_times[key] = time.time()
        
        # Remove from L2
        self.l2_cache.pop(key, None)
        self.l2_access_times.pop(key, None)
    
    async def _ensure_l1_space(self) -> None:
        """Ensure L1 cache has space, evict to L2 if needed"""
        if len(self.l1_cache) >= self.l1_size:
            await self._evict_l1_to_l2()
    
    async def _evict_l1_to_l2(self, evict_count: int = None) -> None:
        """Evict LRU entries from L1 to L2"""
        evict_count = evict_count or self.l1_size // 4
        
        # Sort by access time (LRU first)
        sorted_items = sorted(
            self.l1_access_times.items(),
            key=lambda x: x[1]
        )
        
        for key, _ in sorted_items[:evict_count]:
            if key in self.l1_cache:
                entry = self.l1_cache.pop(key)
                self.l1_access_times.pop(key)
                
                # Move to L2 if still valid
                if time.time() < entry["expires_at"]:
                    await self._ensure_l2_space()
                    self.l2_cache[key] = entry
                    self.l2_access_times[key] = time.time()
                
                self.stats["evictions"] += 1
    
    async def _ensure_l2_space(self) -> None:
        """Ensure L2 cache has space"""
        if len(self.l2_cache) >= self.l2_size:
            # Remove oldest L2 entries
            evict_count = self.l2_size // 4
            sorted_items = sorted(
                self.l2_access_times.items(),
                key=lambda x: x[1]
            )
            
            for key, _ in sorted_items[:evict_count]:
                self.l2_cache.pop(key, None)
                self.l2_access_times.pop(key, None)
                self.stats["evictions"] += 1
    
    async def invalidate(self, pattern: str = None, keys: List[str] = None) -> int:
        """Invalidate cache entries by pattern or specific keys"""
        invalidated = 0
        
        if keys:
            for key in keys:
                if key in self.l1_cache:
                    del self.l1_cache[key]
                    self.l1_access_times.pop(key, None)
                    invalidated += 1
                if key in self.l2_cache:
                    del self.l2_cache[key]
                    self.l2_access_times.pop(key, None)
                    invalidated += 1
        
        elif pattern:
            # Pattern-based invalidation
            to_remove = []
            for key in list(self.l1_cache.keys()) + list(self.l2_cache.keys()):
                if pattern in key:
                    to_remove.append(key)
            
            for key in to_remove:
                self.l1_cache.pop(key, None)
                self.l1_access_times.pop(key, None)
                self.l2_cache.pop(key, None)
                self.l2_access_times.pop(key, None)
                invalidated += 1
        
        self.stats["invalidations"] += invalidated
        return invalidated
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        l1_hit_rate = self.stats["l1_hits"] / max(
            self.stats["l1_hits"] + self.stats["l1_misses"], 1
        )
        l2_hit_rate = self.stats["l2_hits"] / max(
            self.stats["l2_hits"] + self.stats["l2_misses"], 1  
        )
        
        return {
            **self.stats,
            "l1_size": len(self.l1_cache),
            "l2_size": len(self.l2_cache),
            "l1_hit_rate": l1_hit_rate,
            "l2_hit_rate": l2_hit_rate,
            "total_hit_rate": (self.stats["l1_hits"] + self.stats["l2_hits"]) / max(
                self.stats["l1_hits"] + self.stats["l1_misses"] + 
                self.stats["l2_hits"] + self.stats["l2_misses"], 1
            )
        }

cache = MultiLevelCache()

# ===============================================================================
# High-Performance JSON Serialization
# ===============================================================================

class OptimizedJSONResponse(JSONResponse):
    """High-performance JSON response using orjson"""
    
    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: str = "application/json",
        use_decimal_serialization: bool = True
    ):
        self.use_decimal_serialization = use_decimal_serialization
        super().__init__(content, status_code, headers, media_type)
    
    def render(self, content: Any) -> bytes:
        """Optimized JSON rendering with orjson"""
        try:
            if self.use_decimal_serialization:
                # Custom serialization for Decimal and other types
                return orjson.dumps(
                    content,
                    default=self._custom_serializer,
                    option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z
                )
            else:
                return orjson.dumps(content)
        except Exception:
            # Fallback to standard JSON
            return json.dumps(content, default=str).encode()
    
    def _custom_serializer(self, obj: Any) -> Any:
        """Custom serializer for non-standard types"""
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

# ===============================================================================
# Advanced Background Task Processing
# ===============================================================================

class HighPerformanceTaskProcessor:
    """Advanced background task processor with batching and error recovery"""
    
    def __init__(self, 
                 batch_size: int = 100,
                 batch_timeout: float = 5.0,
                 max_workers: int = 4):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_workers = max_workers
        
        self.task_queue: deque = deque()
        self.processing_stats = {
            "processed": 0,
            "failed": 0,
            "batches": 0,
            "avg_batch_time": 0.0
        }
        
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._processing_lock = asyncio.Lock()
        self._batch_timer_task: Optional[asyncio.Task] = None
        self._start_batch_timer()
    
    def add_task(self, func: Callable, *args, **kwargs) -> str:
        """Add task to processing queue"""
        task_id = str(uuid4())
        task = {
            "id": task_id,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "created_at": time.time(),
            "retries": 0
        }
        
        self.task_queue.append(task)
        
        # Process immediately if batch is full
        if len(self.task_queue) >= self.batch_size:
            asyncio.create_task(self._process_batch())
        
        return task_id
    
    async def _process_batch(self) -> None:
        """Process a batch of tasks efficiently"""
        if not self.task_queue:
            return
        
        async with self._processing_lock:
            # Extract batch
            batch = []
            for _ in range(min(self.batch_size, len(self.task_queue))):
                if self.task_queue:
                    batch.append(self.task_queue.popleft())
            
            if not batch:
                return
            
            batch_start_time = time.time()
            
            # Group tasks by function for batch optimization
            task_groups = defaultdict(list)
            for task in batch:
                func_key = f"{task['func'].__module__}.{task['func'].__name__}"
                task_groups[func_key].append(task)
            
            # Process each group
            results = []
            for func_key, group_tasks in task_groups.items():
                group_results = await self._process_task_group(group_tasks)
                results.extend(group_results)
            
            # Update statistics
            batch_time = time.time() - batch_start_time
            self.processing_stats["batches"] += 1
            self.processing_stats["processed"] += len([r for r in results if r["success"]])
            self.processing_stats["failed"] += len([r for r in results if not r["success"]])
            
            # Update average batch time
            prev_avg = self.processing_stats["avg_batch_time"]
            batch_count = self.processing_stats["batches"]
            self.processing_stats["avg_batch_time"] = (
                (prev_avg * (batch_count - 1) + batch_time) / batch_count
            )
    
    async def _process_task_group(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a group of similar tasks efficiently"""
        results = []
        
        # Check if tasks can be batched
        if len(tasks) > 1 and hasattr(tasks[0]["func"], "__batch_processable__"):
            # Batch processing
            try:
                batch_args = [task["args"] for task in tasks]
                batch_kwargs = [task["kwargs"] for task in tasks]
                
                batch_results = await self._execute_batch_function(
                    tasks[0]["func"], batch_args, batch_kwargs
                )
                
                for task, result in zip(tasks, batch_results):
                    results.append({
                        "task_id": task["id"],
                        "success": True,
                        "result": result,
                        "execution_time": time.time() - task["created_at"]
                    })
                    
            except Exception as e:
                # Fallback to individual processing
                for task in tasks:
                    result = await self._process_single_task(task)
                    results.append(result)
        else:
            # Individual processing
            for task in tasks:
                result = await self._process_single_task(task)
                results.append(result)
        
        return results
    
    async def _process_single_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual task with error handling"""
        try:
            func = task["func"]
            args = task["args"]
            kwargs = task["kwargs"]
            
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = await run_in_threadpool(func, *args, **kwargs)
            
            return {
                "task_id": task["id"],
                "success": True,
                "result": result,
                "execution_time": time.time() - task["created_at"]
            }
            
        except Exception as e:
            # Retry logic
            if task["retries"] < 3:
                task["retries"] += 1
                self.task_queue.append(task)  # Re-queue for retry
            
            return {
                "task_id": task["id"],
                "success": False,
                "error": str(e),
                "execution_time": time.time() - task["created_at"],
                "retries": task["retries"]
            }
    
    async def _execute_batch_function(
        self, 
        func: Callable, 
        batch_args: List[tuple], 
        batch_kwargs: List[dict]
    ) -> List[Any]:
        """Execute batch function efficiently"""
        if asyncio.iscoroutinefunction(func):
            return await func(batch_args, batch_kwargs)
        else:
            return await run_in_threadpool(func, batch_args, batch_kwargs)
    
    def _start_batch_timer(self):
        """Start batch processing timer"""
        async def batch_timer():
            while True:
                await asyncio.sleep(self.batch_timeout)
                if self.task_queue:
                    await self._process_batch()
        
        self._batch_timer_task = asyncio.create_task(batch_timer())
    
    async def shutdown(self):
        """Shutdown task processor gracefully"""
        # Cancel batch timer
        if self._batch_timer_task:
            self._batch_timer_task.cancel()
        
        # Process remaining tasks
        while self.task_queue:
            await self._process_batch()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task processing statistics"""
        return {
            **self.processing_stats,
            "queue_size": len(self.task_queue),
            "active_workers": len(self.executor._threads) if hasattr(self.executor, '_threads') else 0
        }

task_processor = HighPerformanceTaskProcessor()

# ===============================================================================
# Streaming Response Optimization
# ===============================================================================

class StreamingDataProcessor:
    """High-performance data streaming with chunked processing"""
    
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
        self.compression_enabled = True
    
    async def stream_large_dataset(
        self, 
        data_source: AsyncGenerator[Any, None],
        transform_func: Optional[Callable] = None,
        include_metadata: bool = True
    ) -> AsyncGenerator[bytes, None]:
        """Stream large dataset with optional transformation"""
        
        # Send opening bracket for JSON array
        yield b'["data":['
        
        first_item = True
        chunk_buffer = []
        chunk_size = 0
        
        async for item in data_source:
            # Apply transformation if provided
            if transform_func:
                if asyncio.iscoroutinefunction(transform_func):
                    item = await transform_func(item)
                else:
                    item = transform_func(item)
            
            # Serialize item
            serialized_item = orjson.dumps(item)
            
            # Add comma if not first item
            if not first_item:
                chunk_buffer.append(b',')
            else:
                first_item = False
            
            chunk_buffer.append(serialized_item)
            chunk_size += len(serialized_item)
            
            # Yield chunk when buffer is full
            if chunk_size >= self.chunk_size:
                yield b''.join(chunk_buffer)
                chunk_buffer.clear()
                chunk_size = 0
        
        # Send remaining buffer
        if chunk_buffer:
            yield b''.join(chunk_buffer)
        
        # Send closing bracket and metadata
        if include_metadata:
            metadata = {
                "streamed_at": datetime.utcnow().isoformat(),
                "chunk_size": self.chunk_size
            }
            yield b'],"metadata":' + orjson.dumps(metadata) + b'}'
        else:
            yield b']}'
    
    async def stream_csv_data(
        self, 
        data_source: AsyncGenerator[Dict[str, Any], None],
        headers: List[str]
    ) -> AsyncGenerator[bytes, None]:
        """Stream data as CSV format"""
        
        # Send CSV headers
        yield ','.join(headers).encode() + b'\n'
        
        chunk_buffer = []
        chunk_size = 0
        
        async for row in data_source:
            # Convert row to CSV format
            csv_row = ','.join(str(row.get(header, '')) for header in headers)
            csv_bytes = csv_row.encode() + b'\n'
            
            chunk_buffer.append(csv_bytes)
            chunk_size += len(csv_bytes)
            
            # Yield chunk when buffer is full
            if chunk_size >= self.chunk_size:
                yield b''.join(chunk_buffer)
                chunk_buffer.clear()
                chunk_size = 0
        
        # Send remaining buffer
        if chunk_buffer:
            yield b''.join(chunk_buffer)

streaming_processor = StreamingDataProcessor()

# ===============================================================================
# Performance Monitoring Middleware
# ===============================================================================

class AdvancedPerformanceMiddleware(BaseHTTPMiddleware):
    """Comprehensive performance monitoring with detailed metrics"""
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics = {
            "request_count": 0,
            "total_time": 0.0,
            "db_time": 0.0,
            "cache_time": 0.0,
            "serialization_time": 0.0,
            "slow_requests": [],
            "error_count": 0
        }
        self.percentile_tracker = deque(maxlen=10000)  # Track last 10k requests
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        # Initialize request tracking
        request.state.perf_metrics = {
            "db_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "db_time": 0.0,
            "cache_time": 0.0
        }
        
        try:
            response = await call_next(request)
            
            # Calculate metrics
            total_time = time.perf_counter() - start_time
            
            # Update global metrics
            self.metrics["request_count"] += 1
            self.metrics["total_time"] += total_time
            self.metrics["db_time"] += request.state.perf_metrics["db_time"]
            self.metrics["cache_time"] += request.state.perf_metrics["cache_time"]
            
            # Track percentiles
            self.percentile_tracker.append(total_time)
            
            # Track slow requests
            if total_time > 1.0:  # Requests slower than 1 second
                self.metrics["slow_requests"].append({
                    "path": request.url.path,
                    "method": request.method,
                    "time": total_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "db_queries": request.state.perf_metrics["db_queries"],
                    "cache_hits": request.state.perf_metrics["cache_hits"]
                })
                
                # Keep only recent slow requests
                if len(self.metrics["slow_requests"]) > 100:
                    self.metrics["slow_requests"] = self.metrics["slow_requests"][-100:]
            
            # Add performance headers
            response.headers["X-Process-Time"] = f"{total_time * 1000:.2f}"
            response.headers["X-DB-Queries"] = str(request.state.perf_metrics["db_queries"])
            response.headers["X-Cache-Hits"] = str(request.state.perf_metrics["cache_hits"])
            
            return response
            
        except Exception as e:
            self.metrics["error_count"] += 1
            raise
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.percentile_tracker:
            return {"message": "No requests processed yet"}
        
        sorted_times = sorted(self.percentile_tracker)
        request_count = self.metrics["request_count"]
        
        return {
            "request_count": request_count,
            "avg_response_time": self.metrics["total_time"] / max(request_count, 1),
            "percentiles": {
                "p50": sorted_times[int(0.5 * len(sorted_times))],
                "p90": sorted_times[int(0.9 * len(sorted_times))],
                "p95": sorted_times[int(0.95 * len(sorted_times))],
                "p99": sorted_times[int(0.99 * len(sorted_times))],
            },
            "db_metrics": {
                "total_db_time": self.metrics["db_time"],
                "avg_db_time": self.metrics["db_time"] / max(request_count, 1),
                "db_time_ratio": self.metrics["db_time"] / self.metrics["total_time"]
            },
            "cache_metrics": {
                "total_cache_time": self.metrics["cache_time"],
                "avg_cache_time": self.metrics["cache_time"] / max(request_count, 1)
            },
            "error_rate": self.metrics["error_count"] / max(request_count, 1),
            "slow_requests_count": len(self.metrics["slow_requests"]),
            "recent_slow_requests": self.metrics["slow_requests"][-5:]  # Last 5 slow requests
        }

# ===============================================================================
# High-Performance Utility Functions
# ===============================================================================

@lru_cache(maxsize=10000)
def cached_computation(input_data: str) -> str:
    """CPU-intensive computation with LRU caching"""
    # Simulate complex computation
    result = hash(input_data * 1000)
    return str(result)

async def batch_database_operation(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch database operations for improved performance"""
    # Simulate batch database operation
    await asyncio.sleep(0.1)  # Simulate DB latency
    
    results = []
    for item in items:
        results.append({
            **item,
            "processed_at": datetime.utcnow().isoformat(),
            "batch_size": len(items)
        })
    
    return results

# Mark function as batch processable
batch_database_operation.__batch_processable__ = True

async def optimized_data_aggregation(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """High-performance data aggregation with parallel processing"""
    
    if not data:
        return {}
    
    # Parallel aggregation tasks
    tasks = [
        asyncio.create_task(asyncio.get_event_loop().run_in_executor(
            None, lambda: sum(item.get('value', 0) for item in data)
        )),
        asyncio.create_task(asyncio.get_event_loop().run_in_executor(
            None, lambda: len(set(item.get('category', '') for item in data))
        )),
        asyncio.create_task(asyncio.get_event_loop().run_in_executor(
            None, lambda: max((item.get('timestamp', 0) for item in data), default=0)
        ))
    ]
    
    total_value, unique_categories, latest_timestamp = await asyncio.gather(*tasks)
    
    return {
        "total_value": total_value,
        "unique_categories": unique_categories,
        "latest_timestamp": latest_timestamp,
        "record_count": len(data),
        "aggregated_at": datetime.utcnow().isoformat()
    }

# ===============================================================================
# Example Usage and Performance Tests
# ===============================================================================

async def performance_test_data_generator() -> AsyncGenerator[Dict[str, Any], None]:
    """Generate test data for performance benchmarking"""
    for i in range(10000):
        yield {
            "id": i,
            "name": f"Item {i}",
            "value": i * 1.5,
            "category": f"category_{i % 10}",
            "timestamp": time.time(),
            "metadata": {
                "source": "performance_test",
                "batch_id": i // 100
            }
        }

# Performance-optimized dependency for database operations
async def get_optimized_db_session() -> AsyncSession:
    """Get database session optimized for performance"""
    # Use object pool for session management
    session = response_pool.acquire()
    try:
        yield session
    finally:
        response_pool.release(session)

# Example high-performance endpoints would use these patterns:
#
# @app.get("/performance/stream-data")
# async def stream_performance_data():
#     data_gen = performance_test_data_generator()
#     stream_gen = streaming_processor.stream_large_dataset(
#         data_gen, 
#         transform_func=lambda x: {**x, "processed": True}
#     )
#     return StreamingResponse(stream_gen, media_type="application/json")
#
# @app.post("/performance/batch-process")
# async def batch_process_data(items: List[Dict[str, Any]]):
#     task_id = task_processor.add_task(batch_database_operation, items)
#     return OptimizedJSONResponse({
#         "task_id": task_id,
#         "message": "Batch processing started",
#         "estimated_completion": time.time() + 2
#     })