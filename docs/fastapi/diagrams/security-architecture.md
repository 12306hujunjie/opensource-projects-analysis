# FastAPI 安全架构图表

## 1. 安全层概述

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FastAPI 安全架构                                      │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                           纵深防御                                       │  │
│  │                                                                           │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                        周边安全                                    │ │  │
│  │  │                                                                     │ │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │ │  │
│  │  │  │  网络应用    │  │  DDoS防护   │  │     TLS     │  │   防火墙    │ │ │  │
│  │  │  │             │  │             │  │             │  │             │ │ │  │
│  │  │  │ • OWASP     │  │ • 速率       │  │ • 1.3       │  │ • 端口       │ │ │  │
│  │  │  │   规则       │  │   限制      │  │ • HSTS      │  │   限制      │ │ │  │
│  │  │  │ • IP过滤   │  │ • 流量       │  │ • 完美       │  │ • IP        │ │ │  │
│  │  │  │ • 地理封锁  │  │   整形       │  │   前向       │  │   白名单     │ │ │  │
│  │  │  │ • 机器人检测 │  │             │  │   保密       │  │             │ │ │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │ │  │
│  │  └─────────────────────────────────────────────────────────────────────┘ │  │
│  │                                      │                                   │  │
│  │                                      ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                      应用程序安全                                  │ │  │
│  │  │                                                                     │ │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │ │  │
│  │  │  │    认证     │  │   输入       │  │   CORS      │  │    CSRF     │ │ │  │
│  │  │  │ 中间件      │  │ 验证        │  │   策略      │  │ 防护        │ │ │  │
│  │  │  │             │  │             │  │             │  │             │ │ │  │
│  │  │  │ • JWT       │  │ • Pydantic  │  │ • 来源       │  │ • 令牌      │ │ │  │
│  │  │  │ • OAuth2    │  │ • 清理      │  │ • 方法       │  │ • 双重      │ │ │  │
│  │  │  │ • API密钥   │  │ • 长度      │  │ • 请求头     │  │   提交      │ │ │  │
│  │  │  │ • 会话      │  │   限制      │  │ • 凭证       │  │ • SameSite  │ │ │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │ │  │
│  │  └─────────────────────────────────────────────────────────────────────┘ │  │
│  │                                      │                                   │  │
│  │                                      ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                        数据安全                                       │ │  │
│  │  │                                                                     │ │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │ │  │
│  │  │  │ 加密        │  │   访问      │  │    审计      │  │   隐私     │ │ │  │
│  │  │  │             │  │   控制      │  │   日志      │  │   控制      │ │ │  │
│  │  │  │             │  │             │  │             │  │             │ │ │  │
│  │  │  │ • 静态      │  │ • RBAC      │  │ • 安全      │  │ • PII遮罩  │ │ │  │
│  │  │  │ • 传输中    │  │ • ABAC      │  │   事件      │  │ • GDPR      │ │ │  │
│  │  │  │ • 字段级   │  │ • ACL       │  │ • API调用   │  │ • 数据最小  │ │ │  │
│  │  │  │ • 密钥管理  │  │ • 策略      │  │ • 异常      │  │ • 保留      │ │ │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │ │  │
│  │  └─────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. 身份验证与授权流程

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     认证与授权流程                                        │
│                                                                                 │
│    ┌─────────────┐                                                             │
│    │   客户端    │                                                             │
│    │  请求      │                                                             │
│    └──────┬──────┘                                                             │
│           │ POST /auth/login                                                   │
│           │ { "username": "user", "password": "pass" }                         │
│           ▼                                                                    │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                    认证服务                                     │   │
│    │                                                                     │   │
│    │    async def authenticate_user(credentials: UserCredentials):       │   │
│    │        # 1. 输入验证                                              │   │
│    │        user_input = sanitize_credentials(credentials)               │   │
│    │                                                                     │   │
│    │        # 2. 速率限制检查                                         │   │
│    │        await check_rate_limit(user_input.username)                  │   │
│    │                                                                     │   │
│    │        # 3. 用户查找 (带时序攻击防护)                        │   │
│    │        user = await get_user_by_username(user_input.username)       │   │
│    │                                                                     │   │
│    │        # 4. 密码验证                                             │   │
│    │        is_valid = await verify_password(                            │   │
│    │            user_input.password,                                     │   │
│    │            user.hashed_password                                     │   │
│    │        )                                                            │   │
│    │                                                                     │   │
│    │        # 5. 多因子认证 (如果启用)                             │   │
│    │        if user.mfa_enabled:                                         │   │
│    │            await verify_mfa_token(user_input.mfa_token)             │   │
│    │                                                                     │   │
│    │        # 6. 生成 JWT 令牌                                          │   │
│    │        if is_valid:                                                 │   │
│    │            return generate_jwt_token(user)                          │   │
│    │        else:                                                        │   │
│    │            await log_failed_attempt(user_input.username)            │   │
│    │            raise HTTPException(401, "Invalid credentials")          │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                       JWT 令牌结构                                   │   │
│    │                                                                     │   │
│    │    Header: {                                                        │   │
│    │        "alg": "RS256",          # RSA 使用 SHA-256                   │   │
│    │        "typ": "JWT",                                                │   │
│    │        "kid": "key-id-1"        # 密钥轮换的密钥ID                │   │
│    │    }                                                                │   │
│    │                                                                     │   │
│    │    Payload: {                                                       │   │
│    │        "sub": "user-uuid",      # Subject (user ID)                │   │
│    │        "iss": "fastapi-app",    # Issuer                           │   │
│    │        "aud": ["api", "web"],   # Audience                         │   │
│    │        "iat": 1640995200,       # Issued at                        │   │
│    │        "exp": 1640998800,       # Expires at (1 hour)              │   │
│    │        "jti": "token-uuid",     # JWT ID (for revocation)          │   │
│    │        "roles": ["user"],       # User roles                       │   │
│    │        "scopes": ["read", "write"], # API scopes                   │   │
│    │        "tenant": "tenant-id",   # Multi-tenancy                    │   │
│    │        "session": "sess-id"     # Session ID                       │   │
│    │    }                                                                │   │
│    │                                                                     │   │
│    │    Signature: RSA256(                                               │   │
│    │        base64UrlEncode(header) + "." +                              │   │
│    │        base64UrlEncode(payload),                                    │   │
│    │        private_key                                                  │   │
│    │    )                                                                │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                    Subsequent API Request                           │   │
│    │                                                                     │   │
│    │    GET /api/v1/protected-resource                                   │   │
│    │    Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI...          │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                   Authorization Middleware                          │   │
│    │                                                                     │   │
│    │    class JWTBearer(HTTPBearer):                                     │   │
│    │        async def __call__(self, request: Request):                  │   │
│    │            credentials = await super().__call__(request)            │   │
│    │                                                                     │   │
│    │            # 1. Token extraction and format validation             │   │
│    │            token = credentials.credentials                          │   │
│    │                                                                     │   │
│    │            # 2. JWT signature verification                         │   │
│    │            try:                                                     │   │
│    │                payload = jwt.decode(                               │   │
│    │                    token, public_key,                              │   │
│    │                    algorithms=["RS256"],                           │   │
│    │                    options={                                        │   │
│    │                        "verify_exp": True,                         │   │
│    │                        "verify_aud": True,                         │   │
│    │                        "require": ["exp", "sub", "roles"]          │   │
│    │                    }                                                │   │
│    │                )                                                    │   │
│    │            except jwt.ExpiredSignatureError:                       │   │
│    │                raise HTTPException(401, "Token expired")           │   │
│    │            except jwt.InvalidTokenError:                           │   │
│    │                raise HTTPException(401, "Invalid token")           │   │
│    │                                                                     │   │
│    │            # 3. Token revocation check (optional)                  │   │
│    │            jti = payload.get("jti")                                 │   │
│    │            if await is_token_revoked(jti):                          │   │
│    │                raise HTTPException(401, "Token revoked")            │   │
│    │                                                                     │   │
│    │            # 4. User context creation                              │   │
│    │            return SecurityScope(                                    │   │
│    │                user_id=payload["sub"],                             │   │
│    │                roles=payload["roles"],                             │   │
│    │                scopes=payload["scopes"],                           │   │
│    │                tenant_id=payload.get("tenant")                     │   │
│    │            )                                                        │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                     Endpoint Authorization                          │   │
│    │                                                                     │   │
│    │    @app.get("/api/v1/admin/users")                                  │   │
│    │    async def get_users(                                             │   │
│    │        security_scope: SecurityScope = Depends(                    │   │
│    │            JWTBearer(required_roles={"admin"})                     │   │
│    │        )                                                            │   │
│    │    ):                                                               │   │
│    │        # Role-based access control                                 │   │
│    │        if "admin" not in security_scope.roles:                     │   │
│    │            raise HTTPException(403, "Insufficient permissions")     │   │
│    │                                                                     │   │
│    │        # Resource-based access control                             │   │
│    │        if security_scope.tenant_id != requested_tenant:            │   │
│    │            raise HTTPException(403, "Access denied")               │   │
│    │                                                                     │   │
│    │        # Scope-based access control                                │   │
│    │        if "users:read" not in security_scope.scopes:               │   │
│    │            raise HTTPException(403, "Scope not authorized")        │   │
│    │                                                                     │   │
│    │        return await get_tenant_users(security_scope.tenant_id)     │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3. 输入验证安全

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          输入验证安全                                          │
│                                                                                 │
│    ┌─────────────┐                                                             │
│    │    请求     │                                                             │
│    │    数据     │                                                             │
│    └──────┬──────┘                                                             │
│           │                                                                    │
│           ▼                                                                    │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                     Pydantic 验证                                  │   │
│    │                                                                     │   │
│    │    class SecureUserInput(BaseModel):                               │   │
│    │        # SQL 注入防护                                   │   │
│    │        username: str = Field(                                       │   │
│    │            ...,                                                     │   │
│    │            min_length=3,                                            │   │
│    │            max_length=50,                                           │   │
│    │            regex=r'^[a-zA-Z0-9_.-]+$'  # 仅字母数字        │   │
│    │        )                                                            │   │
│    │                                                                     │   │
│    │        # XSS 防护                                             │   │
│    │        description: str = Field(                                    │   │
│    │            ...,                                                     │   │
│    │            max_length=1000                                          │   │
│    │        )                                                            │   │
│    │                                                                     │   │
│    │        # 命令注入防护                               │   │
│    │        filename: str = Field(                                       │   │
│    │            ...,                                                     │   │
│    │            regex=r'^[a-zA-Z0-9._-]+$'  # 安全文件名字符      │   │
│    │        )                                                            │   │
│    │                                                                     │   │
│    │        # 路径遍历防护                                  │   │
│    │        file_path: str = Field(..., max_length=255)                 │   │
│    │                                                                     │   │
│    │        # 邮箱验证                                           │   │
│    │        email: EmailStr = Field(...)                                │   │
│    │                                                                     │   │
│    │        # 电话号码验证                                    │   │
│    │        phone: str = Field(                                          │   │
│    │            ...,                                                     │   │
│    │            regex=r'^\+?1?[2-9]\d{2}[2-9]\d{2}\d{4}$'              │   │
│    │        )                                                            │   │
│    │                                                                     │   │
│    │        @validator('description')                                    │   │
│    │        def sanitize_description(cls, v):                            │   │
│    │            # HTML实体编码进行XSS防护               │   │
│    │            import html                                              │   │
│    │            return html.escape(v)                                    │   │
│    │                                                                     │   │
│    │        @validator('file_path')                                      │   │
│    │        def validate_path(cls, v):                                   │   │
│    │            # 路径遍历防护                              │   │
│    │            if '..' in v or v.startswith('/'):                       │   │
│    │                raise ValueError('无效路径')                     │   │
│    │            return v                                                 │   │
│    │                                                                     │   │
│    │        class Config:                                                │   │
│    │            # 附加安全选项                            │   │
│    │            anystr_strip_whitespace = True                           │   │
│    │            max_anystr_length = 10000                               │   │
│    │            validate_assignment = True                               │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                    自定义安全验证器                             │   │
│    │                                                                     │   │
│    │    def validate_no_sql_keywords(value: str) -> str:                 │   │
│    │        """防止SQL注入攻击"""                         │   │
│    │        sql_keywords = [                                             │   │
│    │            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP',         │   │
│    │            'UNION', 'EXEC', 'EXECUTE', 'SCRIPT', 'JAVASCRIPT'      │   │
│    │        ]                                                            │   │
│    │        upper_value = value.upper()                                  │   │
│    │        for keyword in sql_keywords:                                 │   │
│    │            if keyword in upper_value:                               │   │
│    │                raise ValueError(f'禁止的关键字: {keyword}')    │   │
│    │        return value                                                 │   │
│    │                                                                     │   │
│    │    def validate_safe_url(url: str) -> str:                          │   │
│    │        """防止SSRF攻击"""                                   │   │
│    │        from urllib.parse import urlparse                            │   │
│    │        parsed = urlparse(url)                                       │   │
│    │                                                                     │   │
│    │        # 阻止私有IP范围                                    │   │
│    │        if parsed.hostname in ['localhost', '127.0.0.1']:           │   │
│    │            raise ValueError('不允许私有IP')               │   │
│    │                                                                     │   │
│    │        # 阻止内部网络                                    │   │
│    │        if parsed.hostname.startswith('192.168.'):                  │   │
│    │            raise ValueError('不允许私有网络')          │   │
│    │                                                                     │   │
│    │        # 仅允许HTTPS                                           │   │
│    │        if parsed.scheme != 'https':                                 │   │
│    │            raise ValueError('仅允许HTTPS URL')              │   │
│    │                                                                     │   │
│    │        return url                                                   │   │
│    │                                                                     │   │
│    │    def validate_file_content(content: bytes) -> bytes:              │   │
│    │        """验证上传文件内容"""                         │   │
│    │        # 大小限制                                                 │   │
│    │        if len(content) > 10 * 1024 * 1024:  # 10MB                 │   │
│    │            raise ValueError('文件过大')                       │   │
│    │                                                                     │   │
│    │        # 图像文件的魔数字节检查                          │   │
│    │        image_signatures = {                                         │   │
│    │            b'\xFF\xD8\xFF': 'JPEG',                                 │   │
│    │            b'\x89PNG\r\n\x1a\n': 'PNG',                            │   │
│    │            b'GIF87a': 'GIF',                                        │   │
│    │            b'GIF89a': 'GIF'                                         │   │
│    │        }                                                            │   │
│    │                                                                     │   │
│    │        # 检查文件是否以已知签名开始                  │   │
│    │        for signature in image_signatures:                           │   │
│    │            if content.startswith(signature):                        │   │
│    │                return content                                       │   │
│    │                                                                     │   │
│    │        raise ValueError('无效文件类型')                        │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                       清理管道                                      │   │
│    │                                                                     │   │
│    │    class SecurityMiddleware:                                        │   │
│    │        async def __call__(self, request: Request, call_next):       │   │
│    │            # 1. 请求大小限制                                  │   │
│    │            content_length = request.headers.get('content-length')   │   │
│    │            if content_length and int(content_length) > MAX_SIZE:    │   │
│    │                raise HTTPException(413, "负载过大")        │   │
│    │                                                                     │   │
│    │            # 2. 速率限制                                       │   │
│    │            client_ip = request.client.host                          │   │
│    │            if await is_rate_limited(client_ip):                     │   │
│    │                raise HTTPException(429, "请求过多")        │   │
│    │                                                                     │   │
│    │            # 3. 请求头安全                                     │   │
│    │            dangerous_headers = [                                    │   │
│    │                'x-forwarded-for', 'x-real-ip',                     │   │
│    │                'x-forwarded-host', 'host'                          │   │
│    │            ]                                                        │   │
│    │            for header in dangerous_headers:                         │   │
│    │                if header in request.headers:                        │   │
│    │                    await log_security_event(                        │   │
│    │                        "可疑请求头", header, client_ip       │   │
│    │                    )                                                │   │
│    │                                                                     │   │
│    │            response = await call_next(request)                      │   │
│    │                                                                     │   │
│    │            # 4. 响应安全头                           │   │
│    │            response.headers.update({                                │   │
│    │                "X-Content-Type-Options": "nosniff",                │   │
│    │                "X-Frame-Options": "DENY",                          │   │
│    │                "X-XSS-Protection": "1; mode=block",                │   │
│    │                "Strict-Transport-Security": "max-age=31536000",    │   │
│    │                "Content-Security-Policy": "default-src 'self'",    │   │
│    │                "Referrer-Policy": "strict-origin-when-cross-origin" │   │
│    │            })                                                       │   │
│    │                                                                     │   │
│    │            return response                                          │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 4. 数据保护架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          数据保护架构                                         │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                        静态加密                                           │  │
│  │                                                                           │  │
│  │    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐       │  │
│  │    │  应用程序  │         │   数据库    │         │   备份     │       │  │
│  │    │   密钥     │         │   加密     │         │   加密     │       │  │
│  │    │             │────────▶│             │────────▶│             │       │  │
│  │    │ • AES-256   │         │ • TDE       │         │ • GPG       │       │  │
│  │    │ • RSA-4096  │         │ • 字段      │         │ • AES-256   │       │  │
│  │    │ • 密钥      │         │   级别      │         │ • 异地      │       │  │
│  │    │   轮换      │         │ • 自动      │         │   存储      │       │  │
│  │    │ • HSM       │         │   加密      │         │ • 版本化    │       │  │
│  │    └─────────────┘         └─────────────┘         └─────────────┘       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                      传输中加密                                          │  │
│  │                                                                           │  │
│  │    Client ◄───TLS 1.3───► Load Balancer ◄───mTLS───► FastAPI             │  │
│  │                                  │                       │                │  │
│  │                                  ▼                       ▼                │  │
│  │    ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │    │                      TLS 配置                                  │   │  │
│  │    │                                                                 │   │  │
│  │    │    tls_config = {                                               │   │  │
│  │    │        'protocol': 'TLSv1.3',                                   │   │  │
│  │    │        'ciphers': [                                             │   │  │
│  │    │            'TLS_AES_256_GCM_SHA384',                            │   │  │
│  │    │            'TLS_CHACHA20_POLY1305_SHA256',                      │   │  │
│  │    │            'TLS_AES_128_GCM_SHA256'                             │   │  │
│  │    │        ],                                                       │   │  │
│  │    │        'key_exchange': 'ECDHE',                                 │   │  │
│  │    │        'signature': 'ECDSA',                                    │   │  │
│  │    │        'certificate_transparency': True,                        │   │  │
│  │    │        'hsts_max_age': 31536000,                                │   │  │
│  │    │        'hsts_include_subdomains': True                          │   │  │
│  │    │    }                                                            │   │  │
│  │    └─────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                           │  │
│  │    FastAPI ◄───TLS 1.3───► Database ◄───VPN───► Cache ◄───TLS───► Queue  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                       密钥管理系统                                       │  │
│  │                                                                           │  │
│  │    ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │    │                    密钥生命周期                                 │   │  │
│  │    │                                                                 │   │  │
│  │    │    生成 → 存储 → 分发 → 轮换 → 销毁 │   │  │
│  │    │         │         │           │            │            │       │   │  │
│  │    │         ▼         ▼           ▼            ▼            ▼       │   │  │
│  │    │    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │   │  │
│  │    │    │ 随机    │ │   HSM   │ │   KMS   │ │ 计划    │ │ 安全    │ │   │  │
│  │    │    │ 生成    │ │ 保库    │ │  API    │ │ 轮换    │ │ 擦除    │ │   │  │
│  │    │    │ • CSPRNG│ │ • FIPS  │ │ • TLS   │ │ • 90day │ │ • Zero  │ │   │  │
│  │    │    │ • HSM   │ │  140-2  │ │ • mTLS  │ │ • Alert │ │   fill  │ │   │  │
│  │    │    │ • Entropy│ │ • Audit │ │ • RBAC  │ │ • Auto  │ │ • Multi │ │   │  │
│  │    │    └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │   │  │
│  │    └─────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                           │  │
│  │    ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │    │                  密钥类型和使用                                 │   │  │
│  │    │                                                                 │   │  │
│  │    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │  │
│  │    │  │   主      │  │   数据      │  │   会话     │           │   │  │
│  │    │  │ Encryption  │  │ Encryption  │  │    Keys     │           │   │  │
│  │    │  │    Keys     │  │    Keys     │  │             │           │   │  │
│  │    │  │             │  │             │  │             │           │   │  │
│  │    │  │ • RSA-4096  │  │ • AES-256   │  │ • Ephemeral │           │   │  │
│  │    │  │ • Root CA   │  │ • ChaCha20  │  │ • Short TTL │           │   │  │
│  │    │  │ • Signing   │  │ • Encrypted │  │ • Memory    │           │   │  │
│  │    │  │   keys      │  │   storage   │  │   only      │           │   │  │
│  │    │  └─────────────┘  └─────────────┘  └─────────────┘           │   │  │
│  │    └─────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                      隐私与合规                                           │  │
│  │                                                                           │  │
│  │    ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │    │                    GDPR 合规                                   │   │  │
│  │    │                                                                 │   │  │
│  │    │    class GDPRCompliantModel(BaseModel):                        │   │  │
│  │    │        # 数据最小化                                      │   │  │
│  │    │        personal_data: Optional[str] = Field(                    │   │  │
│  │    │            None,                                                │   │  │
│  │    │            description="仅在必要时收集"             │   │  │
│  │    │        )                                                        │   │  │
│  │    │                                                                 │   │  │
│  │    │        # 目的限制                                     │   │  │
│  │    │        processing_purpose: str = Field(                        │   │  │
│  │    │            ...,                                                 │   │  │
│  │    │            description="处理的具体目的"       │   │  │
│  │    │        )                                                        │   │  │
│  │    │                                                                 │   │  │
│  │    │        # 存储限制                                     │   │  │
│  │    │        retention_period: timedelta = Field(                    │   │  │
│  │    │            default=timedelta(days=365)                         │   │  │
│  │    │        )                                                        │   │  │
│  │    │                                                                 │   │  │
│  │    │        # 数据主体权利                                    │   │  │
│  │    │        @validator('personal_data')                              │   │  │
│  │    │        def ensure_consent(cls, v, values):                      │   │  │
│  │            if v and not values.get('consent_given'):                │   │  │
│  │                raise ValueError('需要同意')                  │   │  │
│  │            return v                                                  │   │  │
│  │    │                                                                 │   │  │
│  │    │        class Config:                                            │   │  │
│  │    │            # 启用审计日志                               │   │  │
│  │    │            audit_fields = True                                  │   │  │
│  │    │            # 保存期后自动匿名化         │   │  │
│  │    │            auto_anonymize = True                                │   │  │
│  │    └─────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                           │  │
│  │    ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │    │                    数据匿名化                                │   │  │
│  │    │                                                                 │   │  │
│  │    │    def anonymize_pii(data: dict) -> dict:                       │   │  │
│  │    │        """删除或遮罩个人可识别信息""" │   │  │
│  │    │        anonymized = data.copy()                                 │   │  │
│  │    │                                                                 │   │  │
│  │    │        # 邮箱匿名化                                    │   │  │
│  │    │        if 'email' in anonymized:                                │   │  │
│  │    │            email = anonymized['email']                          │   │  │
│  │    │            local, domain = email.split('@')                     │   │  │
│  │    │            anonymized['email'] = f"{local[:2]}***@{domain}"     │   │  │
│  │    │                                                                 │   │  │
│  │    │        # 姓名匿名化                                     │   │  │
│  │    │        if 'name' in anonymized:                                 │   │  │
│  │    │            name = anonymized['name']                            │   │  │
│  │    │            anonymized['name'] = name[0] + "*" * (len(name)-1)   │   │  │
│  │    │                                                                 │   │  │
│  │    │        # IP地址匿名化                               │   │  │
│  │    │        if 'ip_address' in anonymized:                           │   │  │
│  │    │            ip = anonymized['ip_address']                        │   │  │
│  │    │            parts = ip.split('.')                                │   │  │
│  │    │            anonymized['ip_address'] = f"{parts[0]}.{parts[1]}.XXX.XXX" │  │
│  │    │                                                                 │   │  │
│  │    │        return anonymized                                        │   │  │
│  │    └─────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```