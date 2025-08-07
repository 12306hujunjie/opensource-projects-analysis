# FastAPI 路由系统

## 简介

FastAPI 的路由系统构建在 Starlette 路由功能之上，增强了自动验证、依赖注入和 OpenAPI 模式生成功能。本文档全面分析了路由如何注册、匹配和执行。

## 核心组件

### 1. APIRouter 类

`APIRouter` 是以模块化方式组织路由的核心组件：

```python
class APIRouter(routing.Router):
    def __init__(
        self,
        *,
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        routes: Optional[List[BaseRoute]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        dependency_overrides_provider: Optional[Any] = None,
        route_class: Type[APIRoute] = APIRoute,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,  # Deprecated
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,  # Deprecated
        lifespan: Optional[Lifespan] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
    ) -> None:
```

#### 主要职责：
- **路由组织**：将相关端点组合在一起
- **前缀管理**：为所有包含的路由应用路径前缀
- **标签分配**：应用 OpenAPI 标签进行文档分组
- **依赖共享**：在路由间应用通用依赖项
- **中间件集成**：与 FastAPI 的中间件系统集成

### 2. APIRoute 类

`APIRoute` 表示具有所有元数据和处理逻辑的单个端点：

```python
class APIRoute(routing.Route):
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        response_model: Any = Default(None),
        status_code: Optional[int] = None,
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        deprecated: Optional[bool] = None,
        name: Optional[str] = None,
        methods: Optional[Union[Set[str], List[str]]] = None,
        operation_id: Optional[str] = None,
        response_model_include: Optional[IncEx] = None,
        response_model_exclude: Optional[IncEx] = None,
        response_model_by_alias: bool = True,
        response_model_exclude_unset: bool = False,
        response_model_exclude_defaults: bool = False,
        response_model_exclude_none: bool = False,
        include_in_schema: bool = True,
        response_class: Union[Type[Response], DefaultPlaceholder] = Default(JSONResponse),
        dependency_overrides_provider: Optional[Any] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        openapi_extra: Optional[Dict[str, Any]] = None,
        generate_unique_id_function: Union[Callable[["APIRoute"], str], DefaultPlaceholder] = Default(generate_unique_id),
    ) -> None:
```

## 路由注册过程

### 1. 路径编译

在路由初始化期间，FastAPI 编译路径模式以实现高效匹配：

```python
# 在 APIRoute.__init__ 中
self.path_regex, self.path_format, self.param_convertors = compile_path(path)
```

路径编译过程：
- **正则表达式生成**：创建编译后的正则表达式进行快速路径匹配
- **参数提取**：识别路径参数及其类型
- **格式字符串**：创建用于 URL 生成的格式字符串

### 2. 依赖项分析

FastAPI 分析端点函数以提取依赖项：

```python
# 在 APIRoute.__init__ 中
self.dependant = get_dependant(path=self.path_format, call=self.endpoint)
for depends in self.dependencies[::-1]:
    self.dependant.dependencies.insert(
        0,
        get_parameterless_sub_dependant(depends=depends, path=self.path_format),
    )
```

`get_dependant` 函数：
- **函数签名分析**：检查端点函数签名
- **参数分类**：对参数进行分类（路径、查询、正文等）
- **依赖关系图构建**：构造依赖解析图
- **验证规则设置**：为每个参数设置 Pydantic 验证

### 3. 响应模型设置

如果指定了响应模型，FastAPI 会创建验证字段：

```python
if self.response_model:
    response_name = "Response_" + self.unique_id
    self.response_field = create_model_field(
        name=response_name,
        type_=self.response_model,
        mode="serialization",
    )
```

## 请求处理管道

### 1. 路由匹配

当请求到达时，FastAPI 使用 Starlette 的路由匹配：

```python
def matches(self, scope: Scope) -> Tuple[Match, Scope]:
    match, child_scope = super().matches(scope)
    if match != Match.NONE:
        child_scope["route"] = self
    return match, child_scope
```

匹配过程：
- **路径模式匹配**：使用编译的正则表达式匹配请求路径
- **方法验证**：检查是否支持 HTTP 方法
- **作用域增强**：向 ASGI 作用域添加路由信息

### 2. 请求处理程序执行

核心请求处理发生在 `app` 方法中：

```python
async def app(request: Request) -> Response:
    response: Union[Response, None] = None
    async with AsyncExitStack() as file_stack:
        try:
            # 1. 正文解析
            body: Any = None
            if body_field:
                if is_body_form:
                    body = await request.form()
                    file_stack.push_async_callback(body.close)
                else:
                    body_bytes = await request.body()
                    # JSON 解析逻辑...
            
            # 2. 依赖项解析
            async with AsyncExitStack() as async_exit_stack:
                solved_result = await solve_dependencies(
                    request=request,
                    dependant=dependant,
                    body=body,
                    dependency_overrides_provider=dependency_overrides_provider,
                    async_exit_stack=async_exit_stack,
                    embed_body_fields=embed_body_fields,
                )
                
                # 3. 端点执行
                if not solved_result.errors:
                    raw_response = await run_endpoint_function(
                        dependant=dependant,
                        values=solved_result.values,
                        is_coroutine=is_coroutine,
                    )
                    
                    # 4. 响应处理
                    if isinstance(raw_response, Response):
                        response = raw_response
                    else:
                        # 响应模型序列化...
                        response = response_class(
                            content=actual_response_content,
                            status_code=current_status_code,
                            **response_args,
                        )
```

### 3. 正文解析策略

FastAPI 根据内容类型智能解析请求正文：

```python
# JSON 正文解析
content_type_value = request.headers.get("content-type")
if not content_type_value:
    json_body = await request.json()
else:
    message = email.message.Message()
    message["content-type"] = content_type_value
    if message.get_content_maintype() == "application":
        subtype = message.get_content_subtype()
        if subtype == "json" or subtype.endswith("+json"):
            json_body = await request.json()
```

支持的正文类型：
- **JSON**：`application/json` 和变体（例如 `application/vnd.api+json`）
- **表单数据**：`application/x-www-form-urlencoded`
- **多部分**：`multipart/form-data`
- **原始字节**：任何其他内容类型

## 依赖解析系统

### 1. 依赖关系图构建

FastAPI 在路由初始化期间构建依赖关系图：

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
```

### 2. 依赖解析过程

`solve_dependencies` 函数解析整个依赖关系图：

1. **参数提取**：从请求路径、查询参数、请求头、cookies 中提取值
2. **正文验证**：根据 Pydantic 模型验证请求正文
3. **依赖注入**：递归解析子依赖项
4. **缓存**：为标记了 `use_cache=True` 的依赖项应用缓存
5. **错误聚合**：从所有参数收集验证错误

### 3. 子依赖解析

依赖项可以有自己的依赖项，形成解析链：

```python
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(get_token), db: Session = Depends(get_db)):
    # 首先解析 get_token 和 get_db
    return authenticate_user(db, token)

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    # 所有依赖项都被解析：get_token -> get_db -> get_current_user
    return current_user
```

## 路由器层次结构和包含

### 1. 路由器嵌套

APIRouter 可以嵌套以创建分层路由组织：

```python
# users/router.py
users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.get("/")
async def read_users(): ...

@users_router.get("/{user_id}")
async def read_user(user_id: int): ...

# admin/router.py  
admin_router = APIRouter(prefix="/admin", tags=["admin"])
admin_router.include_router(users_router, prefix="/users")  # /admin/users

# main.py
app = FastAPI()
app.include_router(users_router)  # /users
app.include_router(admin_router)  # /admin
```

### 2. 路由继承

在包含路由器时，FastAPI 继承和组合配置：

```python
def include_router(
    self,
    router: "APIRouter",
    *,
    prefix: str = "",
    tags: Optional[List[Union[str, Enum]]] = None,
    dependencies: Optional[Sequence[Depends]] = None,
    default_response_class: Type[Response] = Default(JSONResponse),
    responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
    callbacks: Optional[List[BaseRoute]] = None,
    deprecated: Optional[bool] = None,
    include_in_schema: bool = True,
    generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
) -> None:
```

配置继承规则：
- **前缀连接**：父前缀 + 路由器前缀 + 路由路径
- **标签合并**：父标签 + 路由器标签  
- **依赖链接**：父依赖项 + 路由器依赖项 + 路由依赖项
- **响应类覆盖**：最具体的响应类获胜

## 路由匹配算法

### 1. 路径模式编译

FastAPI 使用 Starlette 的路径编译进行高效匹配：

```python
def compile_path(path: str) -> Tuple[Pattern[str], str, Dict[str, Convertor]]:
    """
    给定路径字符串，返回：
    * 用于匹配的编译正则表达式
    * 用于 URL 生成的格式字符串
    * 路径参数的转换器字典
    """
```

### 2. 参数转换器

路径参数使用特定类型的转换器进行转换：

```python
convertors = {
    "str": StringConvertor(),
    "path": PathConvertor(),
    "int": IntegerConvertor(),
    "float": FloatConvertor(),
    "uuid": UUIDConvertor(),
}
```

路径模式示例：
- `/users/{user_id:int}` → 转换为整数
- `/files/{file_path:path}` → 捕获包括斜杠在内的完整路径  
- `/items/{item_id:uuid}` → 验证 UUID 格式

### 3. 路由优先级

路由按注册顺序匹配：
- **精确匹配**优先于参数匹配
- **具体模式**应在通用模式之前注册
- **方法特定路由**在通用路由之前检查

## 性能优化

### 1. 路由编译

- **正则表达式缓存**：编译的模式被缓存以进行快速匹配
- **参数提取**：从 URL 路径优化参数提取
- **方法集查找**：使用集合进行 O(1) HTTP 方法验证

### 2. 依赖缓存

标记为 `use_cache=True` 的依赖项在请求处理期间被缓存：

```python
@lru_cache()
def expensive_dependency():
    # 此计算在每个请求中被缓存
    return compute_expensive_data()

@app.get("/endpoint1")
async def endpoint1(data = Depends(expensive_dependency)):
    return data  # 使用缓存结果

@app.get("/endpoint2") 
async def endpoint2(data = Depends(expensive_dependency)):
    return data  # 使用相同的缓存结果
```

### 3. 响应模型优化

- **字段克隆**：响应字段被克隆以防止继承问题
- **序列化模式**：针对 JSON 序列化进行优化
- **排除策略**：序列化期间高效的字段排除

## 路由中的错误处理

### 1. 验证错误

FastAPI 从所有来源收集和格式化验证错误：

```python
# 验证错误响应示例
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

### 2. 路由解析错误

- **404 未找到**：没有匹配的路由模式
- **405 方法不被允许**：路由存在但不支持 HTTP 方法
- **422 无法处理的实体**：路由匹配但验证失败

### 3. 自定义异常处理器

路由可以定义自定义异常处理器：

```python
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"message": f"Value error: {exc}"}
    )
```

## WebSocket 路由

FastAPI 还通过 `APIWebSocketRoute` 支持 WebSocket 路由：

```python
class APIWebSocketRoute(routing.WebSocketRoute):
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        name: Optional[str] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        dependency_overrides_provider: Optional[Any] = None,
    ) -> None:
```

WebSocket 特定功能：
- **连接管理**：自动连接处理
- **依赖注入**：WebSocket 端点的完整依赖支持
- **参数提取**：从 WebSocket URL 提取路径和查询参数

## 最佳实践

### 1. 路由组织

```python
# 好的：按领域组织
users_router = APIRouter(prefix="/users", tags=["users"])
posts_router = APIRouter(prefix="/posts", tags=["posts"])

# 好的：分层组织
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(users_router)
api_v1.include_router(posts_router)
```

### 2. 依赖管理

```python
# 好的：在路由器级别共享依赖项
router = APIRouter(dependencies=[Depends(verify_token)])

# 好的：逻辑性地分层依赖项
@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_user),  # 使用 verify_token
    db: Session = Depends(get_db)
):
    return {"user": current_user.name}
```

### 3. 响应模型设计

```python
# 好的：特定的响应模型
class UserResponse(BaseModel):
    id: int
    name: str
    email: str

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int

@router.get("/", response_model=UserListResponse)
async def list_users(): ...
```

## 下一章节

继续阅读[依赖注入系统](./04-dependency-injection.md)以了解 FastAPI 的高级依赖解析和缓存机制。