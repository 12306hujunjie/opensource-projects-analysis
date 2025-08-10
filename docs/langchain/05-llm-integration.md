# LangChain LLM 集成层深度分析

## 目录

1. [LLM抽象架构](#llm抽象架构)
2. [消息系统设计](#消息系统设计)
3. [提供商集成模式](#提供商集成模式)
4. [类型系统与泛型](#类型系统与泛型)
5. [异步与并发处理](#异步与并发处理)
6. [错误处理与重试](#错误处理与重试)
7. [实际集成案例](#实际集成案例)
8. [最佳实践指南](#最佳实践指南)

---

## LLM抽象架构

### 三层抽象体系

LangChain通过精心设计的三层抽象体系，实现了对各种LLM提供商的统一封装：

```python
# 第一层：基础语言模型抽象
class BaseLanguageModel(BaseModel, ABC):
    """所有语言模型的根基类"""
    
    # 通用配置
    callbacks: Callbacks = Field(default=None, exclude=True)
    tags: Optional[List[str]] = Field(default=None, exclude=True) 
    metadata: Optional[Dict[str, Any]] = Field(default=None, exclude=True)
    
    @abstractmethod
    def generate_prompt(
        self, 
        prompts: List[PromptValue],
        stop: Optional[List[str]] = None,
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> LLMResult:
        """生成响应的核心方法"""
    
    @abstractmethod
    async def agenerate_prompt(
        self,
        prompts: List[PromptValue], 
        stop: Optional[List[str]] = None,
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> LLMResult:
        """异步生成方法"""
    
    @abstractmethod
    def get_num_tokens(self, text: str) -> int:
        """计算token数量"""
    
    @property
    @abstractmethod
    def _llm_type(self) -> str:
        """返回LLM类型标识"""


# 第二层：专门化抽象
class BaseLLM(BaseLanguageModel):
    """文本完成模型的抽象基类"""
    
    @abstractmethod
    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """文本生成的具体实现"""
    
    def __call__(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """便捷调用接口"""
        result = self.generate([prompt], stop=stop)
        return result.generations[0][0].text


class BaseChatModel(BaseLanguageModel):
    """对话模型的抽象基类"""
    
    @abstractmethod
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """对话生成的具体实现"""
    
    def __call__(self, messages: List[BaseMessage], stop: Optional[List[str]] = None) -> BaseMessage:
        """便捷调用接口"""
        result = self.generate([messages], stop=stop)
        return result.generations[0][0].message


# 第三层：具体实现
class ChatOpenAI(BaseChatModel):
    """OpenAI Chat模型的具体实现"""
    
    model_name: str = Field(default="gpt-3.5-turbo", alias="model")
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1
    frequency_penalty: float = 0
    presence_penalty: float = 0
    n: int = 1
    streaming: bool = False
    
    # OpenAI特定配置
    openai_api_key: Optional[str] = Field(default=None, alias="api_key")
    openai_api_base: Optional[str] = Field(default=None, alias="base_url")
    openai_organization: Optional[str] = Field(default=None, alias="organization")
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """OpenAI API调用实现"""
        # 具体的API调用逻辑
        pass
```

### 统一输入输出接口

```python
# 统一的输入类型系统
LanguageModelInput = Union[
    PromptValue,           # 提示值对象
    str,                   # 简单字符串
    Sequence[BaseMessage], # 消息序列
    Dict[str, Any],       # 字典格式输入
]

# 统一的输出类型系统  
LanguageModelOutput = Union[
    str,                  # 文本输出
    BaseMessage,          # 消息输出
    LLMResult,           # 完整结果对象
    ChatResult,          # 对话结果对象
]

# 类型安全的LLM接口
class TypeSafeLLM(Generic[Input, Output]):
    """类型安全的LLM接口"""
    
    def invoke(self, input: Input, config: Optional[RunnableConfig] = None) -> Output:
        """类型安全的调用接口"""
        pass
    
    def batch(self, inputs: List[Input], config: Optional[RunnableConfig] = None) -> List[Output]:
        """批处理接口"""
        pass
    
    def stream(self, input: Input, config: Optional[RunnableConfig] = None) -> Iterator[Output]:
        """流式处理接口"""
        pass

# 具体的类型化实现
class TypedChatModel(TypeSafeLLM[List[BaseMessage], BaseMessage]):
    """类型化的对话模型"""
    
    def invoke(self, messages: List[BaseMessage], config: Optional[RunnableConfig] = None) -> BaseMessage:
        """类型安全的对话调用"""
        result = self._generate(messages, **self._get_generation_kwargs(config))
        return result.generations[0].message
```

### 配置管理系统

```python
class LLMConfigManager:
    """LLM配置管理器"""
    
    def __init__(self):
        self.default_configs = {}
        self.provider_configs = {}
        self.environment_configs = {}
    
    def register_provider_defaults(self, provider: str, config: Dict[str, Any]):
        """注册提供商默认配置"""
        self.provider_configs[provider] = config
    
    def get_merged_config(self, provider: str, user_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取合并后的配置"""
        
        # 配置优先级：用户配置 > 环境配置 > 提供商默认 > 全局默认
        merged_config = {}
        
        # 1. 全局默认配置
        merged_config.update(self.default_configs)
        
        # 2. 提供商默认配置
        if provider in self.provider_configs:
            merged_config.update(self.provider_configs[provider])
        
        # 3. 环境配置
        if provider in self.environment_configs:
            merged_config.update(self.environment_configs[provider])
            
        # 4. 用户配置
        if user_config:
            merged_config.update(user_config)
        
        return merged_config

# 配置验证系统
from pydantic import BaseModel, validator

class OpenAIConfig(BaseModel):
    """OpenAI配置验证模型"""
    
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError('temperature must be between 0 and 2')
        return v
    
    @validator('top_p')
    def validate_top_p(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('top_p must be between 0 and 1')
        return v
    
    @validator('max_tokens')
    def validate_max_tokens(cls, v):
        if v is not None and v <= 0:
            raise ValueError('max_tokens must be positive')
        return v

class AnthropicConfig(BaseModel):
    """Anthropic配置验证模型"""
    
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 1024
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    
    @validator('max_tokens')
    def validate_max_tokens(cls, v):
        if v <= 0 or v > 200000:
            raise ValueError('max_tokens must be between 1 and 200000')
        return v
```

---

## 消息系统设计

### 统一消息类型体系

```python
# 消息基类
class BaseMessage(BaseModel):
    """所有消息类型的基类"""
    
    content: Union[str, List[Union[str, Dict]]]  # 支持文本和多模态内容
    additional_kwargs: Dict[str, Any] = Field(default_factory=dict)
    response_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    type: str = Field()  # 消息类型标识
    name: Optional[str] = None
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    
    @property
    @abstractmethod
    def type(self) -> str:
        """消息类型"""
        pass
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(content={self.content})"


# 具体消息类型
class HumanMessage(BaseMessage):
    """人类用户消息"""
    
    example: bool = False  # 是否为示例消息
    
    @property
    def type(self) -> str:
        return "human"


class AIMessage(BaseMessage):
    """AI助手消息"""
    
    example: bool = False
    
    @property
    def type(self) -> str:
        return "ai"


class SystemMessage(BaseMessage):
    """系统消息"""
    
    @property
    def type(self) -> str:
        return "system"


class FunctionMessage(BaseMessage):
    """函数调用结果消息"""
    
    name: str  # 函数名
    
    @property
    def type(self) -> str:
        return "function"


class ToolMessage(BaseMessage):
    """工具调用结果消息"""
    
    tool_call_id: str  # 工具调用ID
    
    @property
    def type(self) -> str:
        return "tool"


# 多模态消息支持
class MultimodalMessage(BaseMessage):
    """多模态消息"""
    
    def __init__(self, content: List[Union[str, Dict]], **kwargs):
        """
        内容格式：
        [
            {"type": "text", "text": "描述这张图片"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]
        """
        super().__init__(content=content, **kwargs)
    
    def add_text(self, text: str):
        """添加文本内容"""
        if isinstance(self.content, str):
            self.content = [{"type": "text", "text": self.content}]
        elif not isinstance(self.content, list):
            self.content = []
        
        self.content.append({"type": "text", "text": text})
    
    def add_image(self, image_url: str, detail: str = "auto"):
        """添加图像内容"""
        if isinstance(self.content, str):
            self.content = [{"type": "text", "text": self.content}]
        elif not isinstance(self.content, list):
            self.content = []
        
        self.content.append({
            "type": "image_url",
            "image_url": {
                "url": image_url,
                "detail": detail
            }
        })
```

### 消息转换系统

```python
class MessageConverter:
    """消息格式转换器"""
    
    @staticmethod
    def to_openai_format(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """转换为OpenAI API格式"""
        
        openai_messages = []
        
        for message in messages:
            openai_msg = {
                "role": MessageConverter._get_openai_role(message),
                "content": MessageConverter._format_content_for_openai(message.content)
            }
            
            # 添加额外属性
            if message.name:
                openai_msg["name"] = message.name
            
            if isinstance(message, FunctionMessage):
                openai_msg["name"] = message.name
            
            if isinstance(message, ToolMessage):
                openai_msg["tool_call_id"] = message.tool_call_id
            
            # 添加函数调用信息
            if hasattr(message, 'additional_kwargs'):
                if 'function_call' in message.additional_kwargs:
                    openai_msg["function_call"] = message.additional_kwargs["function_call"]
                if 'tool_calls' in message.additional_kwargs:
                    openai_msg["tool_calls"] = message.additional_kwargs["tool_calls"]
            
            openai_messages.append(openai_msg)
        
        return openai_messages
    
    @staticmethod
    def _get_openai_role(message: BaseMessage) -> str:
        """获取OpenAI角色映射"""
        role_mapping = {
            "human": "user",
            "ai": "assistant", 
            "system": "system",
            "function": "function",
            "tool": "tool"
        }
        return role_mapping.get(message.type, "user")
    
    @staticmethod
    def _format_content_for_openai(content: Union[str, List]) -> Union[str, List]:
        """格式化内容为OpenAI格式"""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # 多模态内容直接返回
            return content
        else:
            return str(content)
    
    @staticmethod
    def to_anthropic_format(messages: List[BaseMessage]) -> Dict[str, Any]:
        """转换为Anthropic API格式"""
        
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        conversation_messages = [m for m in messages if not isinstance(m, SystemMessage)]
        
        # Anthropic格式
        result = {
            "messages": []
        }
        
        # 处理系统消息
        if system_messages:
            result["system"] = "\n".join(msg.content for msg in system_messages)
        
        # 处理对话消息
        for message in conversation_messages:
            anthropic_msg = {
                "role": MessageConverter._get_anthropic_role(message),
                "content": message.content
            }
            result["messages"].append(anthropic_msg)
        
        return result
    
    @staticmethod
    def _get_anthropic_role(message: BaseMessage) -> str:
        """获取Anthropic角色映射"""
        role_mapping = {
            "human": "user",
            "ai": "assistant"
        }
        return role_mapping.get(message.type, "user")
    
    @staticmethod
    def from_openai_response(response: Dict[str, Any]) -> BaseMessage:
        """从OpenAI响应创建消息"""
        
        choice = response["choices"][0]
        message_data = choice["message"]
        
        content = message_data.get("content", "")
        role = message_data.get("role", "assistant")
        
        # 创建对应的消息对象
        if role == "assistant":
            msg = AIMessage(content=content)
            
            # 处理函数调用
            if "function_call" in message_data:
                msg.additional_kwargs["function_call"] = message_data["function_call"]
            
            if "tool_calls" in message_data:
                msg.additional_kwargs["tool_calls"] = message_data["tool_calls"]
                
        elif role == "user":
            msg = HumanMessage(content=content)
        else:
            msg = SystemMessage(content=content)
        
        # 添加响应元数据
        if "usage" in response:
            msg.response_metadata["token_usage"] = response["usage"]
        
        if "model" in response:
            msg.response_metadata["model_name"] = response["model"]
        
        return msg

# 消息历史管理
class ChatMessageHistory:
    """聊天消息历史管理"""
    
    def __init__(self, messages: List[BaseMessage] = None):
        self.messages: List[BaseMessage] = messages or []
    
    def add_message(self, message: BaseMessage):
        """添加消息"""
        self.messages.append(message)
    
    def add_user_message(self, content: str):
        """添加用户消息"""
        self.add_message(HumanMessage(content=content))
    
    def add_ai_message(self, content: str):
        """添加AI消息"""
        self.add_message(AIMessage(content=content))
    
    def add_system_message(self, content: str):
        """添加系统消息"""
        self.add_message(SystemMessage(content=content))
    
    def get_messages(self) -> List[BaseMessage]:
        """获取所有消息"""
        return self.messages.copy()
    
    def clear(self):
        """清空消息历史"""
        self.messages.clear()
    
    def get_last_n_messages(self, n: int) -> List[BaseMessage]:
        """获取最近n条消息"""
        return self.messages[-n:] if n > 0 else []
    
    def filter_by_type(self, message_type: str) -> List[BaseMessage]:
        """按类型过滤消息"""
        return [msg for msg in self.messages if msg.type == message_type]
    
    def get_token_count(self, tokenizer_func: Callable[[str], int]) -> int:
        """计算总token数"""
        total_tokens = 0
        for message in self.messages:
            content_str = str(message.content)
            total_tokens += tokenizer_func(content_str)
        return total_tokens
    
    def trim_to_token_limit(self, max_tokens: int, tokenizer_func: Callable[[str], int]):
        """裁剪到token限制"""
        
        current_tokens = self.get_token_count(tokenizer_func)
        
        while current_tokens > max_tokens and len(self.messages) > 1:
            # 从最早的非系统消息开始删除
            for i, message in enumerate(self.messages):
                if not isinstance(message, SystemMessage):
                    removed_message = self.messages.pop(i)
                    removed_tokens = tokenizer_func(str(removed_message.content))
                    current_tokens -= removed_tokens
                    break
            else:
                # 如果只剩系统消息，删除最早的一条
                if self.messages:
                    removed_message = self.messages.pop(0)
                    removed_tokens = tokenizer_func(str(removed_message.content))
                    current_tokens -= removed_tokens
```

---

## 提供商集成模式

### 标准化集成接口

```python
# Provider抽象基类
class BaseLLMProvider(ABC):
    """LLM提供商抽象基类"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        pass
    
    @abstractmethod
    def create_chat_model(self, model_name: str, **kwargs) -> BaseChatModel:
        """创建对话模型实例"""
        pass
    
    @abstractmethod
    def create_llm_model(self, model_name: str, **kwargs) -> BaseLLM:
        """创建文本生成模型实例"""
        pass
    
    @abstractmethod
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    @abstractmethod
    def validate_api_key(self, api_key: str) -> bool:
        """验证API密钥"""
        pass

# OpenAI Provider实现
class OpenAIProvider(BaseLLMProvider):
    """OpenAI提供商实现"""
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "gpt-4",
            "gpt-4-32k", 
            "gpt-4-1106-preview",
            "gpt-4-vision-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "text-davinci-003",
            "text-curie-001",
            "text-babbage-001",
            "text-ada-001"
        ]
    
    def create_chat_model(self, model_name: str, **kwargs) -> ChatOpenAI:
        """创建OpenAI对话模型"""
        
        if model_name not in self.supported_models:
            raise ValueError(f"Unsupported model: {model_name}")
        
        # 应用默认配置
        default_config = {
            "temperature": 0.7,
            "max_tokens": None,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }
        
        config = {**default_config, **kwargs}
        config["model_name"] = model_name
        
        return ChatOpenAI(**config)
    
    def create_llm_model(self, model_name: str, **kwargs) -> OpenAI:
        """创建OpenAI文本生成模型"""
        
        if model_name not in self.supported_models:
            raise ValueError(f"Unsupported model: {model_name}")
        
        return OpenAI(model_name=model_name, **kwargs)
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息"""
        
        model_info = {
            "gpt-4": {
                "context_length": 8192,
                "training_data": "2021-09",
                "capabilities": ["text", "code", "reasoning"],
                "cost_per_1k_tokens": {"input": 0.03, "output": 0.06}
            },
            "gpt-4-vision-preview": {
                "context_length": 128000,
                "training_data": "2023-04",
                "capabilities": ["text", "code", "reasoning", "vision"],
                "cost_per_1k_tokens": {"input": 0.01, "output": 0.03}
            },
            "gpt-3.5-turbo": {
                "context_length": 4096,
                "training_data": "2021-09", 
                "capabilities": ["text", "code"],
                "cost_per_1k_tokens": {"input": 0.0015, "output": 0.002}
            }
        }
        
        return model_info.get(model_name, {})
    
    def validate_api_key(self, api_key: str) -> bool:
        """验证OpenAI API密钥"""
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            # 尝试调用models API
            client.models.list()
            return True
        except Exception:
            return False

# Anthropic Provider实现
class AnthropicProvider(BaseLLMProvider):
    """Anthropic提供商实现"""
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property 
    def supported_models(self) -> List[str]:
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
    
    def create_chat_model(self, model_name: str, **kwargs) -> ChatAnthropic:
        """创建Anthropic对话模型"""
        
        if model_name not in self.supported_models:
            raise ValueError(f"Unsupported model: {model_name}")
        
        return ChatAnthropic(model=model_name, **kwargs)
    
    def create_llm_model(self, model_name: str, **kwargs) -> Anthropic:
        """创建Anthropic文本生成模型"""
        
        if model_name not in self.supported_models:
            raise ValueError(f"Unsupported model: {model_name}")
        
        return Anthropic(model=model_name, **kwargs)
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取Anthropic模型信息"""
        
        model_info = {
            "claude-3-opus-20240229": {
                "context_length": 200000,
                "training_data": "2023-08",
                "capabilities": ["text", "code", "reasoning", "analysis"],
                "cost_per_1k_tokens": {"input": 0.015, "output": 0.075}
            },
            "claude-3-sonnet-20240229": {
                "context_length": 200000,
                "training_data": "2023-08",
                "capabilities": ["text", "code", "reasoning"],
                "cost_per_1k_tokens": {"input": 0.003, "output": 0.015}
            }
        }
        
        return model_info.get(model_name, {})
    
    def validate_api_key(self, api_key: str) -> bool:
        """验证Anthropic API密钥"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            # 这里可以添加具体的验证逻辑
            return True
        except Exception:
            return False

# Provider注册和管理系统
class LLMProviderRegistry:
    """LLM提供商注册表"""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._register_builtin_providers()
    
    def _register_builtin_providers(self):
        """注册内置提供商"""
        self.register_provider(OpenAIProvider())
        self.register_provider(AnthropicProvider())
    
    def register_provider(self, provider: BaseLLMProvider):
        """注册提供商"""
        self.providers[provider.provider_name] = provider
    
    def get_provider(self, provider_name: str) -> BaseLLMProvider:
        """获取提供商"""
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        return self.providers[provider_name]
    
    def list_providers(self) -> List[str]:
        """列出所有提供商"""
        return list(self.providers.keys())
    
    def get_supported_models(self, provider_name: str) -> List[str]:
        """获取支持的模型"""
        provider = self.get_provider(provider_name)
        return provider.supported_models
    
    def create_model(
        self, 
        provider_name: str, 
        model_name: str, 
        model_type: str = "chat",
        **kwargs
    ) -> Union[BaseChatModel, BaseLLM]:
        """创建模型实例"""
        
        provider = self.get_provider(provider_name)
        
        if model_type == "chat":
            return provider.create_chat_model(model_name, **kwargs)
        elif model_type == "llm":
            return provider.create_llm_model(model_name, **kwargs)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

# 全局提供商注册表实例
provider_registry = LLMProviderRegistry()

# 便捷的模型创建函数
def create_llm(
    provider: str, 
    model: str, 
    model_type: str = "chat",
    **kwargs
) -> Union[BaseChatModel, BaseLLM]:
    """便捷的模型创建函数"""
    return provider_registry.create_model(provider, model, model_type, **kwargs)

# 使用示例
def example_usage():
    """使用示例"""
    
    # 创建不同提供商的模型
    openai_model = create_llm("openai", "gpt-4", temperature=0.3)
    anthropic_model = create_llm("anthropic", "claude-3-sonnet-20240229", max_tokens=1000)
    
    # 统一的调用接口
    messages = [HumanMessage(content="Hello, how are you?")]
    
    openai_response = openai_model.invoke(messages)
    anthropic_response = anthropic_model.invoke(messages)
    
    print("OpenAI:", openai_response.content)
    print("Anthropic:", anthropic_response.content)
```

### 动态模型切换

```python
class LLMRouter:
    """LLM路由器 - 支持动态模型切换"""
    
    def __init__(self):
        self.models: Dict[str, BaseChatModel] = {}
        self.routing_rules: List[Callable] = []
        self.fallback_model: Optional[str] = None
        self.performance_monitor = ModelPerformanceMonitor()
    
    def register_model(self, name: str, model: BaseChatModel, is_fallback: bool = False):
        """注册模型"""
        self.models[name] = model
        if is_fallback:
            self.fallback_model = name
    
    def add_routing_rule(self, rule_func: Callable[[List[BaseMessage]], str]):
        """添加路由规则"""
        self.routing_rules.append(rule_func)
    
    def route_request(self, messages: List[BaseMessage]) -> str:
        """根据规则路由请求"""
        
        # 应用路由规则
        for rule in self.routing_rules:
            try:
                selected_model = rule(messages)
                if selected_model and selected_model in self.models:
                    return selected_model
            except Exception as e:
                logger.warning(f"Routing rule failed: {e}")
        
        # 基于性能选择模型
        best_model = self.performance_monitor.get_best_model()
        if best_model and best_model in self.models:
            return best_model
        
        # 使用备用模型
        if self.fallback_model:
            return self.fallback_model
        
        # 返回第一个可用模型
        return next(iter(self.models.keys())) if self.models else None
    
    def invoke(self, messages: List[BaseMessage], **kwargs) -> BaseMessage:
        """路由并调用模型"""
        
        selected_model_name = self.route_request(messages)
        if not selected_model_name:
            raise ValueError("No available models")
        
        model = self.models[selected_model_name]
        
        start_time = time.time()
        try:
            result = model.invoke(messages, **kwargs)
            
            # 记录性能数据
            execution_time = time.time() - start_time
            self.performance_monitor.record_success(
                selected_model_name, execution_time, len(messages)
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.performance_monitor.record_failure(
                selected_model_name, str(e), execution_time
            )
            
            # 尝试备用模型
            if selected_model_name != self.fallback_model and self.fallback_model:
                try:
                    fallback_model = self.models[self.fallback_model]
                    return fallback_model.invoke(messages, **kwargs)
                except Exception:
                    pass
            
            raise e

class ModelPerformanceMonitor:
    """模型性能监控器"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            'success_count': 0,
            'failure_count': 0,
            'total_time': 0.0,
            'average_time': 0.0,
            'success_rate': 0.0,
            'last_used': None,
            'recent_errors': []
        })
    
    def record_success(self, model_name: str, execution_time: float, input_size: int):
        """记录成功调用"""
        metrics = self.metrics[model_name]
        metrics['success_count'] += 1
        metrics['total_time'] += execution_time
        metrics['average_time'] = metrics['total_time'] / (metrics['success_count'] + metrics['failure_count'])
        metrics['success_rate'] = metrics['success_count'] / (metrics['success_count'] + metrics['failure_count'])
        metrics['last_used'] = time.time()
    
    def record_failure(self, model_name: str, error_message: str, execution_time: float):
        """记录失败调用"""
        metrics = self.metrics[model_name]
        metrics['failure_count'] += 1
        metrics['total_time'] += execution_time
        metrics['average_time'] = metrics['total_time'] / (metrics['success_count'] + metrics['failure_count'])
        metrics['success_rate'] = metrics['success_count'] / (metrics['success_count'] + metrics['failure_count'])
        
        # 记录最近的错误
        metrics['recent_errors'].append({
            'error': error_message,
            'timestamp': time.time()
        })
        
        # 只保留最近10个错误
        if len(metrics['recent_errors']) > 10:
            metrics['recent_errors'].pop(0)
    
    def get_best_model(self) -> Optional[str]:
        """获取性能最佳的模型"""
        if not self.metrics:
            return None
        
        # 综合评分：成功率 * 0.7 + 速度评分 * 0.3
        best_model = None
        best_score = -1
        
        for model_name, metrics in self.metrics.items():
            # 成功率评分
            success_score = metrics['success_rate']
            
            # 速度评分（越快分数越高）
            if metrics['average_time'] > 0:
                speed_score = 1.0 / (1.0 + metrics['average_time'])
            else:
                speed_score = 1.0
            
            # 最近使用情况（最近使用的加分）
            recency_score = 1.0
            if metrics['last_used']:
                time_since_used = time.time() - metrics['last_used']
                recency_score = max(0.1, 1.0 - time_since_used / 3600)  # 1小时内满分
            
            # 综合评分
            total_score = success_score * 0.5 + speed_score * 0.3 + recency_score * 0.2
            
            if total_score > best_score:
                best_score = total_score
                best_model = model_name
        
        return best_model
    
    def get_model_metrics(self, model_name: str) -> Dict[str, Any]:
        """获取模型指标"""
        return dict(self.metrics.get(model_name, {}))

# 路由规则示例
def create_routing_rules():
    """创建路由规则示例"""
    
    def long_context_rule(messages: List[BaseMessage]) -> Optional[str]:
        """长上下文路由规则"""
        total_content = ' '.join([str(msg.content) for msg in messages])
        if len(total_content) > 10000:  # 长文本使用Claude
            return "claude-3-sonnet"
        return None
    
    def code_task_rule(messages: List[BaseMessage]) -> Optional[str]:
        """代码任务路由规则"""
        for message in messages:
            content = str(message.content).lower()
            if any(keyword in content for keyword in ['code', 'python', 'javascript', 'programming']):
                return "gpt-4"  # GPT-4适合代码任务
        return None
    
    def creative_task_rule(messages: List[BaseMessage]) -> Optional[str]:
        """创意任务路由规则"""
        for message in messages:
            content = str(message.content).lower()
            if any(keyword in content for keyword in ['story', 'creative', 'imagine', 'write']):
                return "claude-3-opus"  # Claude适合创意任务
        return None
    
    return [long_context_rule, code_task_rule, creative_task_rule]

# 使用示例
def example_llm_routing():
    """LLM路由使用示例"""
    
    # 创建路由器
    router = LLMRouter()
    
    # 注册模型
    router.register_model("gpt-4", create_llm("openai", "gpt-4"))
    router.register_model("claude-3-sonnet", create_llm("anthropic", "claude-3-sonnet-20240229"))
    router.register_model("gpt-3.5-turbo", create_llm("openai", "gpt-3.5-turbo"), is_fallback=True)
    
    # 添加路由规则
    for rule in create_routing_rules():
        router.add_routing_rule(rule)
    
    # 测试不同类型的请求
    test_cases = [
        [HumanMessage(content="Write a Python function to calculate fibonacci numbers")],
        [HumanMessage(content="Tell me a creative story about a robot")],
        [HumanMessage(content="Analyze this long document: " + "A" * 15000)]
    ]
    
    for messages in test_cases:
        try:
            response = router.invoke(messages)
            print(f"Input: {messages[0].content[:50]}...")
            print(f"Response: {response.content[:100]}...")
            print("---")
        except Exception as e:
            print(f"Error: {e}")
```

---

## 类型系统与泛型

### 高级类型定义

```python
from typing import TypeVar, Generic, Protocol, Union, Optional, List, Dict, Any, Callable
from typing_extensions import ParamSpec, Concatenate

# 类型变量定义
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')
ConfigT = TypeVar('ConfigT', bound='RunnableConfig')
P = ParamSpec('P')

# 协议定义
class LLMProtocol(Protocol[InputT, OutputT]):
    """LLM协议定义"""
    
    def invoke(self, input: InputT, config: Optional[ConfigT] = None) -> OutputT:
        """调用协议"""
        ...
    
    async def ainvoke(self, input: InputT, config: Optional[ConfigT] = None) -> OutputT:
        """异步调用协议"""
        ...
    
    def batch(self, inputs: List[InputT], config: Optional[ConfigT] = None) -> List[OutputT]:
        """批处理协议"""
        ...

# 泛型LLM基类
class GenericLLM(Generic[InputT, OutputT]):
    """泛型LLM实现"""
    
    def __init__(self, 
                 input_processor: Callable[[InputT], Any],
                 output_processor: Callable[[Any], OutputT],
                 model_client: Any):
        self.input_processor = input_processor
        self.output_processor = output_processor
        self.model_client = model_client
    
    def invoke(self, input: InputT, config: Optional[RunnableConfig] = None) -> OutputT:
        """类型安全的调用实现"""
        # 输入处理
        processed_input = self.input_processor(input)
        
        # 模型调用
        raw_output = self.model_client.invoke(processed_input)
        
        # 输出处理
        return self.output_processor(raw_output)
    
    def batch(self, inputs: List[InputT], config: Optional[RunnableConfig] = None) -> List[OutputT]:
        """批处理实现"""
        processed_inputs = [self.input_processor(inp) for inp in inputs]
        raw_outputs = self.model_client.batch(processed_inputs)
        return [self.output_processor(out) for out in raw_outputs]

# 具体类型化实现
class TypedChatModel(GenericLLM[List[BaseMessage], BaseMessage]):
    """类型化的对话模型"""
    
    def __init__(self, model_client):
        super().__init__(
            input_processor=self._process_messages,
            output_processor=self._process_response,
            model_client=model_client
        )
    
    def _process_messages(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """处理消息输入"""
        return {
            "messages": MessageConverter.to_openai_format(messages)
        }
    
    def _process_response(self, raw_response: Dict[str, Any]) -> BaseMessage:
        """处理响应输出"""
        return MessageConverter.from_openai_response(raw_response)

class TypedTextModel(GenericLLM[str, str]):
    """类型化的文本模型"""
    
    def __init__(self, model_client):
        super().__init__(
            input_processor=self._process_text,
            output_processor=self._process_response,
            model_client=model_client
        )
    
    def _process_text(self, text: str) -> Dict[str, Any]:
        """处理文本输入"""
        return {"prompt": text}
    
    def _process_response(self, raw_response: Dict[str, Any]) -> str:
        """处理响应输出"""
        return raw_response.get("text", "")

# 类型约束的装饰器
def typed_llm_method(input_type: type, output_type: type):
    """类型约束装饰器"""
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self, input_data, *args, **kwargs):
            # 运行时类型检查
            if not isinstance(input_data, input_type):
                raise TypeError(f"Expected input type {input_type}, got {type(input_data)}")
            
            result = func(self, input_data, *args, **kwargs)
            
            if not isinstance(result, output_type):
                raise TypeError(f"Expected output type {output_type}, got {type(result)}")
            
            return result
        
        # 保留函数元数据
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__annotations__ = func.__annotations__
        
        return wrapper
    
    return decorator

# 使用示例
class StrictTypedLLM:
    """严格类型检查的LLM"""
    
    @typed_llm_method(List[BaseMessage], BaseMessage)
    def chat(self, messages: List[BaseMessage]) -> BaseMessage:
        """严格类型检查的对话方法"""
        # 实现逻辑
        return AIMessage(content="Response")
    
    @typed_llm_method(str, str) 
    def complete(self, prompt: str) -> str:
        """严格类型检查的文本完成方法"""
        # 实现逻辑
        return "Completion"

# 类型推断工具
class TypeInferencer:
    """类型推断工具"""
    
    @staticmethod
    def infer_input_type(llm_instance: Any) -> Optional[type]:
        """推断LLM的输入类型"""
        
        # 检查类型注解
        if hasattr(llm_instance, '__orig_bases__'):
            for base in llm_instance.__orig_bases__:
                if hasattr(base, '__args__') and len(base.__args__) >= 1:
                    return base.__args__[0]
        
        # 检查方法签名
        if hasattr(llm_instance, 'invoke'):
            sig = inspect.signature(llm_instance.invoke)
            for param in sig.parameters.values():
                if param.name == 'input' and param.annotation != inspect.Parameter.empty:
                    return param.annotation
        
        return None
    
    @staticmethod
    def infer_output_type(llm_instance: Any) -> Optional[type]:
        """推断LLM的输出类型"""
        
        # 检查类型注解
        if hasattr(llm_instance, '__orig_bases__'):
            for base in llm_instance.__orig_bases__:
                if hasattr(base, '__args__') and len(base.__args__) >= 2:
                    return base.__args__[1]
        
        # 检查返回值注解
        if hasattr(llm_instance, 'invoke'):
            sig = inspect.signature(llm_instance.invoke)
            if sig.return_annotation != inspect.Parameter.empty:
                return sig.return_annotation
        
        return None
    
    @staticmethod
    def validate_type_compatibility(llm1: Any, llm2: Any) -> bool:
        """验证两个LLM的类型兼容性"""
        
        llm1_input = TypeInferencer.infer_input_type(llm1)
        llm1_output = TypeInferencer.infer_output_type(llm1)
        
        llm2_input = TypeInferencer.infer_input_type(llm2)
        llm2_output = TypeInferencer.infer_output_type(llm2)
        
        # 检查输入输出类型是否匹配
        return (llm1_input == llm2_input and llm1_output == llm2_output)
```

---

## 异步与并发处理

### 异步执行架构

```python
import asyncio
from typing import AsyncIterator
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
from contextlib import asynccontextmanager

class AsyncLLMBase(BaseChatModel):
    """异步LLM基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session: Optional[aiohttp.ClientSession] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=300)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
            self.session = None
    
    @asynccontextmanager
    async def _get_session(self):
        """获取HTTP会话的上下文管理器"""
        if self.session is None:
            async with aiohttp.ClientSession() as session:
                yield session
        else:
            yield self.session
    
    async def ainvoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        """异步调用实现"""
        
        # 处理输入
        messages = self._prepare_messages(input)
        
        # 异步API调用
        async with self._get_session() as session:
            response = await self._async_api_call(session, messages, **kwargs)
        
        # 处理响应
        return self._process_response(response)
    
    async def abatch(
        self,
        inputs: List[LanguageModelInput],
        config: Optional[Union[RunnableConfig, List[RunnableConfig]]] = None,
        **kwargs: Any,
    ) -> List[BaseMessage]:
        """异步批处理实现"""
        
        # 准备配置
        if config is None:
            configs = [None] * len(inputs)
        elif isinstance(config, dict):
            configs = [config] * len(inputs)
        else:
            configs = config
        
        # 并发执行
        tasks = []
        async with self._get_session() as session:
            for inp, cfg in zip(inputs, configs):
                task = self._async_single_call(session, inp, cfg, **kwargs)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                # 可以选择重新抛出异常或返回错误消息
                final_results.append(AIMessage(content=f"Error: {str(result)}"))
            else:
                final_results.append(result)
        
        return final_results
    
    async def astream(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> AsyncIterator[BaseMessage]:
        """异步流式处理实现"""
        
        messages = self._prepare_messages(input)
        
        async with self._get_session() as session:
            async for chunk in self._async_stream_call(session, messages, **kwargs):
                yield chunk
    
    async def _async_api_call(
        self,
        session: aiohttp.ClientSession,
        messages: List[BaseMessage],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """异步API调用的具体实现"""
        
        # 准备请求数据
        request_data = self._prepare_request(messages, **kwargs)
        
        # 发送请求
        async with session.post(
            self.api_url,
            json=request_data,
            headers=self._get_headers()
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def _async_single_call(
        self,
        session: aiohttp.ClientSession,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        """单个异步调用"""
        
        messages = self._prepare_messages(input)
        response = await self._async_api_call(session, messages, **kwargs)
        return self._process_response(response)
    
    async def _async_stream_call(
        self,
        session: aiohttp.ClientSession,
        messages: List[BaseMessage],
        **kwargs: Any,
    ) -> AsyncIterator[BaseMessage]:
        """异步流式调用"""
        
        # 准备流式请求数据
        request_data = self._prepare_request(messages, stream=True, **kwargs)
        
        async with session.post(
            self.api_url,
            json=request_data,
            headers=self._get_headers()
        ) as response:
            response.raise_for_status()
            
            # 处理流式响应
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if chunk := self._process_stream_chunk(data):
                            yield chunk
                    except json.JSONDecodeError:
                        continue

# 并发控制器
class ConcurrencyController:
    """并发控制器"""
    
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = RateLimiter()
    
    async def execute_with_concurrency_control(
        self,
        coro_func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> Any:
        """并发控制执行"""
        
        async with self.semaphore:
            await self.rate_limiter.acquire()
            try:
                return await coro_func(*args, **kwargs)
            finally:
                self.rate_limiter.release()

class RateLimiter:
    """速率限制器"""
    
    def __init__(self, 
                 requests_per_minute: int = 60,
                 tokens_per_minute: int = 40000):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        
        self.request_times: List[float] = []
        self.token_usage: List[Tuple[float, int]] = []  # (timestamp, tokens)
        
        self._lock = asyncio.Lock()
    
    async def acquire(self, estimated_tokens: int = 1000):
        """获取速率限制许可"""
        
        async with self._lock:
            current_time = time.time()
            
            # 清理过期记录
            self._cleanup_old_records(current_time)
            
            # 检查请求速率
            if len(self.request_times) >= self.requests_per_minute:
                wait_time = 60 - (current_time - self.request_times[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire(estimated_tokens)
            
            # 检查token速率
            total_tokens = sum(tokens for _, tokens in self.token_usage)
            if total_tokens + estimated_tokens > self.tokens_per_minute:
                if self.token_usage:
                    wait_time = 60 - (current_time - self.token_usage[0][0])
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                        return await self.acquire(estimated_tokens)
            
            # 记录本次请求
            self.request_times.append(current_time)
            self.token_usage.append((current_time, estimated_tokens))
    
    def release(self):
        """释放速率限制（占位方法）"""
        pass
    
    def _cleanup_old_records(self, current_time: float):
        """清理过期记录"""
        cutoff_time = current_time - 60
        
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t > cutoff_time]

# 批处理优化器
class BatchProcessor:
    """批处理优化器"""
    
    def __init__(self, 
                 batch_size: int = 10,
                 max_wait_time: float = 1.0,
                 max_queue_size: int = 100):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.max_queue_size = max_queue_size
        
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.processing_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    async def start(self):
        """启动批处理器"""
        if self.processing_task is None:
            self.processing_task = asyncio.create_task(self._process_batches())
    
    async def stop(self):
        """停止批处理器"""
        self._shutdown = True
        if self.processing_task:
            await self.processing_task
    
    async def submit(self, llm: AsyncLLMBase, input_data: Any, **kwargs) -> Any:
        """提交批处理请求"""
        
        future = asyncio.Future()
        request = {
            'llm': llm,
            'input': input_data,
            'kwargs': kwargs,
            'future': future
        }
        
        try:
            await self.queue.put(request)
            return await future
        except asyncio.QueueFull:
            # 队列满时直接执行
            return await llm.ainvoke(input_data, **kwargs)
    
    async def _process_batches(self):
        """处理批次的主循环"""
        
        while not self._shutdown:
            batch = []
            batch_deadline = time.time() + self.max_wait_time
            
            try:
                # 收集批次
                while len(batch) < self.batch_size and time.time() < batch_deadline:
                    timeout = max(0.1, batch_deadline - time.time())
                    
                    try:
                        request = await asyncio.wait_for(
                            self.queue.get(), timeout=timeout
                        )
                        batch.append(request)
                    except asyncio.TimeoutError:
                        break
                
                if batch:
                    await self._execute_batch(batch)
                    
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                # 处理批次中的所有future
                for request in batch:
                    if not request['future'].done():
                        request['future'].set_exception(e)
    
    async def _execute_batch(self, batch: List[Dict]):
        """执行批次"""
        
        # 按LLM分组
        llm_groups = {}
        for request in batch:
            llm = request['llm']
            if llm not in llm_groups:
                llm_groups[llm] = []
            llm_groups[llm].append(request)
        
        # 并发执行各组
        tasks = []
        for llm, requests in llm_groups.items():
            task = self._execute_llm_batch(llm, requests)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def _execute_llm_batch(self, llm: AsyncLLMBase, requests: List[Dict]):
        """执行单个LLM的批次"""
        
        try:
            inputs = [req['input'] for req in requests]
            results = await llm.abatch(inputs)
            
            # 分发结果
            for request, result in zip(requests, results):
                if not request['future'].done():
                    request['future'].set_result(result)
                    
        except Exception as e:
            # 分发错误
            for request in requests:
                if not request['future'].done():
                    request['future'].set_exception(e)

# 使用示例
async def example_async_usage():
    """异步使用示例"""
    
    # 创建异步LLM实例
    async with AsyncChatOpenAI(temperature=0.7) as llm:
        
        # 单个异步调用
        messages = [HumanMessage(content="Hello, world!")]
        response = await llm.ainvoke(messages)
        print("Single call:", response.content)
        
        # 批量异步调用
        batch_inputs = [
            [HumanMessage(content=f"Tell me a joke #{i}")]
            for i in range(5)
        ]
        batch_results = await llm.abatch(batch_inputs)
        for i, result in enumerate(batch_results):
            print(f"Batch {i}:", result.content[:50])
        
        # 异步流式处理
        print("Streaming:")
        async for chunk in llm.astream(messages):
            print(chunk.content, end="", flush=True)
        print()

# 并发控制使用示例
async def example_concurrent_usage():
    """并发控制使用示例"""
    
    controller = ConcurrencyController(max_concurrent=5)
    
    async def make_llm_call(prompt: str) -> str:
        llm = AsyncChatOpenAI()
        messages = [HumanMessage(content=prompt)]
        result = await llm.ainvoke(messages)
        return result.content
    
    # 并发控制的多个调用
    prompts = [f"Question {i}: What is AI?" for i in range(20)]
    
    tasks = [
        controller.execute_with_concurrency_control(make_llm_call, prompt)
        for prompt in prompts
    ]
    
    results = await asyncio.gather(*tasks)
    
    for i, result in enumerate(results):
        print(f"Result {i}: {result[:50]}...")

# 批处理器使用示例
async def example_batch_processor():
    """批处理器使用示例"""
    
    processor = BatchProcessor(batch_size=5, max_wait_time=2.0)
    await processor.start()
    
    try:
        llm = AsyncChatOpenAI()
        
        # 提交多个请求（会自动批处理）
        tasks = []
        for i in range(15):
            messages = [HumanMessage(content=f"Question {i}: Explain quantum computing")]
            task = processor.submit(llm, messages)
            tasks.append(task)
        
        # 等待所有结果
        results = await asyncio.gather(*tasks)
        
        for i, result in enumerate(results):
            print(f"Batched result {i}: {result.content[:50]}...")
            
    finally:
        await processor.stop()
```

---

## 错误处理与重试

### 统一错误体系

```python
# LLM错误类型定义
class LLMError(Exception):
    """LLM相关错误的基类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 retry_after: Optional[float] = None):
        super().__init__(message)
        self.error_code = error_code
        self.retry_after = retry_after
        self.timestamp = time.time()

class RateLimitError(LLMError):
    """速率限制错误"""
    
    def __init__(self, message: str, retry_after: float = 60.0, **kwargs):
        super().__init__(message, retry_after=retry_after, **kwargs)

class QuotaExceededError(LLMError):
    """配额超限错误"""
    pass

class InvalidRequestError(LLMError):
    """无效请求错误"""
    pass

class AuthenticationError(LLMError):
    """认证错误"""
    pass

class ServiceUnavailableError(LLMError):
    """服务不可用错误"""
    
    def __init__(self, message: str, retry_after: float = 30.0, **kwargs):
        super().__init__(message, retry_after=retry_after, **kwargs)

class ContextLengthExceededError(LLMError):
    """上下文长度超限错误"""
    
    def __init__(self, message: str, max_length: int, actual_length: int, **kwargs):
        super().__init__(message, **kwargs)
        self.max_length = max_length
        self.actual_length = actual_length

class ContentFilterError(LLMError):
    """内容过滤错误"""
    pass

# 错误分类器
class ErrorClassifier:
    """错误分类器"""
    
    @staticmethod
    def classify_error(error: Exception) -> str:
        """分类错误类型"""
        
        error_message = str(error).lower()
        
        # 速率限制
        if any(keyword in error_message for keyword in ['rate limit', 'too many requests', 'quota']):
            return 'rate_limit'
        
        # 认证问题
        if any(keyword in error_message for keyword in ['unauthorized', 'invalid key', 'authentication']):
            return 'authentication'
        
        # 服务问题
        if any(keyword in error_message for keyword in ['service unavailable', 'server error', '502', '503']):
            return 'service_unavailable'
        
        # 请求问题
        if any(keyword in error_message for keyword in ['invalid request', 'bad request', '400']):
            return 'invalid_request'
        
        # 上下文长度
        if any(keyword in error_message for keyword in ['context length', 'maximum context', 'token limit']):
            return 'context_length'
        
        # 内容过滤
        if any(keyword in error_message for keyword in ['content filter', 'safety', 'policy violation']):
            return 'content_filter'
        
        # 网络问题
        if any(keyword in error_message for keyword in ['connection', 'timeout', 'network']):
            return 'network'
        
        return 'unknown'
    
    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """判断错误是否可重试"""
        
        error_type = ErrorClassifier.classify_error(error)
        
        retryable_errors = {
            'rate_limit': True,
            'service_unavailable': True, 
            'network': True,
            'unknown': True  # 未知错误保守重试
        }
        
        non_retryable_errors = {
            'authentication': False,
            'invalid_request': False,
            'context_length': False,
            'content_filter': False
        }
        
        return retryable_errors.get(error_type, False)
    
    @staticmethod
    def get_retry_delay(error: Exception, attempt: int) -> float:
        """获取重试延迟时间"""
        
        error_type = ErrorClassifier.classify_error(error)
        
        # 特定错误类型的延迟策略
        if error_type == 'rate_limit':
            # 检查是否有retry_after信息
            if hasattr(error, 'retry_after'):
                return error.retry_after
            return min(60, 2 ** attempt)  # 指数退避，最大60秒
        
        elif error_type == 'service_unavailable':
            return min(30, 2 ** attempt)
        
        elif error_type == 'network':
            return min(10, 2 ** attempt)
        
        else:
            return min(5, 2 ** (attempt - 1))

# 重试装饰器
def retry_llm_call(max_attempts: int = 3,
                   backoff_factor: float = 1.0,
                   jitter: bool = True,
                   on_retry: Optional[Callable] = None):
    """LLM调用重试装饰器"""
    
    def decorator(func):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否可重试
                    if not ErrorClassifier.is_retryable(e) or attempt == max_attempts - 1:
                        raise
                    
                    # 计算延迟时间
                    delay = ErrorClassifier.get_retry_delay(e, attempt + 1) * backoff_factor
                    
                    # 添加随机抖动
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    # 调用重试回调
                    if on_retry:
                        on_retry(e, attempt + 1, delay)
                    
                    # 等待后重试
                    time.sleep(delay)
            
            raise last_exception
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否可重试
                    if not ErrorClassifier.is_retryable(e) or attempt == max_attempts - 1:
                        raise
                    
                    # 计算延迟时间
                    delay = ErrorClassifier.get_retry_delay(e, attempt + 1) * backoff_factor
                    
                    # 添加随机抖动
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    # 调用重试回调
                    if on_retry:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(e, attempt + 1, delay)
                        else:
                            on_retry(e, attempt + 1, delay)
                    
                    # 等待后重试
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        # 根据函数类型返回对应包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# 重试回调示例
def log_retry(error: Exception, attempt: int, delay: float):
    """记录重试信息"""
    logger.warning(f"LLM call failed (attempt {attempt}), retrying in {delay:.2f}s: {error}")

# 带重试的LLM实现
class ReliableLLM(BaseChatModel):
    """带重试机制的可靠LLM"""
    
    def __init__(self, base_llm: BaseChatModel, 
                 max_retries: int = 3,
                 backoff_factor: float = 1.0):
        super().__init__()
        self.base_llm = base_llm
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        # 错误统计
        self.error_stats = defaultdict(int)
        self.total_calls = 0
        self.failed_calls = 0
    
    @retry_llm_call(max_attempts=3, on_retry=log_retry)
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """带重试的生成方法"""
        
        self.total_calls += 1
        
        try:
            result = self.base_llm._generate(messages, stop, run_manager, **kwargs)
            return result
        
        except Exception as e:
            self.failed_calls += 1
            error_type = ErrorClassifier.classify_error(e)
            self.error_stats[error_type] += 1
            
            # 转换为标准LLM错误
            raise self._convert_to_llm_error(e)
    
    def _convert_to_llm_error(self, error: Exception) -> LLMError:
        """将普通异常转换为LLM错误"""
        
        error_type = ErrorClassifier.classify_error(error)
        error_message = str(error)
        
        if error_type == 'rate_limit':
            return RateLimitError(error_message)
        elif error_type == 'authentication':
            return AuthenticationError(error_message)
        elif error_type == 'service_unavailable':
            return ServiceUnavailableError(error_message)
        elif error_type == 'invalid_request':
            return InvalidRequestError(error_message)
        elif error_type == 'context_length':
            return ContextLengthExceededError(error_message, 0, 0)
        elif error_type == 'content_filter':
            return ContentFilterError(error_message)
        else:
            return LLMError(error_message)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        
        success_rate = ((self.total_calls - self.failed_calls) / self.total_calls * 100) if self.total_calls > 0 else 0
        
        return {
            'total_calls': self.total_calls,
            'failed_calls': self.failed_calls,
            'success_rate': f"{success_rate:.2f}%",
            'error_breakdown': dict(self.error_stats),
            'most_common_error': max(self.error_stats.items(), key=lambda x: x[1])[0] if self.error_stats else None
        }
    
    @property
    def _llm_type(self) -> str:
        return f"reliable_{self.base_llm._llm_type}"

# 容错链路实现
class FallbackLLM(BaseChatModel):
    """容错链路LLM"""
    
    def __init__(self, primary_llm: BaseChatModel, 
                 fallback_llms: List[BaseChatModel]):
        super().__init__()
        self.primary_llm = primary_llm
        self.fallback_llms = fallback_llms
        self.all_llms = [primary_llm] + fallback_llms
        
        # 健康检查状态
        self.llm_health = {llm: True for llm in self.all_llms}
        self.last_health_check = time.time()
        self.health_check_interval = 300  # 5分钟
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """容错生成方法"""
        
        # 定期健康检查
        self._perform_health_check_if_needed()
        
        last_exception = None
        
        # 按优先级尝试所有LLM
        for llm in self.all_llms:
            # 跳过不健康的LLM
            if not self.llm_health.get(llm, True):
                continue
            
            try:
                result = llm._generate(messages, stop, run_manager, **kwargs)
                
                # 标记为健康
                self.llm_health[llm] = True
                
                # 如果不是主LLM成功，记录日志
                if llm != self.primary_llm:
                    logger.info(f"Fallback LLM {llm.__class__.__name__} succeeded")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # 根据错误类型决定是否标记为不健康
                if not ErrorClassifier.is_retryable(e):
                    self.llm_health[llm] = False
                    logger.warning(f"LLM {llm.__class__.__name__} marked as unhealthy: {e}")
                
                # 记录回退
                logger.warning(f"LLM {llm.__class__.__name__} failed, trying next: {e}")
                continue
        
        # 所有LLM都失败
        raise LLMError(f"All LLMs failed. Last error: {last_exception}")
    
    def _perform_health_check_if_needed(self):
        """根据需要执行健康检查"""
        
        current_time = time.time()
        if current_time - self.last_health_check > self.health_check_interval:
            self._perform_health_check()
            self.last_health_check = current_time
    
    def _perform_health_check(self):
        """执行健康检查"""
        
        test_message = [HumanMessage(content="Health check")]
        
        for llm in self.all_llms:
            try:
                # 简单的健康检查调用
                llm._generate(test_message, max_tokens=1)
                self.llm_health[llm] = True
            except Exception as e:
                # 某些错误类型仍然认为是健康的
                if ErrorClassifier.is_retryable(e):
                    self.llm_health[llm] = True
                else:
                    self.llm_health[llm] = False
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        
        return {
            'primary_healthy': self.llm_health.get(self.primary_llm, True),
            'total_llms': len(self.all_llms),
            'healthy_llms': sum(self.llm_health.values()),
            'last_health_check': self.last_health_check,
            'health_details': {
                llm.__class__.__name__: status
                for llm, status in self.llm_health.items()
            }
        }
    
    @property
    def _llm_type(self) -> str:
        return f"fallback_{self.primary_llm._llm_type}"

# 使用示例
def example_error_handling():
    """错误处理使用示例"""
    
    # 创建可靠的LLM
    base_llm = ChatOpenAI(temperature=0.7)
    reliable_llm = ReliableLLM(base_llm, max_retries=3)
    
    # 创建容错链路
    primary_llm = ChatOpenAI()
    fallback_llm1 = ChatAnthropic()
    fallback_llm2 = ChatOpenAI(model="gpt-3.5-turbo")
    
    fault_tolerant_llm = FallbackLLM(primary_llm, [fallback_llm1, fallback_llm2])
    
    # 测试调用
    messages = [HumanMessage(content="Tell me about quantum computing")]
    
    try:
        # 使用可靠LLM
        result1 = reliable_llm.invoke(messages)
        print("Reliable LLM:", result1.content[:100])
        
        # 使用容错LLM
        result2 = fault_tolerant_llm.invoke(messages)
        print("Fault-tolerant LLM:", result2.content[:100])
        
    except LLMError as e:
        print(f"LLM Error: {e}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'retry_after'):
            print(f"Retry after: {e.retry_after} seconds")
    
    # 查看统计信息
    print("\nReliable LLM Stats:", reliable_llm.get_error_stats())
    print("Fault-tolerant LLM Health:", fault_tolerant_llm.get_health_status())
```

---

## 实际集成案例

### 多提供商智能路由

```python
class IntelligentLLMRouter:
    """智能LLM路由系统"""
    
    def __init__(self):
        self.providers = {}
        self.routing_strategies = []
        self.performance_tracker = PerformanceTracker()
        self.cost_tracker = CostTracker()
        self.load_balancer = LoadBalancer()
    
    def register_provider(self, name: str, llm: BaseChatModel, config: Dict[str, Any]):
        """注册LLM提供商"""
        
        self.providers[name] = {
            'llm': llm,
            'config': config,
            'capabilities': config.get('capabilities', []),
            'cost_per_token': config.get('cost_per_token', 0),
            'max_tokens': config.get('max_tokens', 4096),
            'supports_vision': config.get('supports_vision', False),
            'supports_function_calling': config.get('supports_function_calling', False)
        }
    
    def add_routing_strategy(self, strategy: 'RoutingStrategy'):
        """添加路由策略"""
        self.routing_strategies.append(strategy)
    
    def route_request(self, messages: List[BaseMessage], requirements: Dict[str, Any] = None) -> str:
        """智能路由请求"""
        
        requirements = requirements or {}
        
        # 应用路由策略
        for strategy in self.routing_strategies:
            selected = strategy.select_provider(messages, self.providers, requirements)
            if selected:
                return selected
        
        # 基于性能和成本的综合评分
        return self._select_by_score(messages, requirements)
    
    def _select_by_score(self, messages: List[BaseMessage], requirements: Dict[str, Any]) -> str:
        """基于综合评分选择提供商"""
        
        best_provider = None
        best_score = -1
        
        for provider_name, provider_info in self.providers.items():
            # 检查基本要求
            if not self._meets_requirements(provider_info, requirements):
                continue
            
            # 计算综合评分
            score = self._calculate_provider_score(provider_name, messages, requirements)
            
            if score > best_score:
                best_score = score
                best_provider = provider_name
        
        return best_provider
    
    def _meets_requirements(self, provider_info: Dict, requirements: Dict) -> bool:
        """检查提供商是否满足要求"""
        
        # 检查token限制
        if requirements.get('max_tokens', 0) > provider_info['max_tokens']:
            return False
        
        # 检查视觉能力
        if requirements.get('requires_vision', False) and not provider_info['supports_vision']:
            return False
        
        # 检查函数调用能力
        if requirements.get('requires_function_calling', False) and not provider_info['supports_function_calling']:
            return False
        
        # 检查预算限制
        if requirements.get('max_cost_per_token', float('inf')) < provider_info['cost_per_token']:
            return False
        
        return True
    
    def _calculate_provider_score(self, provider_name: str, messages: List[BaseMessage], requirements: Dict) -> float:
        """计算提供商综合评分"""
        
        # 性能评分 (40%)
        performance_metrics = self.performance_tracker.get_metrics(provider_name)
        performance_score = (
            performance_metrics['success_rate'] * 0.6 +
            (1.0 / max(performance_metrics['avg_response_time'], 0.1)) * 0.4
        )
        
        # 成本评分 (30%)
        cost_score = 1.0 / (1.0 + self.providers[provider_name]['cost_per_token'] * 1000)
        
        # 负载评分 (20%)
        load_score = self.load_balancer.get_load_score(provider_name)
        
        # 能力匹配评分 (10%)
        capability_score = self._calculate_capability_match(provider_name, requirements)
        
        # 综合评分
        total_score = (
            performance_score * 0.4 +
            cost_score * 0.3 +
            load_score * 0.2 +
            capability_score * 0.1
        )
        
        return total_score
    
    def _calculate_capability_match(self, provider_name: str, requirements: Dict) -> float:
        """计算能力匹配度"""
        
        provider_capabilities = set(self.providers[provider_name]['capabilities'])
        required_capabilities = set(requirements.get('preferred_capabilities', []))
        
        if not required_capabilities:
            return 1.0
        
        intersection = provider_capabilities & required_capabilities
        return len(intersection) / len(required_capabilities)
    
    async def invoke_with_routing(
        self, 
        messages: List[BaseMessage], 
        requirements: Dict[str, Any] = None,
        **kwargs
    ) -> BaseMessage:
        """路由并调用LLM"""
        
        # 选择提供商
        selected_provider = self.route_request(messages, requirements)
        if not selected_provider:
            raise ValueError("No suitable provider found")
        
        provider_info = self.providers[selected_provider]
        llm = provider_info['llm']
        
        # 记录开始时间
        start_time = time.time()
        token_count = self._estimate_token_count(messages)
        
        try:
            # 执行调用
            result = await llm.ainvoke(messages, **kwargs)
            
            # 记录成功指标
            response_time = time.time() - start_time
            self.performance_tracker.record_success(selected_provider, response_time, token_count)
            
            # 记录成本
            cost = token_count * provider_info['cost_per_token']
            self.cost_tracker.record_usage(selected_provider, token_count, cost)
            
            # 更新负载均衡器
            self.load_balancer.record_request(selected_provider, response_time)
            
            return result
        
        except Exception as e:
            # 记录失败指标
            response_time = time.time() - start_time
            self.performance_tracker.record_failure(selected_provider, str(e), response_time)
            
            # 尝试故障转移
            fallback_provider = self._select_fallback_provider(selected_provider, requirements)
            if fallback_provider:
                logger.info(f"Failing over from {selected_provider} to {fallback_provider}")
                fallback_llm = self.providers[fallback_provider]['llm']
                return await fallback_llm.ainvoke(messages, **kwargs)
            
            raise
    
    def _estimate_token_count(self, messages: List[BaseMessage]) -> int:
        """估算token数量"""
        total_content = ' '.join([str(msg.content) for msg in messages])
        return len(total_content) // 4  # 粗略估算
    
    def _select_fallback_provider(self, failed_provider: str, requirements: Dict) -> Optional[str]:
        """选择备用提供商"""
        
        available_providers = [
            name for name in self.providers.keys() 
            if name != failed_provider and self._meets_requirements(self.providers[name], requirements)
        ]
        
        if not available_providers:
            return None
        
        # 选择负载最低的提供商
        return min(available_providers, key=lambda p: self.load_balancer.get_current_load(p))

# 路由策略基类和实现
class RoutingStrategy(ABC):
    """路由策略抽象基类"""
    
    @abstractmethod
    def select_provider(
        self, 
        messages: List[BaseMessage], 
        providers: Dict[str, Any], 
        requirements: Dict[str, Any]
    ) -> Optional[str]:
        """选择提供商"""
        pass

class TaskBasedRoutingStrategy(RoutingStrategy):
    """基于任务类型的路由策略"""
    
    def __init__(self):
        self.task_provider_map = {
            'code': ['gpt-4', 'claude-3-sonnet'],
            'creative': ['claude-3-opus', 'gpt-4'],
            'analysis': ['gpt-4', 'claude-3-sonnet'],
            'translation': ['gpt-3.5-turbo', 'claude-3-haiku'],
            'conversation': ['gpt-3.5-turbo', 'claude-3-haiku']
        }
    
    def select_provider(
        self, 
        messages: List[BaseMessage], 
        providers: Dict[str, Any], 
        requirements: Dict[str, Any]
    ) -> Optional[str]:
        """根据任务类型选择提供商"""
        
        # 分析消息内容判断任务类型
        content = ' '.join([str(msg.content) for msg in messages]).lower()
        
        detected_task = None
        for task_type, keywords in {
            'code': ['code', 'function', 'algorithm', 'programming', 'debug'],
            'creative': ['story', 'creative', 'imagine', 'write', 'poem'],
            'analysis': ['analyze', 'compare', 'explain', 'research', 'study'],
            'translation': ['translate', 'language', '翻译'],
            'conversation': ['hello', 'how are you', 'chat', 'talk']
        }.items():
            if any(keyword in content for keyword in keywords):
                detected_task = task_type
                break
        
        if detected_task and detected_task in self.task_provider_map:
            preferred_providers = self.task_provider_map[detected_task]
            
            # 返回第一个可用的偏好提供商
            for provider_name in preferred_providers:
                if provider_name in providers:
                    return provider_name
        
        return None

class CostOptimizedRoutingStrategy(RoutingStrategy):
    """成本优化路由策略"""
    
    def select_provider(
        self, 
        messages: List[BaseMessage], 
        providers: Dict[str, Any], 
        requirements: Dict[str, Any]
    ) -> Optional[str]:
        """选择成本最低的提供商"""
        
        # 如果要求成本优化，选择最便宜的提供商
        if requirements.get('optimize_cost', False):
            cheapest_provider = min(
                providers.keys(),
                key=lambda p: providers[p]['cost_per_token']
            )
            return cheapest_provider
        
        return None

class PerformanceOptimizedRoutingStrategy(RoutingStrategy):
    """性能优化路由策略"""
    
    def __init__(self, performance_tracker):
        self.performance_tracker = performance_tracker
    
    def select_provider(
        self, 
        messages: List[BaseMessage], 
        providers: Dict[str, Any], 
        requirements: Dict[str, Any]
    ) -> Optional[str]:
        """选择性能最佳的提供商"""
        
        if requirements.get('optimize_performance', False):
            best_provider = None
            best_performance = -1
            
            for provider_name in providers.keys():
                metrics = self.performance_tracker.get_metrics(provider_name)
                
                # 综合性能评分
                performance_score = (
                    metrics['success_rate'] * 0.7 +
                    (1.0 / max(metrics['avg_response_time'], 0.1)) * 0.3
                )
                
                if performance_score > best_performance:
                    best_performance = performance_score
                    best_provider = provider_name
            
            return best_provider
        
        return None

# 使用示例
async def example_intelligent_routing():
    """智能路由使用示例"""
    
    # 创建路由器
    router = IntelligentLLMRouter()
    
    # 注册提供商
    router.register_provider('gpt-4', ChatOpenAI(model="gpt-4"), {
        'capabilities': ['code', 'analysis', 'reasoning'],
        'cost_per_token': 0.03,
        'max_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    })
    
    router.register_provider('claude-3-opus', ChatAnthropic(model="claude-3-opus-20240229"), {
        'capabilities': ['creative', 'analysis', 'reasoning'],
        'cost_per_token': 0.015,
        'max_tokens': 200000,
        'supports_vision': False,
        'supports_function_calling': True
    })
    
    router.register_provider('gpt-3.5-turbo', ChatOpenAI(model="gpt-3.5-turbo"), {
        'capabilities': ['conversation', 'translation'],
        'cost_per_token': 0.0015,
        'max_tokens': 4096,
        'supports_vision': False,
        'supports_function_calling': True
    })
    
    # 添加路由策略
    router.add_routing_strategy(TaskBasedRoutingStrategy())
    router.add_routing_strategy(CostOptimizedRoutingStrategy())
    router.add_routing_strategy(PerformanceOptimizedRoutingStrategy(router.performance_tracker))
    
    # 测试不同类型的请求
    test_cases = [
        {
            'messages': [HumanMessage(content="Write a Python function to sort a list")],
            'requirements': {'task_type': 'code'}
        },
        {
            'messages': [HumanMessage(content="Tell me a creative story about space exploration")],
            'requirements': {'task_type': 'creative'}
        },
        {
            'messages': [HumanMessage(content="Hello, how are you today?")],
            'requirements': {'optimize_cost': True}
        },
        {
            'messages': [HumanMessage(content="Analyze this complex business problem...")],
            'requirements': {'optimize_performance': True}
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        try:
            result = await router.invoke_with_routing(**test_case)
            print(f"Test case {i+1}: {result.content[:100]}...")
        except Exception as e:
            print(f"Test case {i+1} failed: {e}")
```

---

## 最佳实践指南

### 1. 提供商选择策略

```python
class ProviderSelectionGuide:
    """提供商选择指南"""
    
    @staticmethod
    def recommend_provider(use_case: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """根据使用场景推荐提供商"""
        
        recommendations = {
            'code_generation': {
                'primary': 'gpt-4',
                'fallback': 'claude-3-sonnet',
                'reason': 'GPT-4在代码生成和理解方面表现优秀',
                'cost_effective_alternative': 'gpt-3.5-turbo'
            },
            
            'creative_writing': {
                'primary': 'claude-3-opus', 
                'fallback': 'gpt-4',
                'reason': 'Claude在创意写作方面有独特优势',
                'cost_effective_alternative': 'claude-3-haiku'
            },
            
            'data_analysis': {
                'primary': 'gpt-4',
                'fallback': 'claude-3-sonnet',
                'reason': '强大的分析推理能力',
                'cost_effective_alternative': 'gpt-3.5-turbo'
            },
            
            'conversation': {
                'primary': 'gpt-3.5-turbo',
                'fallback': 'claude-3-haiku', 
                'reason': '成本效益最佳，响应速度快',
                'cost_effective_alternative': 'gpt-3.5-turbo'
            },
            
            'long_context': {
                'primary': 'claude-3-sonnet',
                'fallback': 'gpt-4-32k',
                'reason': 'Claude支持更长的上下文窗口',
                'cost_effective_alternative': 'claude-3-haiku'
            },
            
            'multimodal': {
                'primary': 'gpt-4-vision',
                'fallback': 'claude-3-opus',
                'reason': 'GPT-4-Vision对图像理解能力强',
                'cost_effective_alternative': None
            }
        }
        
        base_recommendation = recommendations.get(use_case, {
            'primary': 'gpt-3.5-turbo',
            'fallback': 'claude-3-haiku',
            'reason': '通用场景的平衡选择'
        })
        
        # 根据要求调整推荐
        if requirements.get('budget_conscious', False):
            if base_recommendation.get('cost_effective_alternative'):
                base_recommendation['adjusted_primary'] = base_recommendation['cost_effective_alternative']
        
        if requirements.get('max_context_length', 0) > 8192:
            base_recommendation['context_note'] = '考虑使用Claude-3或GPT-4-32k处理长上下文'
        
        return base_recommendation

# 使用示例
def example_provider_selection():
    """提供商选择示例"""
    
    guide = ProviderSelectionGuide()
    
    # 不同场景的推荐
    scenarios = [
        {'use_case': 'code_generation', 'requirements': {}},
        {'use_case': 'creative_writing', 'requirements': {'budget_conscious': True}},
        {'use_case': 'data_analysis', 'requirements': {'max_context_length': 50000}},
        {'use_case': 'conversation', 'requirements': {'budget_conscious': True}}
    ]
    
    for scenario in scenarios:
        recommendation = guide.recommend_provider(**scenario)
        print(f"Use case: {scenario['use_case']}")
        print(f"Primary: {recommendation['primary']}")
        print(f"Reason: {recommendation['reason']}")
        if 'adjusted_primary' in recommendation:
            print(f"Budget-adjusted: {recommendation['adjusted_primary']}")
        print("---")
```

### 2. 配置管理最佳实践

```python
class LLMConfigManager:
    """LLM配置管理最佳实践"""
    
    def __init__(self):
        self.environments = ['development', 'staging', 'production']
        self.config_templates = self._load_config_templates()
    
    def _load_config_templates(self) -> Dict[str, Dict]:
        """加载配置模板"""
        return {
            'development': {
                'temperature': 0.8,
                'max_tokens': 1000,
                'timeout': 30,
                'retry_attempts': 2,
                'enable_caching': True,
                'log_level': 'DEBUG'
            },
            'staging': {
                'temperature': 0.5,
                'max_tokens': 2000,
                'timeout': 60,
                'retry_attempts': 3,
                'enable_caching': True,
                'log_level': 'INFO'
            },
            'production': {
                'temperature': 0.3,
                'max_tokens': 4000,
                'timeout': 120,
                'retry_attempts': 5,
                'enable_caching': True,
                'log_level': 'WARNING'
            }
        }
    
    def get_config(self, environment: str, provider: str, model: str) -> Dict[str, Any]:
        """获取特定环境的配置"""
        
        # 基础配置
        base_config = self.config_templates.get(environment, {})
        
        # 提供商特定配置
        provider_config = self._get_provider_specific_config(provider, environment)
        
        # 模型特定配置  
        model_config = self._get_model_specific_config(provider, model, environment)
        
        # 合并配置（优先级：模型 > 提供商 > 基础）
        merged_config = {**base_config, **provider_config, **model_config}
        
        return merged_config
    
    def _get_provider_specific_config(self, provider: str, environment: str) -> Dict[str, Any]:
        """获取提供商特定配置"""
        
        provider_configs = {
            'openai': {
                'development': {'top_p': 0.9, 'frequency_penalty': 0},
                'staging': {'top_p': 0.8, 'frequency_penalty': 0.1},
                'production': {'top_p': 0.7, 'frequency_penalty': 0.2}
            },
            'anthropic': {
                'development': {'top_k': 40},
                'staging': {'top_k': 20},
                'production': {'top_k': 10}
            }
        }
        
        return provider_configs.get(provider, {}).get(environment, {})
    
    def _get_model_specific_config(self, provider: str, model: str, environment: str) -> Dict[str, Any]:
        """获取模型特定配置"""
        
        model_configs = {
            'gpt-4': {
                'production': {'max_tokens': 8000, 'temperature': 0.1}
            },
            'gpt-3.5-turbo': {
                'production': {'max_tokens': 4000, 'temperature': 0.3}
            },
            'claude-3-opus': {
                'production': {'max_tokens': 10000, 'temperature': 0.2}
            }
        }
        
        return model_configs.get(model, {}).get(environment, {})
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """验证配置的有效性"""
        
        errors = []
        
        # 温度验证
        if 'temperature' in config:
            temp = config['temperature']
            if not isinstance(temp, (int, float)) or not 0 <= temp <= 2:
                errors.append("Temperature must be a number between 0 and 2")
        
        # max_tokens验证
        if 'max_tokens' in config:
            max_tokens = config['max_tokens']
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                errors.append("max_tokens must be a positive integer")
        
        # 超时验证
        if 'timeout' in config:
            timeout = config['timeout']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("timeout must be a positive number")
        
        return errors

# 安全配置管理
class SecureLLMConfig:
    """安全的LLM配置管理"""
    
    def __init__(self):
        self.secret_manager = SecretManager()
    
    def get_secure_config(self, provider: str, environment: str) -> Dict[str, Any]:
        """获取安全配置"""
        
        # 从环境变量或密钥管理服务获取敏感信息
        api_key = self.secret_manager.get_secret(f"{provider.upper()}_API_KEY")
        
        config = {
            'api_key': api_key,
            'environment': environment,
            'provider': provider
        }
        
        # 添加其他安全设置
        if environment == 'production':
            config.update({
                'enable_content_filter': True,
                'log_requests': False,  # 生产环境不记录请求内容
                'enable_audit_log': True
            })
        
        return config
    
    def mask_sensitive_info(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """屏蔽敏感信息用于日志"""
        
        masked_config = config.copy()
        
        sensitive_keys = ['api_key', 'secret', 'password', 'token']
        
        for key in sensitive_keys:
            if key in masked_config:
                value = masked_config[key]
                if isinstance(value, str) and len(value) > 8:
                    masked_config[key] = f"{value[:4]}****{value[-4:]}"
                else:
                    masked_config[key] = "****"
        
        return masked_config

class SecretManager:
    """密钥管理器（示例实现）"""
    
    def get_secret(self, key: str) -> Optional[str]:
        """获取密钥"""
        
        # 优先从环境变量获取
        import os
        env_value = os.getenv(key)
        if env_value:
            return env_value
        
        # 可以集成AWS Secrets Manager、Azure Key Vault等
        # 这里只是示例实现
        return None
```

### 3. 性能监控和优化

```python
class LLMPerformanceOptimizer:
    """LLM性能优化器"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.optimizer_rules = self._load_optimization_rules()
    
    def _load_optimization_rules(self) -> List['OptimizationRule']:
        """加载优化规则"""
        return [
            ResponseTimeOptimizationRule(),
            CostOptimizationRule(), 
            AccuracyOptimizationRule(),
            ReliabilityOptimizationRule()
        ]
    
    def analyze_performance(self, llm_name: str, time_window: int = 3600) -> Dict[str, Any]:
        """分析性能指标"""
        
        metrics = self.metrics_collector.get_metrics(llm_name, time_window)
        
        analysis = {
            'response_time': {
                'average': metrics['avg_response_time'],
                'p95': metrics['p95_response_time'],
                'trend': self._calculate_trend(metrics['response_times'])
            },
            'success_rate': {
                'current': metrics['success_rate'],
                'target': 0.99,
                'status': 'good' if metrics['success_rate'] > 0.95 else 'poor'
            },
            'cost_efficiency': {
                'cost_per_request': metrics['avg_cost_per_request'],
                'total_cost': metrics['total_cost'],
                'efficiency_score': self._calculate_cost_efficiency(metrics)
            },
            'error_analysis': {
                'error_types': metrics['error_distribution'],
                'most_common_error': metrics['most_common_error']
            }
        }
        
        return analysis
    
    def generate_optimization_recommendations(
        self, 
        llm_name: str, 
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成优化建议"""
        
        recommendations = []
        
        for rule in self.optimizer_rules:
            rule_recommendations = rule.evaluate(llm_name, analysis)
            recommendations.extend(rule_recommendations)
        
        # 按优先级排序
        recommendations.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return recommendations
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return 'insufficient_data'
        
        # 简单的线性趋势计算
        recent_avg = sum(values[-10:]) / min(10, len(values))
        older_avg = sum(values[:-10]) / max(1, len(values) - 10)
        
        if recent_avg > older_avg * 1.1:
            return 'increasing'
        elif recent_avg < older_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_cost_efficiency(self, metrics: Dict) -> float:
        """计算成本效率"""
        
        # 成本效率 = 成功率 / (平均成本 * 平均响应时间)
        success_rate = metrics['success_rate']
        avg_cost = metrics['avg_cost_per_request']
        avg_time = metrics['avg_response_time']
        
        if avg_cost <= 0 or avg_time <= 0:
            return 0.0
        
        efficiency = success_rate / (avg_cost * avg_time)
        return min(efficiency, 1.0)  # 归一化到0-1

# 优化规则基类和实现
class OptimizationRule(ABC):
    """优化规则抽象基类"""
    
    @abstractmethod
    def evaluate(self, llm_name: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估并生成建议"""
        pass

class ResponseTimeOptimizationRule(OptimizationRule):
    """响应时间优化规则"""
    
    def evaluate(self, llm_name: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估响应时间优化"""
        
        recommendations = []
        response_time = analysis['response_time']
        
        # 响应时间过长
        if response_time['average'] > 10.0:
            recommendations.append({
                'type': 'response_time_optimization',
                'priority': 8,
                'issue': f"平均响应时间过长: {response_time['average']:.2f}秒",
                'suggestions': [
                    '考虑使用更快的模型（如GPT-3.5-turbo替代GPT-4）',
                    '启用请求缓存',
                    '减少max_tokens设置',
                    '使用流式响应改善用户体验'
                ],
                'expected_improvement': '响应时间可减少30-50%'
            })
        
        # 响应时间趋势恶化
        if response_time['trend'] == 'increasing':
            recommendations.append({
                'type': 'response_time_trend',
                'priority': 6,
                'issue': '响应时间呈上升趋势',
                'suggestions': [
                    '检查网络连接质量',
                    '监控API提供商状态',
                    '考虑增加重试间隔',
                    '启用负载均衡'
                ],
                'expected_improvement': '稳定响应时间'
            })
        
        return recommendations

class CostOptimizationRule(OptimizationRule):
    """成本优化规则"""
    
    def evaluate(self, llm_name: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估成本优化"""
        
        recommendations = []
        cost_efficiency = analysis['cost_efficiency']
        
        # 成本效率低
        if cost_efficiency['efficiency_score'] < 0.5:
            recommendations.append({
                'type': 'cost_optimization',
                'priority': 7,
                'issue': f"成本效率较低: {cost_efficiency['efficiency_score']:.2f}",
                'suggestions': [
                    '使用成本更低的模型处理简单任务',
                    '启用智能路由根据任务复杂度选择模型',
                    '减少不必要的token使用',
                    '实施更严格的输入验证'
                ],
                'expected_improvement': '成本可降低20-40%'
            })
        
        return recommendations

class AccuracyOptimizationRule(OptimizationRule):
    """准确性优化规则"""
    
    def evaluate(self, llm_name: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估准确性优化"""
        
        recommendations = []
        success_rate = analysis['success_rate']
        
        if success_rate['current'] < success_rate['target']:
            gap = success_rate['target'] - success_rate['current']
            recommendations.append({
                'type': 'accuracy_optimization',
                'priority': 9,
                'issue': f"成功率低于目标 {gap:.1%}",
                'suggestions': [
                    '优化提示词模板',
                    '增加输入验证',
                    '实施多模型投票机制',
                    '添加结果验证步骤'
                ],
                'expected_improvement': f'成功率提升至 {success_rate["target"]:.1%}'
            })
        
        return recommendations

# 自动优化执行器
class AutoOptimizer:
    """自动优化执行器"""
    
    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
        self.optimizer = LLMPerformanceOptimizer()
        self.auto_apply_enabled = False
        
    def run_optimization_cycle(self):
        """执行一轮优化分析"""
        
        results = {}
        
        for llm_name in self.llm_manager.get_registered_llms():
            
            # 分析性能
            analysis = self.optimizer.analyze_performance(llm_name)
            
            # 生成建议
            recommendations = self.optimizer.generate_optimization_recommendations(
                llm_name, analysis
            )
            
            results[llm_name] = {
                'analysis': analysis,
                'recommendations': recommendations,
                'auto_applied': []
            }
            
            # 自动应用安全的优化建议
            if self.auto_apply_enabled:
                auto_applied = self._auto_apply_safe_optimizations(
                    llm_name, recommendations
                )
                results[llm_name]['auto_applied'] = auto_applied
        
        return results
    
    def _auto_apply_safe_optimizations(
        self, 
        llm_name: str, 
        recommendations: List[Dict[str, Any]]
    ) -> List[str]:
        """自动应用安全的优化建议"""
        
        applied = []
        
        # 只自动应用安全且影响较小的优化
        safe_optimization_types = [
            'enable_caching',
            'adjust_timeout',
            'enable_retry'
        ]
        
        for rec in recommendations:
            if (rec['type'] in safe_optimization_types and 
                rec['priority'] < 8):  # 只应用低优先级的建议
                
                try:
                    self._apply_optimization(llm_name, rec)
                    applied.append(rec['type'])
                except Exception as e:
                    logger.error(f"Failed to apply optimization {rec['type']}: {e}")
        
        return applied
    
    def _apply_optimization(self, llm_name: str, recommendation: Dict[str, Any]):
        """应用具体的优化建议"""
        
        # 这里实现具体的优化应用逻辑
        # 例如：修改LLM配置、启用缓存等
        pass

# 使用示例
def example_performance_optimization():
    """性能优化使用示例"""
    
    optimizer = LLMPerformanceOptimizer()
    
    # 分析性能
    analysis = optimizer.analyze_performance('gpt-4', time_window=3600)
    print("Performance Analysis:", json.dumps(analysis, indent=2))
    
    # 生成优化建议
    recommendations = optimizer.generate_optimization_recommendations('gpt-4', analysis)
    
    print("\nOptimization Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['issue']}")
        print(f"   Priority: {rec['priority']}")
        print(f"   Suggestions: {rec['suggestions']}")
        print(f"   Expected: {rec['expected_improvement']}")
        print()
```

---

## 总结

LangChain的LLM集成层通过精心设计的三层抽象架构，实现了对各种LLM提供商的统一封装和管理：

1. **统一抽象**：BaseLanguageModel → BaseChatModel/BaseLLM → 具体实现的清晰层次
2. **消息系统**：完整的消息类型体系和格式转换机制
3. **提供商集成**：标准化的集成模式和动态切换能力
4. **类型安全**：泛型系统确保编译时类型检查
5. **异步支持**：完整的异步执行和并发控制
6. **错误处理**：统一的错误体系和智能重试机制
7. **性能优化**：缓存、批处理、负载均衡等优化策略

通过这些设计，LangChain为开发者提供了一个强大、灵活且可靠的LLM集成平台，支持各种复杂的应用场景和企业级需求。