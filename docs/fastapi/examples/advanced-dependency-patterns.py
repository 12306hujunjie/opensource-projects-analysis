"""
FastAPI Advanced Dependency Injection Patterns
Ultra-Deep Implementation Examples

This module demonstrates sophisticated dependency injection patterns including:
- Hierarchical dependency resolution with complex scoping
- Context-aware dependency provision with conditional logic
- Resource lifecycle management with automatic cleanup
- Dependency caching strategies with intelligent invalidation
- Async dependency composition with parallel resolution
- Security-aware dependency injection with permission scoping
- Dynamic dependency generation with factory patterns
- Cross-cutting concerns integration (logging, monitoring, tracing)
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import wraps, lru_cache
from typing import Any, Dict, List, Optional, Type, Callable, Union, AsyncGenerator
from uuid import UUID, uuid4
from weakref import WeakKeyDictionary

from fastapi import Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

# ===============================================================================
# Advanced Dependency Resolution Engine
# ===============================================================================

class DependencyScope:
    """Advanced dependency scoping with lifecycle management"""
    REQUEST = "request"
    SESSION = "session" 
    APPLICATION = "application"
    TENANT = "tenant"
    USER = "user"

class DependencyContext(BaseModel):
    """Rich context information for dependency resolution"""
    request_id: str
    user_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    session_id: Optional[str] = None
    security_scopes: List[str] = []
    feature_flags: Dict[str, bool] = {}
    metadata: Dict[str, Any] = {}
    created_at: datetime = datetime.utcnow()

class DependencyCache:
    """Intelligent dependency caching with scope-aware storage"""
    
    def __init__(self):
        self._request_cache: WeakKeyDictionary = WeakKeyDictionary()
        self._session_cache: Dict[str, Dict[str, Any]] = {}
        self._application_cache: Dict[str, Any] = {}
        self._tenant_cache: Dict[UUID, Dict[str, Any]] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def get_cache_key(self, func: Callable, context: DependencyContext) -> str:
        """Generate intelligent cache key based on function and context"""
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Include relevant context elements in cache key
        key_parts = [func_name]
        
        if hasattr(func, '__dependency_scope__'):
            scope = func.__dependency_scope__
            if scope == DependencyScope.USER and context.user_id:
                key_parts.append(f"user:{context.user_id}")
            elif scope == DependencyScope.TENANT and context.tenant_id:
                key_parts.append(f"tenant:{context.tenant_id}")
            elif scope == DependencyScope.SESSION and context.session_id:
                key_parts.append(f"session:{context.session_id}")
        
        return ":".join(key_parts)
    
    async def get(self, key: str, scope: str, request: Request = None) -> Optional[Any]:
        """Get cached dependency with scope-aware retrieval"""
        try:
            if scope == DependencyScope.REQUEST and request:
                cache = self._request_cache.get(request, {})
                value = cache.get(key)
            elif scope == DependencyScope.SESSION:
                cache = self._session_cache.get(key.split(":")[0], {})
                value = cache.get(key)
            elif scope == DependencyScope.APPLICATION:
                value = self._application_cache.get(key)
            else:
                return None
            
            if value is not None:
                self._cache_stats["hits"] += 1
                return value
            else:
                self._cache_stats["misses"] += 1
                return None
                
        except Exception as e:
            logging.warning(f"Cache retrieval error for {key}: {e}")
            self._cache_stats["misses"] += 1
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        scope: str, 
        ttl: Optional[int] = None,
        request: Request = None
    ) -> None:
        """Set cached dependency with scope-aware storage"""
        try:
            if scope == DependencyScope.REQUEST and request:
                if request not in self._request_cache:
                    self._request_cache[request] = {}
                self._request_cache[request][key] = {
                    "value": value,
                    "expires_at": time.time() + ttl if ttl else None,
                    "created_at": time.time()
                }
            elif scope == DependencyScope.SESSION:
                session_key = key.split(":")[0]
                if session_key not in self._session_cache:
                    self._session_cache[session_key] = {}
                self._session_cache[session_key][key] = {
                    "value": value,
                    "expires_at": time.time() + ttl if ttl else None,
                    "created_at": time.time()
                }
            elif scope == DependencyScope.APPLICATION:
                self._application_cache[key] = {
                    "value": value,
                    "expires_at": time.time() + ttl if ttl else None,
                    "created_at": time.time()
                }
                
        except Exception as e:
            logging.warning(f"Cache storage error for {key}: {e}")

# Global dependency cache instance
dependency_cache = DependencyCache()

# ===============================================================================
# Advanced Dependency Decorators
# ===============================================================================

def cached_dependency(
    scope: str = DependencyScope.REQUEST,
    ttl: Optional[int] = None,
    cache_key_factory: Optional[Callable] = None
):
    """
    Advanced dependency caching decorator with intelligent scope management
    
    Args:
        scope: Cache scope (request, session, application, tenant, user)
        ttl: Time to live in seconds
        cache_key_factory: Custom cache key generation function
    """
    def decorator(func: Callable):
        func.__dependency_scope__ = scope
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs or args
            request = None
            context = None
            
            for arg in list(args) + list(kwargs.values()):
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, DependencyContext):
                    context = arg
            
            if not context:
                context = DependencyContext(request_id=str(uuid4()))
            
            # Generate cache key
            if cache_key_factory:
                cache_key = cache_key_factory(func, context, *args, **kwargs)
            else:
                cache_key = dependency_cache.get_cache_key(func, context)
            
            # Try to get from cache
            cached_value = await dependency_cache.get(cache_key, scope, request)
            if cached_value is not None:
                return cached_value["value"]
            
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Cache result
            await dependency_cache.set(cache_key, result, scope, ttl, request)
            
            return result
        
        return wrapper
    return decorator

def scoped_dependency(scope: str, cleanup_callback: Optional[Callable] = None):
    """
    Scoped dependency with automatic cleanup
    
    Args:
        scope: Dependency scope
        cleanup_callback: Optional cleanup function called when scope ends
    """
    def decorator(func: Callable):
        func.__dependency_scope__ = scope
        func.__cleanup_callback__ = cleanup_callback
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Register cleanup if provided
            if cleanup_callback:
                # Implementation would depend on scope management system
                pass
            
            return result
        
        return wrapper
    return decorator

# ===============================================================================
# Complex Dependency Providers
# ===============================================================================

class DatabaseConnectionManager:
    """Advanced database connection management with pooling and health checks"""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self.health_checks: Dict[str, datetime] = {}
        self.connection_stats = {
            "created": 0,
            "reused": 0,
            "health_check_failures": 0
        }
    
    @cached_dependency(scope=DependencyScope.REQUEST, ttl=300)
    async def get_read_connection(self, request: Request) -> AsyncSession:
        """Get optimized read-only database connection"""
        connection_key = "read_replica"
        
        if connection_key in self.connections:
            # Check connection health
            if await self._is_connection_healthy(connection_key):
                self.connection_stats["reused"] += 1
                return self.connections[connection_key]
            else:
                # Remove unhealthy connection
                await self._cleanup_connection(connection_key)
        
        # Create new connection
        connection = await self._create_connection(read_only=True)
        self.connections[connection_key] = connection
        self.health_checks[connection_key] = datetime.utcnow()
        self.connection_stats["created"] += 1
        
        return connection
    
    @cached_dependency(scope=DependencyScope.REQUEST, ttl=60)
    async def get_write_connection(self, request: Request) -> AsyncSession:
        """Get write-optimized database connection with shorter cache TTL"""
        connection_key = f"write_{hash(request)}"
        
        if connection_key in self.connections:
            if await self._is_connection_healthy(connection_key):
                self.connection_stats["reused"] += 1
                return self.connections[connection_key]
            else:
                await self._cleanup_connection(connection_key)
        
        connection = await self._create_connection(read_only=False)
        self.connections[connection_key] = connection
        self.health_checks[connection_key] = datetime.utcnow()
        self.connection_stats["created"] += 1
        
        return connection
    
    async def _create_connection(self, read_only: bool = False) -> AsyncSession:
        """Create new database connection with configuration"""
        # Implementation would create actual database connection
        # This is a mock for demonstration
        connection = AsyncSession()
        connection._read_only = read_only
        return connection
    
    async def _is_connection_healthy(self, connection_key: str) -> bool:
        """Check connection health with caching"""
        last_check = self.health_checks.get(connection_key)
        if not last_check or datetime.utcnow() - last_check > timedelta(minutes=5):
            try:
                # Perform actual health check
                connection = self.connections[connection_key]
                # await connection.execute("SELECT 1")
                self.health_checks[connection_key] = datetime.utcnow()
                return True
            except Exception:
                self.connection_stats["health_check_failures"] += 1
                return False
        return True
    
    async def _cleanup_connection(self, connection_key: str):
        """Clean up connection resources"""
        if connection_key in self.connections:
            connection = self.connections.pop(connection_key)
            # await connection.close()
            self.health_checks.pop(connection_key, None)

db_manager = DatabaseConnectionManager()

# ===============================================================================
# Context-Aware Dependency Providers
# ===============================================================================

class SecurityContext:
    """Advanced security context with role-based access and permissions"""
    
    def __init__(self):
        self.permission_cache: Dict[str, Dict[str, bool]] = {}
        self.role_hierarchy = {
            "admin": ["manager", "user", "readonly"],
            "manager": ["user", "readonly"], 
            "user": ["readonly"],
            "readonly": []
        }
    
    @cached_dependency(scope=DependencyScope.USER, ttl=900)  # 15 minute cache
    async def get_user_permissions(
        self, 
        user_id: UUID, 
        context: DependencyContext
    ) -> Dict[str, bool]:
        """Get user permissions with intelligent caching and hierarchy resolution"""
        
        cache_key = f"permissions:{user_id}"
        
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]
        
        # Fetch base permissions (mock implementation)
        base_permissions = await self._fetch_user_permissions(user_id)
        
        # Apply role hierarchy
        user_roles = base_permissions.get("roles", [])
        inherited_permissions = set()
        
        for role in user_roles:
            if role in self.role_hierarchy:
                inherited_permissions.update(self.role_hierarchy[role])
        
        # Combine with explicit permissions
        all_permissions = {
            **base_permissions,
            "effective_roles": list(set(user_roles + list(inherited_permissions)))
        }
        
        # Cache permissions
        self.permission_cache[cache_key] = all_permissions
        
        return all_permissions
    
    async def _fetch_user_permissions(self, user_id: UUID) -> Dict[str, Any]:
        """Fetch user permissions from database/cache"""
        # Mock implementation
        return {
            "user_id": str(user_id),
            "roles": ["user"],
            "permissions": ["read", "write"],
            "tenant_id": str(uuid4()),
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }

security_context = SecurityContext()

# ===============================================================================
# Dynamic Dependency Generation
# ===============================================================================

class DependencyFactory:
    """Factory for creating dynamic dependencies based on runtime conditions"""
    
    def __init__(self):
        self.provider_registry: Dict[str, Callable] = {}
        self.condition_evaluators: List[Callable] = []
    
    def register_provider(self, name: str, provider: Callable):
        """Register a dependency provider"""
        self.provider_registry[name] = provider
    
    def register_condition(self, evaluator: Callable):
        """Register a condition evaluator for dynamic provider selection"""
        self.condition_evaluators.append(evaluator)
    
    async def create_dependency(
        self, 
        dependency_type: str,
        context: DependencyContext,
        **kwargs
    ) -> Any:
        """Create dependency dynamically based on context and conditions"""
        
        # Evaluate conditions to determine provider
        selected_provider = None
        
        for evaluator in self.condition_evaluators:
            provider_name = await evaluator(dependency_type, context, **kwargs)
            if provider_name and provider_name in self.provider_registry:
                selected_provider = self.provider_registry[provider_name]
                break
        
        if not selected_provider and dependency_type in self.provider_registry:
            selected_provider = self.provider_registry[dependency_type]
        
        if not selected_provider:
            raise ValueError(f"No provider found for dependency type: {dependency_type}")
        
        # Create dependency
        if asyncio.iscoroutinefunction(selected_provider):
            return await selected_provider(context, **kwargs)
        else:
            return selected_provider(context, **kwargs)

dependency_factory = DependencyFactory()

# ===============================================================================
# Async Dependency Composition
# ===============================================================================

class AsyncDependencyComposer:
    """Compose multiple async dependencies with optimal execution strategies"""
    
    @staticmethod
    async def compose_parallel(
        dependencies: List[Callable],
        context: DependencyContext,
        **shared_kwargs
    ) -> Dict[str, Any]:
        """Execute multiple dependencies in parallel where possible"""
        
        # Analyze dependencies for parallelization opportunities
        parallel_deps = []
        sequential_deps = []
        
        for dep in dependencies:
            if hasattr(dep, '__parallel_safe__') and dep.__parallel_safe__:
                parallel_deps.append(dep)
            else:
                sequential_deps.append(dep)
        
        results = {}
        
        # Execute parallel dependencies
        if parallel_deps:
            parallel_tasks = []
            for dep in parallel_deps:
                if asyncio.iscoroutinefunction(dep):
                    task = asyncio.create_task(dep(context, **shared_kwargs))
                else:
                    task = asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(
                            None, dep, context, **shared_kwargs
                        )
                    )
                parallel_tasks.append((dep.__name__, task))
            
            # Wait for parallel execution completion
            for dep_name, task in parallel_tasks:
                try:
                    results[dep_name] = await task
                except Exception as e:
                    logging.error(f"Parallel dependency {dep_name} failed: {e}")
                    results[dep_name] = None
        
        # Execute sequential dependencies
        for dep in sequential_deps:
            try:
                if asyncio.iscoroutinefunction(dep):
                    results[dep.__name__] = await dep(context, **shared_kwargs, **results)
                else:
                    results[dep.__name__] = dep(context, **shared_kwargs, **results)
            except Exception as e:
                logging.error(f"Sequential dependency {dep.__name__} failed: {e}")
                results[dep.__name__] = None
        
        return results
    
    @staticmethod
    async def compose_conditional(
        condition_dep_map: Dict[Callable, List[Callable]],
        context: DependencyContext,
        **shared_kwargs
    ) -> Dict[str, Any]:
        """Compose dependencies based on conditional logic"""
        
        results = {}
        
        for condition_func, deps in condition_dep_map.items():
            try:
                # Evaluate condition
                if asyncio.iscoroutinefunction(condition_func):
                    condition_result = await condition_func(context, **shared_kwargs)
                else:
                    condition_result = condition_func(context, **shared_kwargs)
                
                # Execute dependencies if condition is met
                if condition_result:
                    for dep in deps:
                        if asyncio.iscoroutinefunction(dep):
                            results[dep.__name__] = await dep(context, **shared_kwargs, **results)
                        else:
                            results[dep.__name__] = dep(context, **shared_kwargs, **results)
                        
            except Exception as e:
                logging.error(f"Conditional dependency composition failed: {e}")
        
        return results

async_composer = AsyncDependencyComposer()

# ===============================================================================
# Resource Management Dependencies
# ===============================================================================

class ResourceManager:
    """Advanced resource management with automatic cleanup and monitoring"""
    
    def __init__(self):
        self.active_resources: Dict[str, Any] = {}
        self.resource_metrics = {
            "created": 0,
            "cleaned": 0,
            "leaked": 0
        }
    
    @asynccontextmanager
    async def managed_resource(
        self,
        resource_type: str,
        factory: Callable,
        cleanup: Callable,
        **factory_kwargs
    ) -> AsyncGenerator[Any, None]:
        """Create and manage resource with guaranteed cleanup"""
        
        resource_id = str(uuid4())
        resource = None
        
        try:
            # Create resource
            if asyncio.iscoroutinefunction(factory):
                resource = await factory(**factory_kwargs)
            else:
                resource = factory(**factory_kwargs)
            
            self.active_resources[resource_id] = {
                "resource": resource,
                "type": resource_type,
                "created_at": datetime.utcnow(),
                "cleanup": cleanup
            }
            self.resource_metrics["created"] += 1
            
            yield resource
            
        except Exception as e:
            logging.error(f"Resource {resource_type} error: {e}")
            raise
        finally:
            # Cleanup resource
            if resource_id in self.active_resources:
                resource_info = self.active_resources.pop(resource_id)
                try:
                    cleanup_func = resource_info["cleanup"]
                    if asyncio.iscoroutinefunction(cleanup_func):
                        await cleanup_func(resource_info["resource"])
                    else:
                        cleanup_func(resource_info["resource"])
                    self.resource_metrics["cleaned"] += 1
                except Exception as e:
                    logging.error(f"Resource cleanup failed for {resource_type}: {e}")
                    self.resource_metrics["leaked"] += 1
    
    async def cleanup_all_resources(self):
        """Emergency cleanup of all active resources"""
        for resource_id, resource_info in list(self.active_resources.items()):
            try:
                cleanup_func = resource_info["cleanup"]
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func(resource_info["resource"])
                else:
                    cleanup_func(resource_info["resource"])
                self.resource_metrics["cleaned"] += 1
            except Exception as e:
                logging.error(f"Emergency cleanup failed for {resource_info['type']}: {e}")
                self.resource_metrics["leaked"] += 1
            finally:
                self.active_resources.pop(resource_id, None)

resource_manager = ResourceManager()

# ===============================================================================
# Usage Examples and Test Dependencies
# ===============================================================================

@scoped_dependency(scope=DependencyScope.REQUEST)
async def get_dependency_context(request: Request) -> DependencyContext:
    """Create rich dependency context from request"""
    return DependencyContext(
        request_id=str(uuid4()),
        user_id=getattr(request.state, 'user_id', None),
        tenant_id=getattr(request.state, 'tenant_id', None),
        session_id=request.headers.get('X-Session-ID'),
        security_scopes=getattr(request.state, 'security_scopes', []),
        feature_flags=getattr(request.state, 'feature_flags', {}),
        metadata={
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None,
        }
    )

@cached_dependency(scope=DependencyScope.USER, ttl=600)
async def get_user_settings(
    user_id: UUID,
    context: DependencyContext = Depends(get_dependency_context)
) -> Dict[str, Any]:
    """Get user settings with intelligent caching"""
    
    # Mock user settings retrieval
    settings = {
        "user_id": str(user_id),
        "theme": "dark",
        "language": "en",
        "notifications": {
            "email": True,
            "push": False,
            "sms": True
        },
        "privacy": {
            "profile_visible": True,
            "activity_tracking": False
        }
    }
    
    return settings

async def get_optimized_database_session(
    request: Request,
    context: DependencyContext = Depends(get_dependency_context)
) -> AsyncSession:
    """Get database session optimized for request context"""
    
    # Determine if read-only access is sufficient
    is_read_only = request.method in ["GET", "HEAD", "OPTIONS"]
    
    if is_read_only:
        return await db_manager.get_read_connection(request)
    else:
        return await db_manager.get_write_connection(request)

async def get_multi_tenant_service(
    tenant_id: UUID,
    context: DependencyContext = Depends(get_dependency_context)
) -> Any:
    """Get tenant-specific service instance with configuration"""
    
    # Use dependency factory for dynamic service creation
    service = await dependency_factory.create_dependency(
        "tenant_service",
        context,
        tenant_id=tenant_id,
        configuration=await get_tenant_configuration(tenant_id)
    )
    
    return service

async def get_tenant_configuration(tenant_id: UUID) -> Dict[str, Any]:
    """Get tenant-specific configuration"""
    # Mock implementation
    return {
        "tenant_id": str(tenant_id),
        "features": ["feature_a", "feature_b"],
        "limits": {
            "api_calls_per_minute": 1000,
            "storage_gb": 100
        },
        "customizations": {
            "branding": True,
            "custom_domain": False
        }
    }

# Register providers with factory
dependency_factory.register_provider(
    "tenant_service", 
    lambda context, **kwargs: f"TenantService({kwargs.get('tenant_id')})"
)

# Example of complex dependency composition
async def get_comprehensive_user_context(
    request: Request,
    context: DependencyContext = Depends(get_dependency_context)
) -> Dict[str, Any]:
    """Compose comprehensive user context from multiple dependencies"""
    
    if not context.user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    # Define dependencies for parallel execution
    parallel_deps = [
        lambda ctx, **kwargs: get_user_settings(context.user_id, ctx),
        lambda ctx, **kwargs: security_context.get_user_permissions(context.user_id, ctx),
    ]
    
    # Mark dependencies as parallel-safe
    for dep in parallel_deps:
        dep.__parallel_safe__ = True
    
    # Execute dependencies in parallel
    results = await async_composer.compose_parallel(
        parallel_deps, 
        context,
        request=request
    )
    
    return {
        "context": context.dict(),
        "settings": results.get("get_user_settings"),
        "permissions": results.get("get_user_permissions"),
        "composed_at": datetime.utcnow().isoformat()
    }

# Example usage in FastAPI endpoints would be:
# 
# @app.get("/user/profile")
# async def get_user_profile(
#     user_context: Dict[str, Any] = Depends(get_comprehensive_user_context),
#     db: AsyncSession = Depends(get_optimized_database_session)
# ) -> Dict[str, Any]:
#     return user_context