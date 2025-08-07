# FastAPI 架构概述

## 简介

FastAPI 是一个现代化、高性能的 Web 框架，用于基于 Python 3.7+ 构建 API。它建立在几项关键技术和设计模式的基础上，这些技术和模式协同工作，提供卓越的性能、类型安全性和开发体验。

## 核心架构组件

### 1. 基础架构：Starlette + ASGI

```python
# FastAPI 继承自 Starlette
class FastAPI(Starlette):
    def __init__(self, ...):
        # FastAPI 特定的初始化
        super().__init__(...)
```

FastAPI 构建在 **Starlette** 之上，Starlette 提供：
- **ASGI (异步服务器网关接口)** 兼容性
- 高性能 async/await 支持
- WebSocket 支持
- 后台任务执行
- 中间件系统
- HTTP 异常处理

### 2. 类型系统：Pydantic 集成

FastAPI 利用 **Pydantic** 实现：
- 使用 Python 类型提示进行**自动数据验证**
- **JSON 序列化/反序列化**
- 为 OpenAPI/Swagger 生成**模式**
- 提供详细验证消息的**错误处理**

```python
from pydantic import BaseModel

class UserModel(BaseModel):
    id: int
    name: str
    email: str
```

### 3. 依赖注入系统

FastAPI 通过 `Dependant` 数据类实现了复杂的依赖注入系统：

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
    # ... 更多字段用于缓存、安全等
```

### 4. 路由架构

FastAPI 使用分层路由系统：

- **APIRouter**: 分组相关路由，支持嵌套
- **APIRoute**: 具有端点、参数和元数据的单个路由
- **路由解析**: 模式匹配和参数提取

```python
class APIRouter(routing.Router):
    """为模块化应用结构分组路径操作"""
    
class APIRoute(routing.Route):
    """具有 FastAPI 特定功能的单个路由"""
```

## 关键设计模式

### 1. 用于路由注册的装饰器模式

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int) -> UserModel:
    return await user_service.get_user(user_id)
```

### 2. 依赖注入模式

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/")
async def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

### 3. 中间件模式

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 请求/响应生命周期

### 1. 请求接收
- **ASGI 服务器**接收 HTTP 请求
- **Starlette** 创建 Request 对象
- **FastAPI** 开始路由解析

### 2. 路由匹配
- 对注册路由进行**路径匹配**
- 从路径、查询参数、请求头中**提取参数**
- 基于 HTTP 方法和路径进行**路由选择**

### 3. 依赖解析
- 从函数签名构建**依赖关系图**
- 支持缓存的**依赖注入**
- 使用 Pydantic 模型进行**参数验证**

### 4. 端点执行
- 使用已解析依赖项进行**函数调用**
- 自动使用线程池的**异步/同步处理**
- 提供自定义错误响应的**异常处理**

### 5. 响应生成
- **响应模型验证**（如果指定）
- 使用 FastAPI 编码器进行 **JSON 序列化**
- 为文档生成 **OpenAPI 模式**

## 性能特征

### 异步优先设计
- 整个堆栈的**原生 async/await** 支持
- 为阻塞代码提供**自动同步到异步**转换
- 使用 asyncio 事件循环进行**高效 I/O 处理**

### 优化措施
- **依赖缓存**避免冗余计算
- **路由编译**实现快速路径匹配
- 相对于 Starlette 性能的**最小开销**

### 基准测试
FastAPI 实现了与 Node.js 和 Go 框架相当的性能：
- **高吞吐量**：每秒 60,000+ 个请求
- **低延迟**：毫秒级以下响应时间
- **内存效率**：为并发连接优化

## 安全集成

### 内置安全方案
- **带 JWT 令牌的 OAuth2**
- **API 密钥认证**（请求头、查询参数、Cookie）
- **HTTP Basic/Digest 认证**
- **OpenID Connect 集成**

### 安全架构
```python
@dataclass
class SecurityRequirement:
    security_scheme: SecurityBase
    scopes: Optional[Sequence[str]] = None
```

## 下一步

以下章节提供每个架构组件的详细分析：

1. **[应用生命周期](./02-application-lifecycle.md)** - FastAPI 应用初始化和配置
2. **[路由系统](./03-routing-system.md)** - 路由注册、匹配和参数处理
3. **[依赖注入](./04-dependency-injection.md)** - 高级依赖模式和缓存
4. **[请求处理](./05-request-processing.md)** - 完整的请求处理管道
5. **[响应生成](./06-response-generation.md)** - 响应序列化和验证
6. **[OpenAPI 集成](./07-openapi-integration.md)** - 自动 API 文档生成