# FastAPI 依赖注入系统

## 简介

FastAPI 的依赖注入系统是其最强大的功能之一，提供自动验证、缓存和分层依赖解析。该系统允许清晰的关注点分离、可测试性和跨应用的代码重用。

## 核心组件

### 1. Dependant 数据结构

`Dependant` 数据类是 FastAPI 依赖系统的基础：

```python
@dataclass
class Dependant:
    path_params: List[ModelField] = field(default_factory=list)
    query_params: List[ModelField] = field(default_factory=list) 
    header_params: List[ModelField] = field(default_factory=list)
    cookie_params: List[ModelField] = field(default_factory=list)
    body_params: List[ModelField] = field(default_factory=list)
    dependencies: List["Dependant"] = field(default_factory=list)
    security_requirements: List[SecurityRequirement] = field(default_factory=list)
    name: Optional[str] = None
    call: Optional[Callable[..., Any]] = None
    request_param_name: Optional[str] = None
    websocket_param_name: Optional[str] = None
    http_connection_param_name: Optional[str] = None
    response_param_name: Optional[str] = None
    background_tasks_param_name: Optional[str] = None
    security_scopes_param_name: Optional[str] = None
    security_scopes: Optional[List[str]] = None
    use_cache: bool = True
    path: Optional[str] = None
    cache_key: Tuple[Optional[Callable[..., Any]], Tuple[str, ...]] = field(init=False)
```

关键特征：
- **参数分类**：分离不同的参数类型（路径、查询、正文等）
- **依赖层次结构**：维护子依赖项列表
- **缓存控制**：支持依赖结果缓存
- **安全集成**：处理安全要求和作用域

### 2. SolvedDependency 结果

依赖解析过程返回一个 `SolvedDependency`：

```python
@dataclass
class SolvedDependency:
    values: Dict[str, Any]  # 已解析的参数值
    errors: List[Any]       # 验证错误
    background_tasks: Optional[StarletteBackgroundTasks]  # 后台任务
    response: Response      # 响应对象
    dependency_cache: Dict[Tuple[Callable[..., Any], Tuple[str]], Any]  # 缓存
```

## 依赖分析阶段

### 1. 函数签名分析

`get_dependant` 函数分析端点函数以提取依赖项：

```python
def get_dependant(
    *,
    path: str,
    call: Callable[..., Any],
    name: Optional[str] = None,
    security_scopes: Optional[List[str]] = None,
    use_cache: bool = True,
) -> Dependant:
    path_param_names = get_path_param_names(path)
    endpoint_signature = get_typed_signature(call)
    signature_params = endpoint_signature.parameters
    
    dependant = Dependant(
        call=call,
        name=name,
        path=path,
        security_scopes=security_scopes,
        use_cache=use_cache,
    )
    
    for param_name, param in signature_params.items():
        is_path_param = param_name in path_param_names
        param_details = analyze_param(
            param_name=param_name,
            annotation=param.annotation,
            value=param.default,
            is_path_param=is_path_param,
        )
        # Process parameter details...
```

### 2. 参数分析

`analyze_param` 函数确定每个参数应该如何处理：

```python
def analyze_param(
    *,
    param_name: str,
    annotation: Any,
    value: Any,
    is_path_param: bool,
) -> ParamDetails:
    field_info = None
    depends = None
    type_annotation: Any = Any
    
    # 检查参数是否有显式字段信息（Path、Query、Body 等）
    if isinstance(value, params.Depends):
        depends = value
        field_info = None
        type_annotation = annotation
    elif value == params.Depends:
        depends = params.Depends()
        field_info = None
        type_annotation = annotation
    elif isinstance(value, (params.Path, params.Query, params.Header, ...)):
        field_info = value
        type_annotation = annotation
    else:
        # 基于上下文推断参数类型
        if is_path_param:
            field_info = params.Path()
        else:
            field_info = params.Query()
        type_annotation = annotation
    
    return ParamDetails(type_annotation=type_annotation, depends=depends, field=field)
```

参数分类规则：
- **显式依赖项**：`param: Type = Depends(dependency_func)`
- **路径参数**：URL 路径模式中的参数
- **查询参数**：没有正文注释的非路径参数的默认值
- **正文参数**：具有显式 `Body()` 注释或 Pydantic 模型的参数
- **请求头/Cookie 参数**：具有 `Header()` 或 `Cookie()` 注释的参数

### 3. 依赖关系图构建

FastAPI 在分析期间构建完整的依赖关系图：

```python
# Example dependency chain
async def get_db():
    return database_connection

async def get_current_user(token: str = Header(...), db = Depends(get_db)):
    return authenticate_user(db, token)

@app.get("/users/me")
async def read_user_me(user = Depends(get_current_user)):
    return user

# Resulting dependency graph:
# read_user_me -> get_current_user -> [get_db, token from header]
```

The dependency graph supports:
- **Nested Dependencies**: Dependencies can have their own dependencies
- **Multiple Dependencies**: Single function can depend on multiple sources
- **Circular Dependency Detection**: Prevents infinite dependency loops
- **Caching Optimization**: Shared dependencies are cached per request

## 依赖解析阶段

### 1. The solve_dependencies Function

The core resolution happens in the `solve_dependencies` function:

```python
async def solve_dependencies(
    *,
    request: Union[Request, WebSocket],
    dependant: Dependant,
    body: Optional[Union[Dict[str, Any], FormData]] = None,
    background_tasks: Optional[StarletteBackgroundTasks] = None,
    response: Optional[Response] = None,
    dependency_overrides_provider: Optional[Any] = None,
    dependency_cache: Optional[Dict[Tuple[Callable[..., Any], Tuple[str]], Any]] = None,
    async_exit_stack: AsyncExitStack,
    embed_body_fields: bool,
) -> SolvedDependency:
```

Resolution process:
1. **Recursive Resolution**: Resolve sub-dependencies first
2. **Cache Checking**: Check if dependency result is already cached
3. **Function Execution**: Execute dependency function with resolved parameters
4. **Result Caching**: Cache result for future use (if caching enabled)
5. **Error Collection**: Aggregate validation errors from all dependencies

### 2. Sub-dependency Resolution

Dependencies are resolved recursively:

```python
# In solve_dependencies function
for sub_dependant in dependant.dependencies:
    # Handle dependency overrides
    if (dependency_overrides_provider and 
        dependency_overrides_provider.dependency_overrides):
        original_call = sub_dependant.call
        call = dependency_overrides_provider.dependency_overrides.get(
            original_call, original_call
        )
        # Create new dependant with overridden function
        use_sub_dependant = get_dependant(path=use_path, call=call, ...)
    
    # Recursively solve sub-dependencies
    solved_result = await solve_dependencies(
        request=request,
        dependant=use_sub_dependant,
        body=body,
        # ... other parameters
    )
    
    # Check cache or execute dependency function
    if sub_dependant.use_cache and sub_dependant.cache_key in dependency_cache:
        solved = dependency_cache[sub_dependant.cache_key]
    elif is_gen_callable(call) or is_async_gen_callable(call):
        solved = await solve_generator(call=call, stack=async_exit_stack, ...)
    elif is_coroutine_callable(call):
        solved = await call(**solved_result.values)
    else:
        solved = await run_in_threadpool(call, **solved_result.values)
    
    # Cache result
    if sub_dependant.cache_key not in dependency_cache:
        dependency_cache[sub_dependant.cache_key] = solved
```

### 3. Parameter Value Extraction

After resolving dependencies, FastAPI extracts parameter values from the request:

```python
# Extract path parameters
path_values, path_errors = request_params_to_args(
    dependant.path_params, request.path_params
)

# Extract query parameters
query_values, query_errors = request_params_to_args(
    dependant.query_params, request.query_params
)

# Extract header parameters
header_values, header_errors = request_params_to_args(
    dependant.header_params, request.headers
)

# Extract cookie parameters
cookie_values, cookie_errors = request_params_to_args(
    dependant.cookie_params, request.cookies
)

# Handle request body
if dependant.body_params:
    body_values, body_errors = await request_body_to_args(
        body_fields=dependant.body_params,
        received_body=body,
        embed_body_fields=embed_body_fields,
    )
```

### 4. Special Parameter Injection

FastAPI automatically injects special parameters:

```python
# Inject Request/WebSocket objects
if dependant.request_param_name and isinstance(request, Request):
    values[dependant.request_param_name] = request
elif dependant.websocket_param_name and isinstance(request, WebSocket):
    values[dependant.websocket_param_name] = request

# Inject HTTP connection
if dependant.http_connection_param_name:
    values[dependant.http_connection_param_name] = request

# Inject BackgroundTasks
if dependant.background_tasks_param_name:
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    values[dependant.background_tasks_param_name] = background_tasks

# Inject Response object
if dependant.response_param_name:
    values[dependant.response_param_name] = response

# Inject Security Scopes
if dependant.security_scopes_param_name:
    values[dependant.security_scopes_param_name] = SecurityScopes(
        scopes=dependant.security_scopes
    )
```

## 依赖类型和模式

### 1. Function Dependencies

Simple function-based dependencies:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/items/")
def read_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
```

### 2. Class Dependencies

Class-based dependencies with initialization parameters:

```python
class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        
    def get_connection(self):
        return create_connection(self.database_url)

def get_db_manager():
    return DatabaseManager(settings.database_url)

@app.get("/items/")
def read_items(db_manager: DatabaseManager = Depends(get_db_manager)):
    return db_manager.get_connection().query(Item).all()
```

### 3. Generator Dependencies (Context Managers)

Dependencies that need cleanup:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db  # This value is injected
    finally:
        db.close()  # Cleanup happens automatically

async def get_redis():
    redis = await aioredis.create_redis_pool('redis://localhost')
    try:
        yield redis
    finally:
        redis.close()
        await redis.wait_closed()
```

Generator dependencies are handled specially:
- **Sync Generators**: Run in thread pool with context manager
- **Async Generators**: Run directly with async context manager
- **Resource Management**: Automatic cleanup via AsyncExitStack

### 4. Sub-dependencies with Parameters

Dependencies can have their own parameters:

```python
def get_query_filter(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
):
    return {"skip": skip, "limit": limit}

def get_items(
    db: Session = Depends(get_db),
    query_filter: dict = Depends(get_query_filter),
):
    return db.query(Item).offset(query_filter["skip"]).limit(query_filter["limit"])

@app.get("/items/")
def read_items(items = Depends(get_items)):
    return items
```

## 缓存系统

### 1. Cache Key Generation

FastAPI generates cache keys based on the dependency function and security scopes:

```python
# In Dependant.__post_init__
def __post_init__(self) -> None:
    self.cache_key = (self.call, tuple(sorted(set(self.security_scopes or []))))
```

Cache key components:
- **Function Object**: The actual dependency function
- **Security Scopes**: Sorted tuple of security scopes
- **Uniqueness**: Ensures different security contexts don't share cache

### 2. Cache Lifecycle

Caching behavior:
- **Request Scope**: Cache is maintained for the duration of a single request
- **Automatic Cleanup**: Cache is discarded after request completion
- **Opt-out Available**: Dependencies can disable caching with `use_cache=False`

```python
# Cached dependency (default)
def expensive_computation():
    # This will only run once per request
    return perform_heavy_calculation()

# Non-cached dependency
def always_fresh_data():
    # This runs every time it's needed
    return get_current_timestamp()

@app.get("/endpoint")
def endpoint(
    cached_data = Depends(expensive_computation),  # Cached
    fresh_data = Depends(always_fresh_data, use_cache=False),  # Not cached
):
    return {"cached": cached_data, "fresh": fresh_data}
```

### 3. Cache Sharing

Dependencies with identical functions and security scopes share cache:

```python
def get_current_user(token: str = Header(...)):
    return authenticate_user(token)

@app.get("/profile")
def get_profile(user = Depends(get_current_user)):
    return user.profile

@app.get("/settings") 
def get_settings(user = Depends(get_current_user)):  # Same user, cached
    return user.settings
```

## 依赖覆盖

### 1. Override Mechanism

FastAPI supports dependency overrides for testing and configuration:

```python
app = FastAPI()

def get_db():
    return ProductionDatabase()

def get_test_db():
    return TestDatabase()

# Override for testing
app.dependency_overrides[get_db] = get_test_db
```

### 2. Override Resolution

The override resolution happens during dependency resolution:

```python
# In solve_dependencies function
if (dependency_overrides_provider and 
    dependency_overrides_provider.dependency_overrides):
    original_call = sub_dependant.call
    call = dependency_overrides_provider.dependency_overrides.get(
        original_call, original_call
    )
    # Use overridden function instead of original
```

Override characteristics:
- **Function-level Overrides**: Override specific dependency functions
- **Recursive Application**: Overrides apply to sub-dependencies
- **Test-friendly**: Ideal for mocking dependencies in tests

## 错误处理和验证

### 1. Error Collection

Dependency resolution collects errors from all sources:

```python
# Errors are collected from multiple sources:
errors: List[Any] = []

# Sub-dependency errors
if solved_result.errors:
    errors.extend(solved_result.errors)

# Parameter validation errors  
errors += path_errors + query_errors + header_errors + cookie_errors

# Body validation errors
if dependant.body_params:
    body_values, body_errors = await request_body_to_args(...)
    errors.extend(body_errors)
```

### 2. Error Types

Common dependency-related errors:
- **Missing Required Parameters**: Path or query parameters not provided
- **Type Validation Errors**: Parameter values don't match expected types
- **Dependency Resolution Errors**: Dependency functions raise exceptions
- **Circular Dependencies**: Dependency cycles detected during analysis

### 3. Error Response Format

Validation errors are formatted consistently:

```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["query", "limit"],
            "msg": "Field required",
            "input": null
        },
        {
            "type": "int_parsing",
            "loc": ["path", "user_id"], 
            "msg": "Input should be a valid integer",
            "input": "abc"
        }
    ]
}
```

## 高级依赖模式

### 1. Dependency Factories

Create dependencies with configuration:

```python
def create_database_dependency(database_url: str):
    def get_database():
        return Database(database_url)
    return get_database

# Configure for different environments
if settings.environment == "production":
    get_db = create_database_dependency(settings.prod_db_url)
else:
    get_db = create_database_dependency(settings.test_db_url)
```

### 2. Conditional Dependencies

Dependencies that vary based on conditions:

```python
def get_auth_dependency():
    if settings.auth_required:
        return Depends(verify_token)
    else:
        return Depends(lambda: None)  # No-op dependency

@app.get("/data")
def get_data(auth = get_auth_dependency()):
    return {"data": "secret" if auth else "public"}
```

### 3. Dependency Composition

Combine multiple dependencies:

```python
def compose_dependencies(*deps):
    async def composed(**kwargs):
        results = []
        for dep in deps:
            if callable(dep):
                result = await dep(**kwargs)
                results.append(result)
        return results
    return composed

combined = compose_dependencies(get_db, get_cache, get_logger)

@app.get("/complex")
def complex_endpoint(services = Depends(combined)):
    db, cache, logger = services
    # Use all services...
```

## 性能考虑

### 1. Dependency Resolution Optimization

- **Graph Analysis**: Dependencies analyzed once during startup
- **Compilation**: Dependency graphs compiled for fast resolution
- **Caching**: Aggressive caching reduces redundant computations
- **Async Support**: Native async/await throughout resolution chain

### 2. Memory Management

- **Request Scope**: Dependency cache cleared after each request
- **Generator Cleanup**: Automatic resource cleanup via context managers
- **Weak References**: No memory leaks from dependency references

### 3. Performance Tips

```python
# Good: Use caching for expensive operations
@lru_cache()
def expensive_dependency():
    return heavy_computation()

# Good: Use generators for resource management
def get_db():
    db = create_connection()
    try:
        yield db
    finally:
        db.close()

# Avoid: Creating new objects in dependencies unnecessarily
def bad_dependency():
    return ExpensiveObject()  # Created every time

# Better: Reuse singleton
_expensive_object = None
def good_dependency():
    global _expensive_object
    if _expensive_object is None:
        _expensive_object = ExpensiveObject()
    return _expensive_object
```

## 最佳实践

### 1. Dependency Organization

```python
# dependencies.py - Centralized dependency definitions
def get_db():
    return database_connection

def get_current_user(token: str = Header(...)):
    return authenticate_user(token)

# routers/users.py - Import and use dependencies
from dependencies import get_db, get_current_user

@router.get("/me")
def read_user_me(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    return current_user
```

### 2. Testing with Overrides

```python
# test_app.py
def test_endpoint():
    def mock_get_db():
        return MockDatabase()
    
    app.dependency_overrides[get_db] = mock_get_db
    
    with TestClient(app) as client:
        response = client.get("/endpoint")
        assert response.status_code == 200
    
    # Clean up
    app.dependency_overrides = {}
```

### 3. Security Dependencies

```python
# security.py
def verify_api_key(api_key: str = Header(...)):
    if api_key not in valid_api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

def get_current_user(api_key = Depends(verify_api_key)):
    return get_user_by_api_key(api_key)

# Protected endpoints
@app.get("/protected")
def protected_endpoint(user = Depends(get_current_user)):
    return {"message": f"Hello {user.name}"}
```

## 下一章节

继续阅读 [Pydantic 集成](./05-pydantic-integration.md) 以了解 FastAPI 如何利用 Pydantic 进行数据验证和序列化。