# Starlette 完整代码示例与实践指南

## 概述

本文档提供了 Starlette 框架的完整代码示例，涵盖从基础用法到高级特性的各种使用场景。通过这些实际可运行的示例，您可以快速理解 Starlette 的核心概念和实践模式。

## 1. 基础 Hello World 应用

### 1.1 最简单的 Starlette 应用

```python
# app.py
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

async def homepage(request):
    return JSONResponse({'message': 'Hello, Starlette!'})

# 定义路由
routes = [
    Route('/', homepage, methods=['GET']),
]

# 创建应用实例
app = Starlette(routes=routes)

# 运行方式：uvicorn app:app --reload
```

### 1.2 带调试模式的应用

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

async def homepage(request):
    return JSONResponse({
        'message': 'Hello, Starlette!',
        'method': request.method,
        'url': str(request.url)
    })

async def error_endpoint(request):
    # 故意抛出异常来测试调试模式
    raise ValueError("这是一个测试异常")

routes = [
    Route('/', homepage),
    Route('/error', error_endpoint),
]

# 启用调试模式
app = Starlette(debug=True, routes=routes)
```

## 2. 路由系统示例

### 2.1 不同类型的路由

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route, WebSocketRoute, Mount
from starlette.websockets import WebSocket
import json

# HTTP 路由处理器
async def get_user(request):
    user_id = request.path_params['user_id']
    return JSONResponse({'user_id': user_id, 'name': f'User {user_id}'})

async def create_user(request):
    data = await request.json()
    return JSONResponse({'message': '用户创建成功', 'data': data}, status_code=201)

async def update_user(request):
    user_id = request.path_params['user_id']
    data = await request.json()
    return JSONResponse({'user_id': user_id, 'updated_data': data})

async def delete_user(request):
    user_id = request.path_params['user_id']
    return JSONResponse({'message': f'用户 {user_id} 已删除'})

# WebSocket 处理器
async def websocket_endpoint(websocket):
    await websocket.accept()
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 回显消息
            response = {
                'type': 'echo',
                'original': message,
                'timestamp': str(datetime.now())
            }
            
            await websocket.send_text(json.dumps(response))
            
    except Exception as e:
        print(f"WebSocket 连接错误: {e}")
    finally:
        await websocket.close()

# 子应用
from starlette.applications import Starlette as SubApp
from starlette.routing import Route as SubRoute

async def api_v2_info(request):
    return JSONResponse({'version': 'v2', 'status': 'active'})

api_v2 = SubApp(routes=[
    SubRoute('/', api_v2_info),
])

# 主路由配置
routes = [
    # HTTP 路由
    Route('/users/{user_id:int}', get_user, methods=['GET']),
    Route('/users', create_user, methods=['POST']),
    Route('/users/{user_id:int}', update_user, methods=['PUT']),
    Route('/users/{user_id:int}', delete_user, methods=['DELETE']),
    
    # WebSocket 路由
    WebSocketRoute('/ws', websocket_endpoint),
    
    # 挂载子应用
    Mount('/api/v2', api_v2),
]

app = Starlette(routes=routes)
```

### 2.2 路径参数和类型转换

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uuid
from datetime import datetime

async def string_param(request):
    name = request.path_params['name']
    return JSONResponse({'param_type': 'string', 'name': name})

async def int_param(request):
    user_id = request.path_params['user_id']
    return JSONResponse({'param_type': 'int', 'user_id': user_id, 'type': str(type(user_id))})

async def float_param(request):
    price = request.path_params['price']
    return JSONResponse({'param_type': 'float', 'price': price, 'type': str(type(price))})

async def uuid_param(request):
    item_id = request.path_params['item_id']
    return JSONResponse({'param_type': 'uuid', 'item_id': str(item_id), 'type': str(type(item_id))})

async def path_param(request):
    file_path = request.path_params['file_path']
    return JSONResponse({'param_type': 'path', 'file_path': file_path})

async def multiple_params(request):
    return JSONResponse({
        'user_id': request.path_params['user_id'],
        'category': request.path_params['category'],
        'item_name': request.path_params['item_name']
    })

routes = [
    Route('/string/{name}', string_param),
    Route('/int/{user_id:int}', int_param),
    Route('/float/{price:float}', float_param),
    Route('/uuid/{item_id:uuid}', uuid_param),
    Route('/path/{file_path:path}', path_param),
    Route('/users/{user_id:int}/categories/{category}/items/{item_name}', multiple_params),
]

app = Starlette(routes=routes)
```

## 3. 请求处理示例

### 3.1 处理不同类型的请求数据

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
import json

async def handle_query_params(request: Request):
    """处理查询参数"""
    query_params = dict(request.query_params)
    return JSONResponse({
        'query_params': query_params,
        'page': request.query_params.get('page', '1'),
        'limit': request.query_params.get('limit', '10')
    })

async def handle_headers(request: Request):
    """处理请求头"""
    headers = dict(request.headers)
    return JSONResponse({
        'all_headers': headers,
        'user_agent': request.headers.get('user-agent'),
        'content_type': request.headers.get('content-type'),
        'authorization': request.headers.get('authorization', 'Not provided')
    })

async def handle_json(request: Request):
    """处理 JSON 数据"""
    try:
        data = await request.json()
        return JSONResponse({
            'received_data': data,
            'data_type': type(data).__name__,
            'message': 'JSON 数据接收成功'
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=400)

async def handle_form_data(request: Request):
    """处理表单数据"""
    try:
        form = await request.form()
        form_data = {}
        
        for key, value in form.items():
            if hasattr(value, 'filename'):  # 文件上传
                form_data[key] = {
                    'filename': value.filename,
                    'content_type': value.content_type,
                    'size': len(await value.read())
                }
            else:  # 普通表单字段
                form_data[key] = value
        
        return JSONResponse({
            'form_data': form_data,
            'message': '表单数据接收成功'
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=400)

async def handle_raw_body(request: Request):
    """处理原始请求体"""
    body = await request.body()
    return JSONResponse({
        'body_size': len(body),
        'body_preview': body[:100].decode('utf-8', errors='ignore'),
        'content_type': request.headers.get('content-type')
    })

async def handle_stream(request: Request):
    """处理流式数据"""
    chunks = []
    async for chunk in request.stream():
        chunks.append(len(chunk))
    
    return JSONResponse({
        'total_chunks': len(chunks),
        'chunk_sizes': chunks,
        'total_size': sum(chunks)
    })

async def handle_cookies(request: Request):
    """处理 Cookie"""
    cookies = dict(request.cookies)
    return JSONResponse({
        'all_cookies': cookies,
        'session_id': request.cookies.get('session_id', 'Not found')
    })

routes = [
    Route('/query', handle_query_params, methods=['GET']),
    Route('/headers', handle_headers, methods=['GET', 'POST']),
    Route('/json', handle_json, methods=['POST']),
    Route('/form', handle_form_data, methods=['POST']),
    Route('/raw', handle_raw_body, methods=['POST']),
    Route('/stream', handle_stream, methods=['POST']),
    Route('/cookies', handle_cookies, methods=['GET']),
]

app = Starlette(routes=routes)
```

### 3.2 文件上传处理

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
import os
import uuid
from pathlib import Path

# 确保上传目录存在
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

async def upload_single_file(request: Request):
    """单文件上传"""
    try:
        form = await request.form()
        upload_file = form.get("file")
        
        if not upload_file or not upload_file.filename:
            return JSONResponse({"error": "没有选择文件"}, status_code=400)
        
        # 生成唯一文件名
        file_extension = Path(upload_file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # 保存文件
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)
        
        return JSONResponse({
            "message": "文件上传成功",
            "original_filename": upload_file.filename,
            "saved_filename": unique_filename,
            "file_size": len(content),
            "content_type": upload_file.content_type
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def upload_multiple_files(request: Request):
    """多文件上传"""
    try:
        form = await request.form()
        uploaded_files = []
        
        for key, value in form.items():
            if hasattr(value, 'filename') and value.filename:
                # 生成唯一文件名
                file_extension = Path(value.filename).suffix
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = UPLOAD_DIR / unique_filename
                
                # 保存文件
                content = await value.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                
                uploaded_files.append({
                    "field_name": key,
                    "original_filename": value.filename,
                    "saved_filename": unique_filename,
                    "file_size": len(content),
                    "content_type": value.content_type
                })
        
        return JSONResponse({
            "message": f"成功上传 {len(uploaded_files)} 个文件",
            "files": uploaded_files
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

routes = [
    Route('/upload/single', upload_single_file, methods=['POST']),
    Route('/upload/multiple', upload_multiple_files, methods=['POST']),
]

app = Starlette(routes=routes)
```

## 4. 响应处理示例

### 4.1 不同类型的响应

```python
from starlette.applications import Starlette
from starlette.responses import (
    JSONResponse, PlainTextResponse, HTMLResponse, 
    RedirectResponse, StreamingResponse, FileResponse
)
from starlette.routing import Route
import json
import io
from datetime import datetime

async def json_response(request):
    """JSON 响应"""
    data = {
        "message": "这是一个 JSON 响应",
        "timestamp": datetime.now().isoformat(),
        "request_method": request.method,
        "client_ip": request.client.host if request.client else "unknown"
    }
    return JSONResponse(data)

async def text_response(request):
    """纯文本响应"""
    text_content = f"""
这是一个纯文本响应

请求信息：
- 方法: {request.method}
- 路径: {request.url.path}
- 时间: {datetime.now()}
    """
    return PlainTextResponse(text_content)

async def html_response(request):
    """HTML 响应"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Starlette HTML Response</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .info {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Starlette HTML 响应示例</h1>
        <div class="info">
            <p><strong>请求方法:</strong> {request.method}</p>
            <p><strong>请求路径:</strong> {request.url.path}</p>
            <p><strong>时间:</strong> {datetime.now()}</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

async def redirect_response(request):
    """重定向响应"""
    return RedirectResponse(url="/json", status_code=302)

async def custom_headers_response(request):
    """自定义响应头"""
    headers = {
        "X-Custom-Header": "Custom Value",
        "X-Request-ID": "12345",
        "Cache-Control": "no-cache, no-store, must-revalidate"
    }
    
    data = {"message": "带自定义响应头的 JSON 响应"}
    return JSONResponse(data, headers=headers)

async def status_code_response(request):
    """自定义状态码"""
    status_code = int(request.path_params.get('status_code', 200))
    
    data = {
        "status_code": status_code,
        "message": f"这是一个 {status_code} 状态码的响应"
    }
    
    return JSONResponse(data, status_code=status_code)

async def streaming_response(request):
    """流式响应"""
    async def generate_data():
        for i in range(10):
            data = {"chunk": i, "timestamp": datetime.now().isoformat()}
            yield f"data: {json.dumps(data)}\n\n"
            # 模拟异步处理延迟
            import asyncio
            await asyncio.sleep(0.5)
    
    return StreamingResponse(
        generate_data(),
        media_type="text/plain",
        headers={"X-Stream-Type": "generated-data"}
    )

# 需要一个测试文件用于文件响应
async def create_test_file():
    """创建测试文件"""
    test_file_path = "test_file.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("这是一个测试文件，用于演示 FileResponse。\n")
        f.write(f"创建时间: {datetime.now()}\n")
    return test_file_path

async def file_response(request):
    """文件响应"""
    import os
    test_file = "test_file.txt"
    
    if not os.path.exists(test_file):
        await create_test_file()
    
    return FileResponse(
        test_file,
        filename="download_file.txt",
        headers={"X-File-Type": "text-file"}
    )

routes = [
    Route('/json', json_response),
    Route('/text', text_response),
    Route('/html', html_response),
    Route('/redirect', redirect_response),
    Route('/headers', custom_headers_response),
    Route('/status/{status_code:int}', status_code_response),
    Route('/stream', streaming_response),
    Route('/file', file_response),
]

app = Starlette(routes=routes)
```

## 5. 中间件示例

### 5.1 自定义中间件

```python
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.requests import Request
import time
import logging
import json
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimingMiddleware(BaseHTTPMiddleware):
    """请求计时中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 记录请求信息
        logger.info(f"{request.method} {request.url.path} - Client: {request.client}")
        
        try:
            response = await call_next(request)
            logger.info(f"Response: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            raise

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """简单的认证中间件"""
    
    def __init__(self, app, secret_token: str = "secret-token"):
        super().__init__(app)
        self.secret_token = secret_token
    
    async def dispatch(self, request: Request, call_next):
        # 跳过认证的路径
        if request.url.path in ["/", "/health", "/public"]:
            return await call_next(request)
        
        # 检查认证头
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid authorization header"},
                status_code=401
            )
        
        token = authorization.split(" ")[1]
        if token != self.secret_token:
            return JSONResponse(
                {"error": "Invalid token"},
                status_code=401
            )
        
        # 将用户信息添加到请求状态
        request.state.user = {"id": 1, "name": "test_user"}
        
        return await call_next(request)

class CORSMiddleware(BaseHTTPMiddleware):
    """CORS 中间件"""
    
    def __init__(self, app, allow_origins=None, allow_methods=None, allow_headers=None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
    
    async def dispatch(self, request: Request, call_next):
        # 处理预检请求
        if request.method == "OPTIONS":
            response = PlainTextResponse("", status_code=200)
        else:
            response = await call_next(request)
        
        # 添加 CORS 头
        response.headers["Access-Control-Allow-Origin"] = ", ".join(self.allow_origins)
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        
        return response

# 路由处理器
async def public_endpoint(request):
    return JSONResponse({"message": "这是一个公开端点", "timestamp": datetime.now().isoformat()})

async def protected_endpoint(request):
    user = request.state.user
    return JSONResponse({
        "message": "这是一个受保护的端点",
        "user": user,
        "timestamp": datetime.now().isoformat()
    })

async def health_check(request):
    return JSONResponse({"status": "healthy", "timestamp": datetime.now().isoformat()})

routes = [
    Route("/", public_endpoint),
    Route("/public", public_endpoint),
    Route("/protected", protected_endpoint),
    Route("/health", health_check),
]

# 创建应用并添加中间件
app = Starlette(routes=routes)

# 添加中间件（注意顺序：从外到内）
app.add_middleware(CORSMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthenticationMiddleware, secret_token="my-secret-token")
```

### 5.2 内置中间件使用

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

async def data_endpoint(request):
    # 生成一些大的数据用于测试压缩
    large_data = {
        "message": "这是一个包含大量数据的响应，用于测试 Gzip 压缩" * 100,
        "numbers": list(range(1000)),
        "items": [{"id": i, "value": f"item_{i}"} for i in range(100)]
    }
    return JSONResponse(large_data)

async def secure_endpoint(request):
    return JSONResponse({
        "message": "这是一个安全端点",
        "host": request.headers.get("host"),
        "scheme": request.url.scheme
    })

routes = [
    Route("/data", data_endpoint),
    Route("/secure", secure_endpoint),
]

# 使用 Middleware 对象定义中间件
middleware = [
    # Gzip 压缩中间件
    Middleware(GZipMiddleware, minimum_size=1000),
    
    # CORS 中间件
    Middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://example.com"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=True,
    ),
    
    # 可信主机中间件
    Middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
    ),
    
    # HTTPS 重定向中间件（生产环境使用）
    # Middleware(HTTPSRedirectMiddleware),
]

app = Starlette(routes=routes, middleware=middleware)
```

## 6. WebSocket 示例

### 6.1 基础 WebSocket 应用

```python
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime

# 存储连接的客户端
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"客户端已连接，总连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"客户端已断开连接，总连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # 连接可能已经关闭
                pass

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    """基础 WebSocket 端点"""
    await manager.connect(websocket)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 处理不同类型的消息
            message_type = message_data.get("type", "message")
            
            if message_type == "ping":
                # 心跳检测
                await manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                    websocket
                )
            
            elif message_type == "broadcast":
                # 广播消息给所有连接
                broadcast_data = {
                    "type": "broadcast",
                    "message": message_data.get("message", ""),
                    "timestamp": datetime.now().isoformat(),
                    "sender": f"Client-{id(websocket)}"
                }
                await manager.broadcast(json.dumps(broadcast_data))
            
            elif message_type == "echo":
                # 回显消息
                echo_data = {
                    "type": "echo",
                    "original": message_data,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(json.dumps(echo_data), websocket)
            
            else:
                # 默认处理
                response_data = {
                    "type": "response",
                    "received": message_data,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(json.dumps(response_data), websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # 通知其他客户端有人离开
        await manager.broadcast(json.dumps({
            "type": "notification",
            "message": f"客户端 {id(websocket)} 已断开连接",
            "timestamp": datetime.now().isoformat()
        }))

async def chat_room(websocket: WebSocket):
    """聊天室示例"""
    query_params = websocket.query_params
    username = query_params.get("username", f"Anonymous-{id(websocket)}")
    
    await manager.connect(websocket)
    
    # 通知其他用户有新用户加入
    await manager.broadcast(json.dumps({
        "type": "user_joined",
        "username": username,
        "message": f"{username} 加入了聊天室",
        "timestamp": datetime.now().isoformat()
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 广播聊天消息
            chat_message = {
                "type": "chat_message",
                "username": username,
                "message": message_data.get("message", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            await manager.broadcast(json.dumps(chat_message))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(json.dumps({
            "type": "user_left",
            "username": username,
            "message": f"{username} 离开了聊天室",
            "timestamp": datetime.now().isoformat()
        }))

# WebSocket 客户端测试页面
async def websocket_client_page(request):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Starlette WebSocket 测试</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .messages { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; margin: 10px 0; }
            .input-group { margin: 10px 0; }
            .input-group input, .input-group button { padding: 10px; margin: 5px; }
            .input-group input[type="text"] { width: 300px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WebSocket 测试客户端</h1>
            
            <div class="input-group">
                <input type="text" id="serverUrl" value="ws://localhost:8000/ws" placeholder="WebSocket URL">
                <button onclick="connect()">连接</button>
                <button onclick="disconnect()">断开</button>
            </div>
            
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="输入消息" onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()">发送消息</button>
                <button onclick="sendPing()">发送 Ping</button>
                <button onclick="sendBroadcast()">广播消息</button>
            </div>
            
            <div id="status">状态: 未连接</div>
            <div id="messages" class="messages"></div>
        </div>

        <script>
            let socket = null;
            const messages = document.getElementById('messages');
            const status = document.getElementById('status');
            
            function connect() {
                const url = document.getElementById('serverUrl').value;
                socket = new WebSocket(url);
                
                socket.onopen = function(event) {
                    status.textContent = '状态: 已连接';
                    addMessage('连接已建立');
                };
                
                socket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage('收到消息: ' + JSON.stringify(data, null, 2));
                };
                
                socket.onclose = function(event) {
                    status.textContent = '状态: 已断开';
                    addMessage('连接已关闭');
                };
                
                socket.onerror = function(error) {
                    status.textContent = '状态: 错误';
                    addMessage('错误: ' + error);
                };
            }
            
            function disconnect() {
                if (socket) {
                    socket.close();
                }
            }
            
            function sendMessage() {
                const input = document.getElementById('messageInput');
                if (socket && socket.readyState === WebSocket.OPEN && input.value) {
                    const message = {
                        type: 'echo',
                        message: input.value
                    };
                    socket.send(JSON.stringify(message));
                    addMessage('发送消息: ' + input.value);
                    input.value = '';
                }
            }
            
            function sendPing() {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({type: 'ping'}));
                    addMessage('发送 Ping');
                }
            }
            
            function sendBroadcast() {
                const input = document.getElementById('messageInput');
                if (socket && socket.readyState === WebSocket.OPEN && input.value) {
                    const message = {
                        type: 'broadcast',
                        message: input.value
                    };
                    socket.send(JSON.stringify(message));
                    addMessage('发送广播: ' + input.value);
                    input.value = '';
                }
            }
            
            function addMessage(message) {
                const div = document.createElement('div');
                div.textContent = new Date().toLocaleTimeString() + ' - ' + message;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

routes = [
    Route("/", websocket_client_page),
    WebSocketRoute("/ws", websocket_endpoint),
    WebSocketRoute("/chat", chat_room),
]

app = Starlette(routes=routes)
```

## 7. 异常处理示例

### 7.1 自定义异常处理

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.exceptions import HTTPException
from starlette.requests import Request
import traceback
from datetime import datetime

# 自定义异常类
class BusinessLogicError(Exception):
    """业务逻辑错误"""
    def __init__(self, message: str, error_code: str = "BUSINESS_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class ValidationError(Exception):
    """数据验证错误"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error in field '{field}': {message}")

# 异常处理器
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTP 异常"""
    return JSONResponse(
        {
            "error": "HTTP Exception",
            "status_code": exc.status_code,
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        },
        status_code=exc.status_code,
    )

async def business_exception_handler(request: Request, exc: BusinessLogicError):
    """处理业务逻辑异常"""
    return JSONResponse(
        {
            "error": "Business Logic Error",
            "error_code": exc.error_code,
            "message": exc.message,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        },
        status_code=400,
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """处理验证异常"""
    return JSONResponse(
        {
            "error": "Validation Error",
            "field": exc.field,
            "message": exc.message,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        },
        status_code=422,
    )

async def general_exception_handler(request: Request, exc: Exception):
    """处理一般异常"""
    return JSONResponse(
        {
            "error": "Internal Server Error",
            "type": type(exc).__name__,
            "message": str(exc),
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            # 只在调试模式下包含堆栈跟踪
            "traceback": traceback.format_exc() if app.debug else None
        },
        status_code=500,
    )

# 测试路由
async def success_endpoint(request):
    """正常端点"""
    return JSONResponse({"message": "操作成功", "status": "success"})

async def http_error_endpoint(request):
    """抛出 HTTP 异常"""
    raise HTTPException(status_code=404, detail="资源未找到")

async def business_error_endpoint(request):
    """抛出业务异常"""
    raise BusinessLogicError("用户余额不足", "INSUFFICIENT_BALANCE")

async def validation_error_endpoint(request):
    """抛出验证异常"""
    raise ValidationError("email", "邮箱格式不正确")

async def general_error_endpoint(request):
    """抛出一般异常"""
    # 模拟除零错误
    result = 1 / 0
    return JSONResponse({"result": result})

async def user_create_endpoint(request):
    """模拟用户创建端点，包含验证逻辑"""
    try:
        data = await request.json()
    except Exception:
        raise ValidationError("request_body", "无法解析 JSON 数据")
    
    # 验证必填字段
    if not data.get("email"):
        raise ValidationError("email", "邮箱是必填字段")
    
    if not data.get("password"):
        raise ValidationError("password", "密码是必填字段")
    
    # 验证邮箱格式
    email = data["email"]
    if "@" not in email:
        raise ValidationError("email", "邮箱格式不正确")
    
    # 模拟业务逻辑检查
    if email == "admin@example.com":
        raise BusinessLogicError("该邮箱已被保留", "EMAIL_RESERVED")
    
    # 模拟成功创建用户
    return JSONResponse({
        "message": "用户创建成功",
        "user": {
            "email": email,
            "created_at": datetime.now().isoformat()
        }
    }, status_code=201)

routes = [
    Route("/success", success_endpoint),
    Route("/http-error", http_error_endpoint),
    Route("/business-error", business_error_endpoint),
    Route("/validation-error", validation_error_endpoint),
    Route("/general-error", general_error_endpoint),
    Route("/users", user_create_endpoint, methods=["POST"]),
]

# 定义异常处理器映射
exception_handlers = {
    HTTPException: http_exception_handler,
    BusinessLogicError: business_exception_handler,
    ValidationError: validation_exception_handler,
    Exception: general_exception_handler,  # 捕获所有其他异常
}

app = Starlette(
    debug=True,  # 开启调试模式
    routes=routes,
    exception_handlers=exception_handlers
)
```

## 8. 应用生命周期示例

### 8.1 使用 Lifespan 管理资源

```python
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import asyncio
import httpx
from datetime import datetime

# 模拟数据库连接
class Database:
    def __init__(self, url: str):
        self.url = url
        self.connected = False
        self.connection_time = None
    
    async def connect(self):
        print(f"连接到数据库: {self.url}")
        # 模拟连接延迟
        await asyncio.sleep(1)
        self.connected = True
        self.connection_time = datetime.now()
        print("数据库连接成功")
    
    async def disconnect(self):
        print("断开数据库连接")
        self.connected = False
        print("数据库连接已断开")
    
    async def query(self, sql: str):
        if not self.connected:
            raise RuntimeError("数据库未连接")
        return f"执行查询: {sql}"

# 模拟 Redis 连接
class Redis:
    def __init__(self, url: str):
        self.url = url
        self.connected = False
    
    async def connect(self):
        print(f"连接到 Redis: {self.url}")
        await asyncio.sleep(0.5)
        self.connected = True
        print("Redis 连接成功")
    
    async def disconnect(self):
        print("断开 Redis 连接")
        self.connected = False
        print("Redis 连接已断开")
    
    async def get(self, key: str):
        if not self.connected:
            raise RuntimeError("Redis 未连接")
        return f"Redis value for {key}"

# 应用程序生命周期管理
@asynccontextmanager
async def app_lifespan(app: Starlette):
    """应用程序生命周期上下文管理器"""
    
    # 启动阶段
    print("🚀 应用程序启动中...")
    
    try:
        # 初始化数据库连接
        database = Database("postgresql://localhost/myapp")
        await database.connect()
        app.state.database = database
        
        # 初始化 Redis 连接
        redis = Redis("redis://localhost:6379")
        await redis.connect()
        app.state.redis = redis
        
        # 初始化 HTTP 客户端
        http_client = httpx.AsyncClient(timeout=10.0)
        app.state.http_client = http_client
        
        # 启动后台任务
        app.state.background_task = asyncio.create_task(background_worker())
        
        print("✅ 应用程序启动完成")
        
        yield  # 应用程序运行期间
        
    finally:
        # 关闭阶段
        print("🔄 应用程序关闭中...")
        
        try:
            # 取消后台任务
            if hasattr(app.state, 'background_task'):
                app.state.background_task.cancel()
                try:
                    await app.state.background_task
                except asyncio.CancelledError:
                    print("后台任务已取消")
            
            # 关闭 HTTP 客户端
            if hasattr(app.state, 'http_client'):
                await app.state.http_client.aclose()
                print("HTTP 客户端已关闭")
            
            # 关闭 Redis 连接
            if hasattr(app.state, 'redis'):
                await app.state.redis.disconnect()
            
            # 关闭数据库连接
            if hasattr(app.state, 'database'):
                await app.state.database.disconnect()
            
            print("✅ 应用程序关闭完成")
            
        except Exception as e:
            print(f"❌ 关闭过程中出现错误: {e}")

async def background_worker():
    """后台工作任务"""
    print("🔄 后台工作任务启动")
    try:
        while True:
            print(f"⏰ 后台任务执行中: {datetime.now()}")
            await asyncio.sleep(30)  # 每30秒执行一次
    except asyncio.CancelledError:
        print("🔄 后台工作任务停止")
        raise

# API 端点
async def health_check(request):
    """健康检查端点"""
    database_status = "connected" if request.app.state.database.connected else "disconnected"
    redis_status = "connected" if request.app.state.redis.connected else "disconnected"
    
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": database_status,
            "redis": redis_status,
        },
        "uptime": str(datetime.now() - request.app.state.database.connection_time) if request.app.state.database.connection_time else None
    })

async def database_query(request):
    """数据库查询端点"""
    try:
        result = await request.app.state.database.query("SELECT * FROM users")
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def redis_get(request):
    """Redis 获取端点"""
    try:
        key = request.path_params.get("key", "default_key")
        result = await request.app.state.redis.get(key)
        return JSONResponse({"key": key, "value": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def external_api_call(request):
    """调用外部 API"""
    try:
        response = await request.app.state.http_client.get("https://httpbin.org/json")
        return JSONResponse({
            "status": "success",
            "external_data": response.json()
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

routes = [
    Route("/health", health_check),
    Route("/db/query", database_query),
    Route("/redis/{key}", redis_get),
    Route("/external", external_api_call),
]

# 创建应用实例
app = Starlette(
    routes=routes,
    lifespan=app_lifespan
)
```

## 9. 完整应用示例

### 9.1 RESTful API 应用

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional
import json
import uuid

# 数据存储 (生产环境应使用真实数据库)
users_db: Dict[str, dict] = {}
posts_db: Dict[str, dict] = {}

# 数据模型类
class User:
    def __init__(self, name: str, email: str, user_id: str = None):
        self.id = user_id or str(uuid.uuid4())
        self.name = name
        self.email = email
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class Post:
    def __init__(self, title: str, content: str, author_id: str, post_id: str = None):
        self.id = post_id or str(uuid.uuid4())
        self.title = title
        self.content = content
        self.author_id = author_id
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "author_id": self.author_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

# 数据验证函数
def validate_user_data(data: dict) -> dict:
    """验证用户数据"""
    errors = {}
    
    if not data.get("name"):
        errors["name"] = "姓名是必填字段"
    elif len(data["name"]) < 2:
        errors["name"] = "姓名至少需要2个字符"
    
    if not data.get("email"):
        errors["email"] = "邮箱是必填字段"
    elif "@" not in data["email"]:
        errors["email"] = "邮箱格式不正确"
    
    return errors

def validate_post_data(data: dict) -> dict:
    """验证文章数据"""
    errors = {}
    
    if not data.get("title"):
        errors["title"] = "标题是必填字段"
    elif len(data["title"]) < 5:
        errors["title"] = "标题至少需要5个字符"
    
    if not data.get("content"):
        errors["content"] = "内容是必填字段"
    elif len(data["content"]) < 10:
        errors["content"] = "内容至少需要10个字符"
    
    if not data.get("author_id"):
        errors["author_id"] = "作者ID是必填字段"
    elif data["author_id"] not in users_db:
        errors["author_id"] = "作者不存在"
    
    return errors

# API 端点 - 用户管理
async def get_users(request):
    """获取用户列表"""
    page = int(request.query_params.get("page", 1))
    limit = int(request.query_params.get("limit", 10))
    
    users_list = list(users_db.values())
    total = len(users_list)
    
    start = (page - 1) * limit
    end = start + limit
    paginated_users = users_list[start:end]
    
    return JSONResponse({
        "users": paginated_users,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    })

async def create_user(request):
    """创建用户"""
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效的 JSON 数据")
    
    errors = validate_user_data(data)
    if errors:
        return JSONResponse({"errors": errors}, status_code=422)
    
    # 检查邮箱是否已存在
    for user in users_db.values():
        if user["email"] == data["email"]:
            return JSONResponse(
                {"errors": {"email": "该邮箱已被使用"}}, 
                status_code=409
            )
    
    user = User(data["name"], data["email"])
    users_db[user.id] = user.to_dict()
    
    return JSONResponse(user.to_dict(), status_code=201)

async def get_user(request):
    """获取单个用户"""
    user_id = request.path_params["user_id"]
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return JSONResponse(users_db[user_id])

async def update_user(request):
    """更新用户"""
    user_id = request.path_params["user_id"]
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效的 JSON 数据")
    
    errors = validate_user_data(data)
    if errors:
        return JSONResponse({"errors": errors}, status_code=422)
    
    # 检查邮箱是否被其他用户使用
    for uid, user in users_db.items():
        if uid != user_id and user["email"] == data["email"]:
            return JSONResponse(
                {"errors": {"email": "该邮箱已被使用"}}, 
                status_code=409
            )
    
    # 更新用户信息
    user = users_db[user_id]
    user["name"] = data["name"]
    user["email"] = data["email"]
    user["updated_at"] = datetime.now().isoformat()
    
    return JSONResponse(user)

async def delete_user(request):
    """删除用户"""
    user_id = request.path_params["user_id"]
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 删除用户的所有文章
    posts_to_delete = [post_id for post_id, post in posts_db.items() if post["author_id"] == user_id]
    for post_id in posts_to_delete:
        del posts_db[post_id]
    
    del users_db[user_id]
    
    return JSONResponse({"message": "用户已删除"})

# API 端点 - 文章管理
async def get_posts(request):
    """获取文章列表"""
    page = int(request.query_params.get("page", 1))
    limit = int(request.query_params.get("limit", 10))
    author_id = request.query_params.get("author_id")
    
    posts_list = list(posts_db.values())
    
    # 按作者过滤
    if author_id:
        posts_list = [post for post in posts_list if post["author_id"] == author_id]
    
    total = len(posts_list)
    
    start = (page - 1) * limit
    end = start + limit
    paginated_posts = posts_list[start:end]
    
    return JSONResponse({
        "posts": paginated_posts,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    })

async def create_post(request):
    """创建文章"""
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效的 JSON 数据")
    
    errors = validate_post_data(data)
    if errors:
        return JSONResponse({"errors": errors}, status_code=422)
    
    post = Post(data["title"], data["content"], data["author_id"])
    posts_db[post.id] = post.to_dict()
    
    return JSONResponse(post.to_dict(), status_code=201)

async def get_post(request):
    """获取单个文章"""
    post_id = request.path_params["post_id"]
    
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    post = posts_db[post_id]
    # 包含作者信息
    if post["author_id"] in users_db:
        post_with_author = post.copy()
        post_with_author["author"] = users_db[post["author_id"]]
        return JSONResponse(post_with_author)
    
    return JSONResponse(post)

async def update_post(request):
    """更新文章"""
    post_id = request.path_params["post_id"]
    
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效的 JSON 数据")
    
    # 验证数据（不包括 author_id，因为不允许更改）
    errors = {}
    if not data.get("title"):
        errors["title"] = "标题是必填字段"
    elif len(data["title"]) < 5:
        errors["title"] = "标题至少需要5个字符"
    
    if not data.get("content"):
        errors["content"] = "内容是必填字段"
    elif len(data["content"]) < 10:
        errors["content"] = "内容至少需要10个字符"
    
    if errors:
        return JSONResponse({"errors": errors}, status_code=422)
    
    # 更新文章
    post = posts_db[post_id]
    post["title"] = data["title"]
    post["content"] = data["content"]
    post["updated_at"] = datetime.now().isoformat()
    
    return JSONResponse(post)

async def delete_post(request):
    """删除文章"""
    post_id = request.path_params["post_id"]
    
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    del posts_db[post_id]
    
    return JSONResponse({"message": "文章已删除"})

# API 信息端点
async def api_info(request):
    """API 信息"""
    return JSONResponse({
        "name": "Starlette Demo API",
        "version": "1.0.0",
        "description": "一个使用 Starlette 构建的完整 RESTful API 示例",
        "endpoints": {
            "users": {
                "GET /users": "获取用户列表",
                "POST /users": "创建用户",
                "GET /users/{user_id}": "获取单个用户",
                "PUT /users/{user_id}": "更新用户",
                "DELETE /users/{user_id}": "删除用户"
            },
            "posts": {
                "GET /posts": "获取文章列表",
                "POST /posts": "创建文章",
                "GET /posts/{post_id}": "获取单个文章",
                "PUT /posts/{post_id}": "更新文章",
                "DELETE /posts/{post_id}": "删除文章"
            }
        },
        "timestamp": datetime.now().isoformat()
    })

# 应用生命周期
@asynccontextmanager
async def app_lifespan(app: Starlette):
    # 启动时初始化一些示例数据
    print("🚀 API 服务启动中...")
    
    # 创建示例用户
    user1 = User("张三", "zhangsan@example.com")
    user2 = User("李四", "lisi@example.com")
    users_db[user1.id] = user1.to_dict()
    users_db[user2.id] = user2.to_dict()
    
    # 创建示例文章
    post1 = Post("Starlette 入门指南", "这是一篇关于 Starlette 框架的入门指南...", user1.id)
    post2 = Post("Python 异步编程", "异步编程是现代 Python 开发的重要技能...", user2.id)
    posts_db[post1.id] = post1.to_dict()
    posts_db[post2.id] = post2.to_dict()
    
    print("✅ API 服务启动完成")
    print(f"   - 初始化用户数: {len(users_db)}")
    print(f"   - 初始化文章数: {len(posts_db)}")
    
    yield
    
    print("🔄 API 服务关闭中...")
    print("✅ API 服务关闭完成")

# 路由配置
routes = [
    Route("/", api_info),
    
    # 用户路由
    Route("/users", get_users, methods=["GET"]),
    Route("/users", create_user, methods=["POST"]),
    Route("/users/{user_id}", get_user, methods=["GET"]),
    Route("/users/{user_id}", update_user, methods=["PUT"]),
    Route("/users/{user_id}", delete_user, methods=["DELETE"]),
    
    # 文章路由
    Route("/posts", get_posts, methods=["GET"]),
    Route("/posts", create_post, methods=["POST"]),
    Route("/posts/{post_id}", get_post, methods=["GET"]),
    Route("/posts/{post_id}", update_post, methods=["PUT"]),
    Route("/posts/{post_id}", delete_post, methods=["DELETE"]),
]

# 中间件配置
middleware = [
    Middleware(GZipMiddleware, minimum_size=1000),
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    ),
]

# 创建应用
app = Starlette(
    routes=routes,
    middleware=middleware,
    lifespan=app_lifespan
)

# 运行方式：
# uvicorn complete_api_example:app --reload --port 8000
```

## 运行和测试

### 启动应用

所有示例都可以使用以下命令运行：

```bash
# 安装依赖
pip install starlette uvicorn

# 运行应用
uvicorn filename:app --reload --port 8000
```

### API 测试示例

```bash
# 测试用户 API
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "测试用户", "email": "test@example.com"}'

curl -X GET http://localhost:8000/users

curl -X GET http://localhost:8000/users/{user_id}

# 测试文章 API
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{"title": "测试文章", "content": "这是测试内容", "author_id": "{user_id}"}'

curl -X GET http://localhost:8000/posts
```

这些示例展示了 Starlette 的强大功能和灵活性，从简单的 Hello World 到完整的 RESTful API，涵盖了实际开发中的各种使用场景。通过这些示例，您可以快速上手 Starlette 并构建自己的异步 Web 应用。