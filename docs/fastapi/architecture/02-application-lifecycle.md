# FastAPI 应用生命周期

## 简介

理解 FastAPI 的应用生命周期对于有效的开发和部署至关重要。本文档深入分析了 FastAPI 应用如何初始化、配置和执行。

## 应用初始化序列

### 1. FastAPI 构造函数分析

```python
class FastAPI(Starlette):
    def __init__(
        self,
        *,
        debug: bool = False,
        routes: Optional[List[BaseRoute]] = None,
        title: str = "FastAPI",
        summary: Optional[str] = None,
        description: str = "",
        version: str = "0.1.0",
        openapi_url: Optional[str] = "/openapi.json",
        openapi_tags: Optional[List[Dict[str, Any]]] = None,
        servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
        dependencies: Optional[Sequence[Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        redirect_slashes: bool = True,
        docs_url: Optional[str] = "/docs",
        redoc_url: Optional[str] = "/redoc",
        swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
        swagger_ui_init_oauth: Optional[Dict[str, Any]] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], Callable]] = None,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,  # Deprecated
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,  # Deprecated
        lifespan: Optional[Lifespan[AppType]] = None,
        terms_of_service: Optional[str] = None,
        contact: Optional[Dict[str, Union[str, Any]]] = None,
        license_info: Optional[Dict[str, Union[str, Any]]] = None,
        openapi_prefix: str = "",  # Deprecated
        root_path: str = "",
        root_path_in_servers: bool = True,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        webhooks: Optional[routing.APIRouter] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        swagger_ui_parameters: Optional[Dict[str, Any]] = None,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
        separate_input_output_schemas: bool = True,
        **extra: Any,
    ) -> None:
```

### 2. 初始化步骤

#### 步骤 1：核心状态初始化
```python
# 存储配置参数
self.title = title
self.summary = summary  
self.description = description
self.version = version
self.openapi_url = openapi_url
self.openapi_tags = openapi_tags or []
self.openapi_schema: Optional[Dict[str, Any]] = None
```

#### 步骤 2：路由器设置
```python
# 创建主 API 路由器
self.router: routing.APIRouter = routing.APIRouter(
    routes=routes,
    redirect_slashes=redirect_slashes,
    default=default_response_class,
    on_startup=on_startup,
    on_shutdown=on_shutdown,
    lifespan=lifespan,
    default_response_class=default_response_class,
    dependencies=dependencies,
    callbacks=callbacks,
    deprecated=deprecated,
    include_in_schema=include_in_schema,
    responses=responses,
    generate_unique_id_function=generate_unique_id_function,
)
```

#### 步骤 3：状态和中间件初始化
```python
# 应用状态容器
self.state: State = State()

# 存储用户定义的中间件
self.user_middleware: List[Middleware] = (
    [] if middleware is None else list(middleware)
)

# 中间件栈（稍后构建）
self.middleware_stack: Union[ASGIApp, None] = None
```

#### 步骤 4：文档和 API 设置
```python
# 调用 setup 配置文档路由
self.setup()
```

### 3. Setup 方法深入分析

`setup()` 方法对于配置自动 API 文档至关重要：

```python
def setup(self) -> None:
    if self.openapi_url:
        # 创建 OpenAPI 模式端点
        async def openapi(req: Request) -> JSONResponse:
            root_path = req.scope.get("root_path", "").rstrip("/")
            if root_path not in server_urls:
                if root_path and self.root_path_in_servers:
                    self.servers.insert(0, {"url": root_path})
                    server_urls.add(root_path)
            return JSONResponse(self.openapi())
        
        # 添加 OpenAPI 路由
        self.add_route(self.openapi_url, openapi, include_in_schema=False)
    
    # 设置 Swagger UI 文档
    if self.openapi_url and self.docs_url:
        async def swagger_ui_html(req: Request) -> HTMLResponse:
            # 生成 Swagger UI HTML 响应
            # ...
        self.add_route(self.docs_url, swagger_ui_html, include_in_schema=False)
    
    # 设置 ReDoc 文档
    if self.openapi_url and self.redoc_url:
        async def redoc_html(req: Request) -> HTMLResponse:
            # 生成 ReDoc HTML 响应
            # ...
        self.add_route(self.redoc_url, redoc_html, include_in_schema=False)
```

## 生命周期管理

### 现代生命周期模式

FastAPI 使用现代生命周期模式来处理启动和关闭事件：

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    print("Starting up...")
    database.connect()
    yield
    # 关闭逻辑
    print("Shutting down...")
    database.disconnect()

app = FastAPI(lifespan=lifespan)
```

### 传统事件处理器（已弃用）

```python
# 已弃用的方法
async def startup_handler():
    database.connect()

async def shutdown_handler():
    database.disconnect()

app = FastAPI(
    on_startup=[startup_handler],
    on_shutdown=[shutdown_handler]
)
```

## 中间件栈构建

### 中间件处理顺序

FastAPI 按以下顺序处理中间件：

1. **异常处理中间件** - 处理 HTTP 异常
2. **CORS 中间件** - 跨源资源共享
3. **自定义用户中间件** - 用户定义的中间件
4. **路由中间件** - 路由解析和处理

### 中间件集成

```python
# 在 ASGI 应用构建期间
def build_middleware_stack(self) -> ASGIApp:
    middleware_stack = self.router
    
    # 以相反顺序添加用户中间件
    for middleware in reversed(self.user_middleware):
        middleware_stack = middleware.cls(
            middleware_stack,
            **middleware.options
        )
    
    # 添加异常处理器
    if self.exception_handlers:
        middleware_stack = ExceptionMiddleware(
            middleware_stack,
            handlers=self.exception_handlers
        )
    
    return middleware_stack
```

## 请求处理流程

### 1. ASGI 应用入口点

```python
async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
    if self.middleware_stack is None:
        self.middleware_stack = self.build_middleware_stack()
    await self.middleware_stack(scope, receive, send)
```

### 2. 路由解析过程

1. **路径匹配**：路由器将传入请求路径与注册路由进行匹配
2. **方法验证**：对照路由配置验证 HTTP 方法
3. **参数提取**：提取路径、查询参数、请求头和 cookie 参数
4. **依赖解析**：解析并注入依赖项
5. **端点执行**：执行路由处理函数

### 3. 响应生成

1. **返回值处理**：处理处理程序返回值
2. **响应模型验证**：如果指定，根据响应模型验证响应
3. **序列化**：将响应数据序列化为 JSON（或其他格式）
4. **HTTP 响应构建**：构建最终的 HTTP 响应

## 性能特征

### 延迟初始化

FastAPI 使用延迟初始化模式以获得最佳性能：

- **OpenAPI 模式**：在首次请求 `/openapi.json` 时生成
- **中间件栈**：在首次 ASGI 调用时构建
- **路由编译**：路由在首次访问时编译

### 内存管理

```python
class FastAPI(Starlette):
    def __init__(self, ...):
        # 高效的属性存储
        self.__dict__.update({
            'title': title,
            'version': version,
            'openapi_schema': None,  # 延迟加载
            'middleware_stack': None,  # 延迟构建
        })
```

### 缓存策略

- **OpenAPI 模式**：首次生成后缓存
- **路由匹配**：使用编译的正则表达式模式进行快速匹配
- **依赖解析**：每个端点的依赖关系图都被缓存

## 初始化期间的错误处理

### 配置验证

FastAPI 在初始化期间验证配置参数：

```python
def __init__(self, ...):
    # 验证 URL 模式
    if openapi_url and not openapi_url.startswith('/'):
        raise ValueError("openapi_url must start with '/'")
    
    # 验证响应类
    if not issubclass(default_response_class, Response):
        raise TypeError("default_response_class must inherit from Response")
```

### 运行时错误处理

```python
# 内置异常处理器
exception_handlers = {
    HTTPException: http_exception_handler,
    RequestValidationError: request_validation_exception_handler,
    WebSocketRequestValidationError: websocket_request_validation_exception_handler,
}
```

## 集成点

### Starlette 集成

FastAPI 扩展了 Starlette 的功能：

```python
class FastAPI(Starlette):
    def __init__(self, ...):
        # 初始化父 Starlette 应用
        super().__init__(
            debug=debug,
            routes=routes,
            middleware=middleware,
            exception_handlers=exception_handlers,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
        )
```

### ASGI 兼容性

FastAPI 保持完全的 ASGI 兼容性：

- **Scope、Receive、Send**：标准 ASGI 接口
- **中间件协议**：与 ASGI 中间件兼容
- **服务器集成**：与 Uvicorn、Gunicorn、Hypercorn 等配合使用

## 最佳实践

### 1. 生命周期管理
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 将相关的启动任务分组
    await database.connect()
    await cache.connect()
    yield
    # 优雅关闭
    await cache.disconnect()
    await database.disconnect()
```

### 2. 配置管理
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My API"
    debug: bool = False
    database_url: str

settings = Settings()
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)
```

### 3. 模块化组织
```python
# main.py
from fastapi import FastAPI
from .routers import users, items

app = FastAPI()
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(items.router, prefix="/items", tags=["items"])
```

## 下一章节

继续阅读[路由系统](./03-routing-system.md)以了解 FastAPI 如何处理路由注册和请求路由。