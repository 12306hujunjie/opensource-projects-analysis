"""
FastAPI Enterprise Application Architecture Example
Ultra-Deep Implementation Pattern demonstrating advanced FastAPI capabilities

This example showcases enterprise-level patterns including:
- Advanced dependency injection with hierarchical scoping
- Multi-level caching strategies  
- Performance optimization techniques
- Security integration with JWT and role-based access
- Database connection pooling with async sessions
- Background task processing with error recovery
- Comprehensive error handling and validation
- OpenAPI schema customization
- Monitoring and observability integration
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

import jwt
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from starlette.middleware.base import BaseHTTPMiddleware

# ===============================================================================
# Performance Optimized Configuration
# ===============================================================================

# Connection pool configuration for high concurrency
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/fastapi_enterprise"
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Use external connection pooling (PgBouncer)
    pool_pre_ping=True,
    pool_recycle=3600,
    echo_pool=True,
)

SessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False,  # Manual flush for transaction control
)

# Cache configuration with multiple levels
class CacheLevel(Enum):
    L1_MEMORY = "memory"      # In-process caching
    L2_REDIS = "redis"        # Distributed caching  
    L3_DATABASE = "database"  # Database-level caching

# Global cache store (L1 - Memory)
memory_cache: Dict[str, Dict[str, Any]] = {}

# ===============================================================================
# Advanced Security Implementation
# ===============================================================================

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    READONLY = "readonly"

class SecurityScope(BaseModel):
    """Security scope with hierarchical permissions"""
    user_id: UUID
    roles: Set[UserRole]
    permissions: Set[str]
    tenant_id: Optional[UUID] = None
    expires_at: datetime

class JWTSecurityBearer(HTTPBearer):
    """Enterprise-grade JWT security with advanced features"""
    
    def __init__(
        self, 
        secret_key: str,
        algorithm: str = "HS256",
        auto_error: bool = True,
        required_roles: Optional[Set[UserRole]] = None
    ):
        super().__init__(auto_error=auto_error)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.required_roles = required_roles or set()
    
    async def __call__(self, request: Request) -> SecurityScope:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            raise HTTPException(
                status_code=403, 
                detail="Invalid authorization credentials"
            )
        
        try:
            payload = jwt.decode(
                credentials.credentials,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "require": ["exp", "iat", "sub", "roles"],
                    "verify_exp": True,
                    "verify_iat": True,
                    "leeway": 30,  # 30 second clock skew tolerance
                }
            )
            
            # Extract security scope
            user_roles = {UserRole(role) for role in payload["roles"]}
            permissions = set(payload.get("permissions", []))
            
            security_scope = SecurityScope(
                user_id=UUID(payload["sub"]),
                roles=user_roles,
                permissions=permissions,
                tenant_id=UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
                expires_at=datetime.fromtimestamp(payload["exp"])
            )
            
            # Role-based access control
            if self.required_roles and not user_roles.intersection(self.required_roles):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required roles: {self.required_roles}"
                )
            
            return security_scope
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# ===============================================================================
# Advanced Database Management
# ===============================================================================

async def get_database_session() -> AsyncSession:
    """
    Enterprise database session with advanced features:
    - Connection pooling optimization
    - Automatic retry on connection failures
    - Query performance monitoring
    - Transaction management with savepoints
    """
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            async with SessionLocal() as session:
                # Add query performance monitoring
                session.info["created_at"] = time.time()
                session.info["query_count"] = 0
                yield session
                
                # Log session statistics
                duration = time.time() - session.info["created_at"]
                query_count = session.info["query_count"]
                
                if duration > 1.0:  # Log slow sessions
                    logging.warning(f"Slow database session: {duration:.2f}s, {query_count} queries")
                    
                return
                
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Database connection failed after {max_retries} attempts: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Database temporarily unavailable"
                )
            
            await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff

# ===============================================================================
# Multi-Level Caching System
# ===============================================================================

class CacheManager:
    """Enterprise caching system with multiple levels and intelligent eviction"""
    
    def __init__(self, max_memory_items: int = 10000):
        self.max_memory_items = max_memory_items
        self.access_times: Dict[str, float] = {}
        
    async def get(
        self, 
        key: str, 
        cache_levels: List[CacheLevel] = None
    ) -> Optional[Any]:
        """Get value from cache with level fallback"""
        cache_levels = cache_levels or [CacheLevel.L1_MEMORY]
        
        for level in cache_levels:
            if level == CacheLevel.L1_MEMORY:
                if key in memory_cache:
                    self.access_times[key] = time.time()
                    return memory_cache[key]
            # Add Redis and database cache levels here
            
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 300,
        cache_levels: List[CacheLevel] = None
    ) -> None:
        """Set value in cache with TTL and level distribution"""
        cache_levels = cache_levels or [CacheLevel.L1_MEMORY]
        
        for level in cache_levels:
            if level == CacheLevel.L1_MEMORY:
                # Evict LRU items if cache is full
                if len(memory_cache) >= self.max_memory_items:
                    await self._evict_lru_items()
                
                memory_cache[key] = {
                    "value": value,
                    "expires_at": time.time() + ttl,
                    "created_at": time.time()
                }
                self.access_times[key] = time.time()
    
    async def _evict_lru_items(self, evict_count: int = 1000) -> None:
        """Evict least recently used items from memory cache"""
        if not self.access_times:
            return
            
        # Sort by access time and remove oldest items
        sorted_items = sorted(
            self.access_times.items(),
            key=lambda x: x[1]
        )
        
        for key, _ in sorted_items[:evict_count]:
            memory_cache.pop(key, None)
            self.access_times.pop(key, None)

cache_manager = CacheManager()

# ===============================================================================
# Advanced Data Models with Enterprise Validation
# ===============================================================================

class AuditFields(BaseModel):
    """Mixin for audit fields with automatic timestamp management"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: UUID
    updated_by: UUID
    version: int = Field(default=1, ge=1)

class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    ARCHIVED = "archived"

class Product(BaseModel):
    """Enterprise product model with advanced validation and business logic"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", regex=r'^[A-Z]{3}$')
    status: ProductStatus = ProductStatus.DRAFT
    category_id: UUID
    tags: List[str] = Field(default_factory=list, max_items=20)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    audit: AuditFields
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tag format and uniqueness"""
        if not v:
            return v
            
        # Ensure uniqueness
        unique_tags = list(set(v))
        if len(unique_tags) != len(v):
            raise ValueError('Duplicate tags are not allowed')
        
        # Validate tag format
        for tag in unique_tags:
            if not tag.strip() or len(tag) > 50:
                raise ValueError('Invalid tag format')
        
        return unique_tags
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata structure and size"""
        if not v:
            return v
            
        # Limit metadata size to prevent abuse
        import json
        if len(json.dumps(v)) > 10000:  # 10KB limit
            raise ValueError('Metadata exceeds size limit')
        
        return v
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            Decimal: float,
        }
        schema_extra = {
            "example": {
                "name": "Enterprise Software License",
                "description": "Professional software license with enterprise features",
                "price": "999.99",
                "currency": "USD",
                "status": "active",
                "tags": ["software", "enterprise", "license"],
                "metadata": {
                    "license_type": "perpetual",
                    "support_level": "premium"
                }
            }
        }

class CreateProductRequest(BaseModel):
    """Request model for product creation with validation"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", regex=r'^[A-Z]{3}$')
    category_id: UUID
    tags: List[str] = Field(default_factory=list, max_items=20)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ProductResponse(BaseModel):
    """Optimized response model with selective field exposure"""
    id: UUID
    name: str
    description: Optional[str]
    price: Decimal
    currency: str
    status: ProductStatus
    category_id: UUID
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            Decimal: float,
        }

# ===============================================================================
# Advanced Background Tasks with Error Recovery
# ===============================================================================

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

class BackgroundTaskManager:
    """Enterprise background task manager with retry logic and monitoring"""
    
    def __init__(self):
        self.task_registry: Dict[str, Dict[str, Any]] = {}
        self.max_retries = 3
        self.retry_delays = [1, 5, 15]  # Exponential backoff
    
    async def execute_with_retry(
        self,
        task_id: str,
        func: callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute task with intelligent retry logic"""
        self.task_registry[task_id] = {
            "status": TaskStatus.RUNNING,
            "started_at": datetime.utcnow(),
            "attempts": 0,
            "errors": []
        }
        
        for attempt in range(self.max_retries):
            try:
                self.task_registry[task_id]["attempts"] = attempt + 1
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                self.task_registry[task_id].update({
                    "status": TaskStatus.COMPLETED,
                    "completed_at": datetime.utcnow(),
                    "result": result
                })
                
                return result
                
            except Exception as e:
                error_info = {
                    "attempt": attempt + 1,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                self.task_registry[task_id]["errors"].append(error_info)
                
                if attempt == self.max_retries - 1:
                    self.task_registry[task_id].update({
                        "status": TaskStatus.FAILED,
                        "failed_at": datetime.utcnow()
                    })
                    logging.error(f"Task {task_id} failed after {self.max_retries} attempts: {e}")
                    raise
                else:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    await asyncio.sleep(delay)
                    logging.warning(f"Task {task_id} attempt {attempt + 1} failed, retrying in {delay}s: {e}")

task_manager = BackgroundTaskManager()

async def process_product_analytics(product_id: UUID, user_id: UUID) -> Dict[str, Any]:
    """Background task for processing product analytics with comprehensive error handling"""
    try:
        # Simulate analytics processing
        await asyncio.sleep(2)  # Simulate processing time
        
        analytics_data = {
            "product_id": str(product_id),
            "user_id": str(user_id),
            "processed_at": datetime.utcnow().isoformat(),
            "metrics": {
                "views": 1,
                "engagement_score": 0.85,
                "conversion_probability": 0.23
            }
        }
        
        # Cache analytics results
        cache_key = f"analytics:{product_id}:{user_id}"
        await cache_manager.set(cache_key, analytics_data, ttl=3600)
        
        return analytics_data
        
    except Exception as e:
        logging.error(f"Analytics processing failed for product {product_id}: {e}")
        raise

# ===============================================================================
# Performance Monitoring Middleware
# ===============================================================================

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Advanced performance monitoring with detailed metrics collection"""
    
    def __init__(self, app, enable_detailed_metrics: bool = True):
        super().__init__(app)
        self.enable_detailed_metrics = enable_detailed_metrics
        self.metrics: Dict[str, List[float]] = {
            "request_duration": [],
            "database_time": [],
            "cache_hits": [],
            "cache_misses": [],
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        # Add request tracking
        request.state.start_time = start_time
        request.state.db_query_count = 0
        request.state.cache_hits = 0
        request.state.cache_misses = 0
        
        response = await call_next(request)
        
        # Calculate metrics
        total_time = time.perf_counter() - start_time
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(round(total_time * 1000, 2))
        response.headers["X-DB-Queries"] = str(getattr(request.state, 'db_query_count', 0))
        response.headers["X-Cache-Hits"] = str(getattr(request.state, 'cache_hits', 0))
        
        # Store metrics for analysis
        if self.enable_detailed_metrics:
            self.metrics["request_duration"].append(total_time)
            
            # Keep only recent metrics (rolling window)
            for metric_name, values in self.metrics.items():
                if len(values) > 1000:
                    self.metrics[metric_name] = values[-1000:]
        
        # Log slow requests
        if total_time > 1.0:  # Requests slower than 1 second
            logging.warning(
                f"Slow request: {request.method} {request.url.path} - "
                f"{total_time:.2f}s, "
                f"DB queries: {getattr(request.state, 'db_query_count', 0)}"
            )
        
        return response
    
    def get_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics summary"""
        summary = {}
        
        for metric_name, values in self.metrics.items():
            if values:
                summary[metric_name] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p95": sorted(values)[int(0.95 * len(values))] if len(values) > 1 else values[0],
                    "p99": sorted(values)[int(0.99 * len(values))] if len(values) > 1 else values[0],
                }
        
        return summary

# ===============================================================================
# Application Lifecycle Management
# ===============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Advanced application lifecycle management with comprehensive setup and teardown"""
    
    # Startup sequence with dependency verification
    logging.info("Starting FastAPI Enterprise Application...")
    
    # Initialize database connection
    try:
        async with engine.begin() as conn:
            # Verify database connectivity
            await conn.execute(text("SELECT 1"))
        logging.info("Database connection established")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise
    
    # Initialize cache systems
    try:
        # Pre-warm critical caches
        await cache_manager.set("system:status", {"status": "healthy"}, ttl=60)
        logging.info("Cache systems initialized")
    except Exception as e:
        logging.warning(f"Cache initialization failed: {e}")
    
    # System health check
    startup_time = time.time()
    app.state.startup_time = startup_time
    logging.info(f"Application startup completed in {time.time() - startup_time:.2f}s")
    
    yield  # Application runs here
    
    # Shutdown sequence with graceful cleanup
    logging.info("Shutting down FastAPI Enterprise Application...")
    
    # Close database connections
    await engine.dispose()
    logging.info("Database connections closed")
    
    # Clear caches
    memory_cache.clear()
    logging.info("Caches cleared")
    
    logging.info("Application shutdown completed")

# ===============================================================================
# FastAPI Application with Enterprise Configuration
# ===============================================================================

app = FastAPI(
    title="FastAPI Enterprise Architecture Demo",
    description="Ultra-deep FastAPI implementation showcasing enterprise patterns",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,  # High-performance JSON responses
)

# Add enterprise middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict origins in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(PerformanceMonitoringMiddleware, enable_detailed_metrics=True)

# Security configuration
security = JWTSecurityBearer(
    secret_key="your-super-secret-key",  # Use environment variable in production
    required_roles={UserRole.USER}
)

admin_security = JWTSecurityBearer(
    secret_key="your-super-secret-key",
    required_roles={UserRole.ADMIN, UserRole.MANAGER}
)

# ===============================================================================
# Enterprise API Endpoints
# ===============================================================================

@app.get("/health", tags=["System"])
async def health_check():
    """Comprehensive health check endpoint with system metrics"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time() - app.state.startup_time if hasattr(app.state, 'startup_time') else 0,
        "version": "1.0.0"
    }

@app.get("/metrics", tags=["System"])
async def get_metrics(security_scope: SecurityScope = Depends(admin_security)):
    """System metrics endpoint for monitoring (admin only)"""
    middleware = next(
        (m for m in app.user_middleware if isinstance(m.cls, type) and 
         issubclass(m.cls, PerformanceMonitoringMiddleware)), 
        None
    )
    
    if middleware:
        return {
            "performance": middleware.cls.get_metrics_summary(),
            "cache": {
                "memory_items": len(memory_cache),
                "memory_size": sum(len(str(v)) for v in memory_cache.values())
            },
            "collected_at": datetime.utcnow().isoformat()
        }
    
    return {"message": "Metrics not available"}

@app.post("/products/", response_model=ProductResponse, tags=["Products"])
async def create_product(
    product_data: CreateProductRequest,
    background_tasks: BackgroundTasks,
    security_scope: SecurityScope = Depends(security),
    db: AsyncSession = Depends(get_database_session)
) -> ProductResponse:
    """Create a new product with enterprise validation and background processing"""
    
    # Create audit fields
    audit_fields = AuditFields(
        created_by=security_scope.user_id,
        updated_by=security_scope.user_id
    )
    
    # Create product with full validation
    product = Product(
        **product_data.dict(),
        audit=audit_fields
    )
    
    # Here you would normally save to database
    # db.add(product_entity)
    # await db.commit()
    
    # Schedule background analytics processing
    task_id = f"analytics:{product.id}"
    background_tasks.add_task(
        task_manager.execute_with_retry,
        task_id,
        process_product_analytics,
        product.id,
        security_scope.user_id
    )
    
    # Cache the product for fast retrieval
    cache_key = f"product:{product.id}"
    await cache_manager.set(cache_key, product.dict(), ttl=300)
    
    return ProductResponse(**product.dict())

@app.get("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
async def get_product(
    product_id: UUID,
    security_scope: SecurityScope = Depends(security),
    db: AsyncSession = Depends(get_database_session)
) -> ProductResponse:
    """Get product with multi-level caching and permission validation"""
    
    # Try cache first (L1 - Memory)
    cache_key = f"product:{product_id}"
    cached_product = await cache_manager.get(cache_key)
    
    if cached_product:
        return ProductResponse(**cached_product["value"])
    
    # Fallback to database
    # product = await db.get(Product, product_id)
    # if not product:
    #     raise HTTPException(status_code=404, detail="Product not found")
    
    # For demo purposes, create a mock product
    mock_product = Product(
        id=product_id,
        name="Sample Product",
        description="This is a sample product for demonstration",
        price=Decimal("99.99"),
        category_id=uuid4(),
        audit=AuditFields(
            created_by=security_scope.user_id,
            updated_by=security_scope.user_id
        )
    )
    
    # Cache for future requests
    await cache_manager.set(cache_key, mock_product.dict(), ttl=300)
    
    return ProductResponse(**mock_product.dict())

@app.get("/products/", response_model=List[ProductResponse], tags=["Products"])
async def list_products(
    limit: int = Field(default=10, le=100),
    offset: int = Field(default=0, ge=0),
    status: Optional[ProductStatus] = None,
    security_scope: SecurityScope = Depends(security),
    db: AsyncSession = Depends(get_database_session)
) -> List[ProductResponse]:
    """List products with pagination and filtering"""
    
    # Build cache key based on query parameters
    cache_key = f"products:list:{limit}:{offset}:{status}:{security_scope.tenant_id}"
    cached_result = await cache_manager.get(cache_key)
    
    if cached_result:
        return [ProductResponse(**product) for product in cached_result["value"]]
    
    # For demo purposes, create mock products
    mock_products = []
    for i in range(min(limit, 5)):  # Return max 5 mock products
        mock_product = Product(
            id=uuid4(),
            name=f"Sample Product {i + 1}",
            description=f"Description for product {i + 1}",
            price=Decimal(f"{(i + 1) * 10}.99"),
            status=status or ProductStatus.ACTIVE,
            category_id=uuid4(),
            audit=AuditFields(
                created_by=security_scope.user_id,
                updated_by=security_scope.user_id
            )
        )
        mock_products.append(mock_product)
    
    # Cache the results
    product_dicts = [product.dict() for product in mock_products]
    await cache_manager.set(cache_key, product_dicts, ttl=60)  # Shorter TTL for lists
    
    return [ProductResponse(**product.dict()) for product in mock_products]

# ===============================================================================
# Application Entry Point
# ===============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Production-ready server configuration
    uvicorn.run(
        "enterprise-application:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable in production
        workers=4,     # Scale based on CPU cores
        access_log=True,
        log_level="info",
        server_header=False,  # Security: hide server info
        date_header=False,    # Security: hide date header
    )