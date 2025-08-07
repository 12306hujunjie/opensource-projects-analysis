# FastAPI Pydantic 集成

## 简介

FastAPI 与 Pydantic 的深度集成是其定义特征之一，提供自动请求验证、响应序列化和 OpenAPI 模式生成。这种集成利用 Python 的类型提示来创建无缝的开发体验，具有强类型安全性和自动文档生成功能。

## 核心集成架构

### 1. Pydantic 版本兼容性

FastAPI 通过全面的兼容层支持 Pydantic v1 和 v2：

```python
# From fastapi/_compat.py
from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC_VERSION_MINOR_TUPLE = tuple(int(x) for x in PYDANTIC_VERSION.split(".")[:2])
PYDANTIC_V2 = PYDANTIC_VERSION_MINOR_TUPLE[0] == 2

if PYDANTIC_V2:
    from pydantic import ValidationError as ValidationError
    from pydantic import TypeAdapter
    from pydantic.fields import FieldInfo
    from pydantic_core import PydanticUndefined as RequiredParam
    # ... v2 specific imports
else:
    from pydantic import ValidationError as ValidationError  
    from pydantic.fields import FieldInfo
    # ... v1 specific imports
```

This compatibility layer provides:
- **Unified Interface**: Common API regardless of Pydantic version
- **Feature Parity**: Same functionality across versions
- **Migration Path**: Smooth transition between Pydantic versions

### 2. ModelField Abstraction

FastAPI creates a unified `ModelField` abstraction that works across Pydantic versions:

```python
@dataclass
class ModelField:
    field_info: FieldInfo
    name: str
    mode: Literal["validation", "serialization"] = "validation"

    @property
    def alias(self) -> str:
        a = self.field_info.alias
        return a if a is not None else self.name

    @property
    def required(self) -> bool:
        return self.field_info.default in (RequiredParam, Undefined)

    @property
    def type_(self) -> Any:
        return self.field_info.annotation
```

This abstraction enables:
- **Version Independence**: Same interface for both Pydantic versions
- **Mode Support**: Distinction between validation and serialization modes
- **Property Access**: Consistent access to field metadata

## 模型字段创建

### 1. The create_model_field Function

The core function for creating model fields adapts to Pydantic versions:

```python
def create_model_field(
    name: str,
    type_: Any,
    class_validators: Optional[Dict[str, Validator]] = None,
    default: Optional[Any] = Undefined,
    required: Union[bool, UndefinedType] = Undefined,
    model_config: Type[BaseConfig] = BaseConfig,
    field_info: Optional[FieldInfo] = None,
    alias: Optional[str] = None,
    mode: Literal["validation", "serialization"] = "validation",
) -> ModelField:
    class_validators = class_validators or {}
    
    if PYDANTIC_V2:
        field_info = field_info or FieldInfo(
            annotation=type_, default=default, alias=alias
        )
        kwargs = {"name": name, "field_info": field_info, "mode": mode}
    else:
        field_info = field_info or FieldInfo()
        kwargs = {
            "name": name,
            "field_info": field_info,
            "type_": type_,
            "class_validators": class_validators,
            "default": default,
            "required": required,
            "model_config": model_config,
            "alias": alias,
        }
    
    try:
        return ModelField(**kwargs)
    except (RuntimeError, PydanticSchemaGenerationError):
        raise FastAPIError(f"Invalid args for response field! Check that {type_} is a valid Pydantic field type.")
```

### 2. Field Type Classification

FastAPI classifies fields based on their types and annotations:

```python
# Parameter type detection
if isinstance(value, params.Depends):
    # Dependency injection
    depends = value
elif isinstance(value, (params.Path, params.Query, params.Header, params.Cookie)):
    # Explicit parameter type
    field_info = value
elif is_path_param:
    # Path parameter inference
    field_info = params.Path()
else:
    # Query parameter default
    field_info = params.Query()
```

Classification rules:
- **Dependency Parameters**: Marked with `Depends()`
- **Path Parameters**: Present in URL path pattern
- **Query Parameters**: Default for non-body parameters
- **Body Parameters**: Pydantic models or explicit `Body()` annotation
- **Header Parameters**: Explicit `Header()` annotation
- **Cookie Parameters**: Explicit `Cookie()` annotation

## 请求验证管道

### 1. Parameter Extraction and Validation

FastAPI validates different parameter types using specialized functions:

```python
# Path parameter validation
path_values, path_errors = request_params_to_args(
    dependant.path_params, request.path_params
)

# Query parameter validation
query_values, query_errors = request_params_to_args(
    dependant.query_params, request.query_params
)

# Header parameter validation
header_values, header_errors = request_params_to_args(
    dependant.header_params, request.headers
)

# Cookie parameter validation
cookie_values, cookie_errors = request_params_to_args(
    dependant.cookie_params, request.cookies
)
```

### 2. Body Validation

Request body validation handles complex Pydantic models:

```python
async def request_body_to_args(
    *,
    body_fields: List[ModelField],
    received_body: Optional[Union[Dict[str, Any], FormData]],
    embed_body_fields: bool,
) -> Tuple[Dict[str, Any], List[Any]]:
    values = {}
    errors: List[Any] = []
    
    if body_fields:
        if embed_body_fields or len(body_fields) > 1:
            # Multiple body fields - create embedded structure
            body_model = create_body_model(body_fields)
            field = create_model_field(name="body", type_=body_model)
        else:
            # Single body field
            field = body_fields[0]
        
        # Validate body against field
        value, field_errors = field.validate(received_body, {}, loc=("body",))
        if field_errors:
            errors.extend(field_errors)
        else:
            values.update(value)
    
    return values, errors
```

Body validation features:
- **Single Model Validation**: Direct validation against Pydantic model
- **Multiple Field Embedding**: Combines multiple fields into single body model
- **Form Data Support**: Handles `multipart/form-data` and URL-encoded forms
- **File Upload Support**: Automatic handling of file uploads
- **Nested Model Support**: Full support for nested Pydantic models

### 3. Validation Error Handling

FastAPI collects and formats validation errors from all sources:

```python
# Error collection from all parameter types
errors: List[Any] = []
errors += path_errors + query_errors + header_errors + cookie_errors

# Body validation errors
if dependant.body_params:
    body_values, body_errors = await request_body_to_args(...)
    errors.extend(body_errors)

# Error formatting
if errors:
    raise RequestValidationError(errors, body=received_body)
```

Error format example:
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
            "loc": ["body", "user_id"],
            "msg": "Input should be a valid integer", 
            "input": "abc"
        }
    ]
}
```

## 响应序列化

### 1. Response Content Preparation

FastAPI prepares response content for JSON serialization:

```python
def _prepare_response_content(
    res: Any,
    *,
    exclude_unset: bool,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
) -> Any:
    if isinstance(res, BaseModel):
        # Handle ORM mode for database models
        read_with_orm_mode = getattr(_get_model_config(res), "read_with_orm_mode", None)
        if read_with_orm_mode:
            return res  # Let from_orm handle extraction
        
        # Standard Pydantic model serialization
        return _model_dump(
            res,
            by_alias=True,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
    elif isinstance(res, list):
        # Recursively handle lists
        return [
            _prepare_response_content(
                item,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )
            for item in res
        ]
    elif isinstance(res, dict):
        # Recursively handle dictionaries
        return {
            k: _prepare_response_content(
                v,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )
            for k, v in res.items()
        }
    elif dataclasses.is_dataclass(res):
        # Handle dataclasses
        return dataclasses.asdict(res)
    
    return res  # Return as-is for other types
```

### 2. Response Model Validation

When response models are specified, FastAPI validates the response:

```python
if self.response_field:
    # Prepare content for validation
    response_content = _prepare_response_content(
        raw_response,
        exclude_unset=self.response_model_exclude_unset,
        exclude_defaults=self.response_model_exclude_defaults,
        exclude_none=self.response_model_exclude_none,
    )
    
    # Validate response against response model
    if is_coroutine:
        value, errors = field.validate(response_content, {}, loc=("response",))
    else:
        value, errors = await run_in_threadpool(
            field.validate, response_content, {}, loc=("response",)
        )
    
    if errors:
        raise ResponseValidationError(errors=errors, body=response_content)
    
    # Use validated response
    actual_response_content = jsonable_encoder(
        value,
        include=self.response_model_include,
        exclude=self.response_model_exclude,
        by_alias=self.response_model_by_alias,
        exclude_unset=self.response_model_exclude_unset,
        exclude_defaults=self.response_model_exclude_defaults,
        exclude_none=self.response_model_exclude_none,
    )
```

## 高级 Pydantic 功能

### 1. Field Cloning for Response Models

FastAPI clones response fields to prevent inheritance issues:

```python
def create_cloned_field(field: ModelField) -> ModelField:
    # Create a cloned field to prevent subclass inheritance
    if lenient_issubclass(field.type_, BaseModel):
        use_type = create_response_model_fields_clone(field.type_)
    else:
        use_type = field.type_
        
    new_field = create_model_field(name=field.name, type_=use_type)
    
    # Copy all field attributes
    new_field.has_alias = field.has_alias
    new_field.alias = field.alias
    new_field.default = field.default
    new_field.required = field.required
    new_field.field_info = field.field_info
    
    return new_field
```

This prevents scenarios where:
- `UserInDB` (with password hash) extends `User` (public fields only)
- Response should return `User` but might return `UserInDB` due to inheritance
- Cloning ensures only specified fields are included in response

### 2. Custom Validators and Serializers

FastAPI supports Pydantic's validation and serialization customizations:

```python
class UserModel(BaseModel):
    id: int
    name: str
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(None, gt=0, le=120)
    
    @validator('email')
    def validate_email_domain(cls, v):
        if not v.endswith('@company.com'):
            raise ValueError('Email must be from company domain')
        return v
    
    @validator('age')
    def validate_age(cls, v):
        if v is not None and v < 13:
            raise ValueError('Users must be at least 13 years old')
        return v
```

### 3. ORM Mode Support

FastAPI supports Pydantic's ORM mode for database integration:

```python
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    
    class Config:
        from_attributes = True  # Pydantic v2
        # orm_mode = True       # Pydantic v1

# Usage with SQLAlchemy
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return user  # Pydantic automatically converts ORM object
```

## 模式生成集成

### 1. OpenAPI Schema Generation

FastAPI generates OpenAPI schemas from Pydantic models:

```python
def get_schema_from_model_field(
    *,
    field: ModelField,
    field_mapping: Dict[Tuple[ModelField, Literal["validation", "serialization"]], Any],
    separate_input_output_schemas: bool = True,
) -> Dict[str, Any]:
    # Generate schema based on Pydantic version
    if PYDANTIC_V2:
        return field_mapping[(field, field.mode)]
    else:
        # Pydantic v1 schema generation
        return field.field_info  # Simplified
```

### 2. Model Name Mapping

FastAPI maintains mappings between models and schema names:

```python
def get_model_definitions(
    *,
    flat_models: Set[Union[Type[BaseModel], Type[Enum]]],
    model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
) -> Dict[str, Any]:
    definitions: Dict[str, Dict[str, Any]] = {}
    
    for model in flat_models:
        if lenient_issubclass(model, BaseModel):
            model_schema = get_model_schema(model)
            model_name = model_name_map[model]
            definitions[model_name] = model_schema
    
    return definitions
```

### 3. Field Information Extraction

FastAPI extracts field information for documentation:

```python
def get_field_info(field: ModelField) -> Dict[str, Any]:
    field_info = field.field_info
    return {
        "title": getattr(field_info, "title", None),
        "description": getattr(field_info, "description", None),
        "default": field_info.default if field_info.default is not RequiredParam else None,
        "examples": getattr(field_info, "examples", None),
        "deprecated": getattr(field_info, "deprecated", None),
    }
```

## 类型系统集成

### 1. Union Type Handling

FastAPI handles Union types with special processing:

```python
def get_flat_models_from_routes(routes: Sequence[BaseRoute]) -> Set[Union[Type[BaseModel], Type[Enum]]]:
    body_fields = []
    responses = []
    
    # Extract models from all routes
    for route in routes:
        if getattr(route, "response_model", None):
            responses.append(route.response_model)
        if hasattr(route, "dependant"):
            body_fields.extend(route.dependant.body_params)
    
    # Handle Union types
    flat_models: Set[Union[Type[BaseModel], Type[Enum]]] = set()
    for field in body_fields:
        if hasattr(field.type_, "__origin__") and field.type_.__origin__ is Union:
            for arg in field.type_.__args__:
                if lenient_issubclass(arg, BaseModel):
                    flat_models.add(arg)
    
    return flat_models
```

### 2. Generic Type Support

FastAPI supports Pydantic's generic types:

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class Response(BaseModel, Generic[T]):
    data: T
    success: bool
    message: str

class User(BaseModel):
    id: int
    name: str

# Usage
@app.get("/user/{user_id}", response_model=Response[User])
def get_user(user_id: int) -> Response[User]:
    user = User(id=user_id, name="John Doe")
    return Response(data=user, success=True, message="User retrieved")
```

## 性能优化

### 1. Model Field Caching

FastAPI caches model fields for improved performance:

```python
# Cache for model fields
_CLONED_TYPES_CACHE: MutableMapping[Type[BaseModel], Type[BaseModel]] = WeakKeyDictionary()

def get_cached_model_fields(model: Type[BaseModel]) -> List[ModelField]:
    # Cache model fields to avoid repeated introspection
    return get_model_fields(model)

def create_response_model_fields_clone(model: Type[BaseModel]) -> Type[BaseModel]:
    if model in _CLONED_TYPES_CACHE:
        return _CLONED_TYPES_CACHE[model]
    
    # Create cloned model
    cloned_model = create_cloned_model(model)
    _CLONED_TYPES_CACHE[model] = cloned_model
    return cloned_model
```

### 2. Validation Optimization

- **Field-level Caching**: Model fields cached during route analysis
- **Schema Compilation**: Pydantic schemas compiled once during startup
- **Lazy Evaluation**: Complex validations executed only when needed
- **Memory Management**: WeakKeyDictionary prevents memory leaks

### 3. Serialization Performance

```python
def jsonable_encoder(
    obj: Any,
    include: Optional[IncEx] = None,
    exclude: Optional[IncEx] = None,
    by_alias: bool = True,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
    custom_encoder: Optional[Dict[Any, Callable[[Any], Any]]] = None,
    sqlalchemy_safe: bool = True,
) -> Any:
    # Optimized JSON encoding
    if isinstance(obj, BaseModel):
        if not PYDANTIC_V2:
            encoders = getattr(obj.__config__, "json_encoders", {})
            if custom_encoder:
                encoders.update(custom_encoder)
                
        # Use Pydantic's optimized serialization
        return _model_dump(
            obj,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
```

## 错误处理和边缘情况

### 1. Validation Error Recovery

```python
try:
    field = create_model_field(name=param_name, type_=annotation, ...)
except (RuntimeError, PydanticSchemaGenerationError) as e:
    raise FastAPIError(
        f"Invalid field configuration for {param_name}: {e}"
    )
```

### 2. Type Annotation Resolution

```python
def get_typed_annotation(annotation: Any, globalns: Dict[str, Any]) -> Any:
    if isinstance(annotation, str):
        # Handle forward references
        try:
            return evaluate_forwardref(annotation, globalns)
        except NameError:
            return annotation
    return annotation
```

### 3. Compatibility Layer Edge Cases

```python
# Handle differences between Pydantic versions
if PYDANTIC_V2:
    def _model_dump(model: BaseModel, **kwargs) -> Any:
        return model.model_dump(**kwargs)
else:
    def _model_dump(model: BaseModel, **kwargs) -> Any:
        return model.dict(**kwargs)
```

## 最佳实践

### 1. Model Design

```python
# Good: Clear, specific models
class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=EMAIL_REGEX)
    age: Optional[int] = Field(None, ge=13, le=120)

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

# Good: Separate input/output models
@app.post("/users/", response_model=UserResponse)
def create_user(user: CreateUserRequest):
    return user_service.create_user(user)
```

### 2. Validation Strategies

```python
# Good: Custom validators for business logic
class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=100)
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    
    @validator('quantity')
    def validate_quantity(cls, v, values):
        if 'product_id' in values:
            # Check stock availability
            if not inventory.check_stock(values['product_id'], v):
                raise ValueError('Insufficient stock')
        return v
```

### 3. Response Model Configuration

```python
# Good: Explicit response configuration
@app.get(
    "/users/{user_id}", 
    response_model=UserResponse,
    response_model_exclude_unset=True,
    response_model_exclude={"internal_field"}
)
def get_user(user_id: int):
    return user_service.get_user(user_id)
```

## 下一章节

继续阅读 [Starlette 基础](./06-starlette-foundation.md) 以了解 FastAPI 如何构建在 Starlette 的 ASGI 功能之上。