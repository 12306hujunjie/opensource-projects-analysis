# LangChain Agents 系统深度分析

## 目录

1. [Agent系统概览](#agent系统概览)
2. [核心架构设计](#核心架构设计)
3. [决策循环机制](#决策循环机制)
4. [Agent类型与策略](#agent类型与策略)
5. [工具调用系统](#工具调用系统)
6. [执行器与控制](#执行器与控制)
7. [实际应用案例](#实际应用案例)
8. [最佳实践指南](#最佳实践指南)

---

## Agent系统概览

### 什么是Agent

在LangChain中，Agent是一个能够使用工具、制定决策并执行复杂任务的智能实体。与传统的预定义工作流不同，Agent具备推理能力，能够根据当前状态动态决定下一步行动。

```python
# Agent的核心概念
class Agent:
    """
    Agent = LLM推理引擎 + 工具集合 + 决策循环
    
    核心能力：
    1. 理解任务和上下文
    2. 制定行动计划
    3. 选择合适的工具
    4. 执行并观察结果
    5. 迭代优化直到完成任务
    """
    
    def solve_task(self, task: str) -> str:
        """解决复杂任务的通用流程"""
        
        observations = []
        
        while not self.is_task_complete():
            # 1. 分析当前状态
            current_state = self.analyze_state(task, observations)
            
            # 2. 制定下一步行动
            action = self.plan_next_action(current_state)
            
            # 3. 执行行动
            if action.is_final_answer():
                return action.output
            
            # 4. 使用工具执行
            tool = self.get_tool(action.tool_name)
            result = tool.execute(action.tool_input)
            
            # 5. 观察结果
            observations.append((action, result))
            
        return self.synthesize_final_answer(observations)
```

### Agent系统的核心优势

1. **动态适应性**：根据任务需求动态调整执行策略
2. **工具集成**：无缝集成各种外部工具和API
3. **推理能力**：基于LLM的强大推理和理解能力
4. **错误恢复**：能够从错误中学习和恢复
5. **可扩展性**：易于添加新工具和扩展功能

---

## 核心架构设计

### Agent系统的分层架构

```python
# LangChain Agent架构的层次结构

┌─────────────────────────────────────────────────────────┐
│                   AgentExecutor                         │
│  • 执行控制和循环管理                                      │
│  • 错误处理和重试逻辑                                      │
│  • 性能监控和日志记录                                      │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│                 BaseAgent                               │
│  • 决策逻辑和推理                                        │
│  • 提示模板管理                                         │
│  • 输出解析和格式化                                       │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│               Tools Ecosystem                           │
│  • 工具定义和注册                                        │
│  • 参数验证和类型检查                                      │
│  • 执行结果处理                                         │
└─────────────────────────────────────────────────────────┘
```

### BaseAgent抽象层

```python
# langchain/agents/agent.py 核心实现
from abc import ABC, abstractmethod
from typing import List, Tuple, Union, Optional, Any, Dict

class BaseSingleActionAgent(BaseModel, ABC):
    """单动作Agent的抽象基类"""
    
    # Agent核心属性
    allowed_tools: Optional[List[str]] = None
    return_intermediate_steps: bool = False
    
    @abstractmethod
    def plan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """
        核心决策方法：分析当前状态并决定下一步行动
        
        参数:
            intermediate_steps: 历史执行步骤 [(动作, 观察结果), ...]
            callbacks: 回调处理器
            **kwargs: 其他上下文信息
            
        返回:
            AgentAction: 要执行的具体动作
            AgentFinish: 完成信号和最终答案
        """
        
    @abstractmethod
    async def aplan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """plan方法的异步版本"""
    
    @property
    @abstractmethod
    def input_keys(self) -> List[str]:
        """Agent接受的输入键"""
        return []
    
    def return_stopped_response(
        self,
        early_stopping_method: str,
        intermediate_steps: List[Tuple[AgentAction, str]],
        **kwargs: Any,
    ) -> AgentFinish:
        """处理早停情况的响应"""
        if early_stopping_method == "force":
            return AgentFinish(
                {"output": "Agent stopped due to iteration limit or time limit."},
                ""
            )
        else:
            raise ValueError(f"Unknown early stopping method: {early_stopping_method}")


class BaseMultiActionAgent(BaseModel, ABC):
    """多动作Agent的抽象基类 - 支持并行执行多个动作"""
    
    @abstractmethod
    def plan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> Union[List[AgentAction], AgentFinish]:
        """规划多个并行动作"""
```

### AgentAction和AgentFinish数据结构

```python
from pydantic import BaseModel

class AgentAction(BaseModel):
    """代表Agent要执行的一个动作"""
    
    tool: str              # 工具名称
    tool_input: Union[str, Dict]  # 工具输入参数
    log: str               # 推理日志和思考过程
    
    def __str__(self) -> str:
        return f"Action: {self.tool}\nInput: {self.tool_input}\nLog: {self.log}"


class AgentFinish(BaseModel):
    """代表Agent完成任务的信号"""
    
    return_values: Dict[str, Any]  # 最终返回值
    log: str                       # 完成时的日志
    
    def __str__(self) -> str:
        return f"Final Answer: {self.return_values}\nLog: {self.log}"


# 使用示例
def example_agent_decision():
    """Agent决策过程示例"""
    
    # 继续执行的情况
    continue_action = AgentAction(
        tool="search_engine",
        tool_input="什么是量子计算",
        log="用户询问量子计算，我需要搜索最新信息"
    )
    
    # 完成任务的情况
    finish_action = AgentFinish(
        return_values={"output": "量子计算是一种利用量子力学原理进行计算的技术..."},
        log="已获得足够信息，可以提供完整答案"
    )
    
    return continue_action  # 或 finish_action
```

---

## 决策循环机制

### AgentExecutor - 执行引擎

```python
class AgentExecutor(Chain):
    """
    Agent执行器：管理Agent的完整决策-执行循环
    
    核心职责：
    1. 维护执行状态和历史
    2. 控制执行流程和迭代次数  
    3. 处理错误和异常情况
    4. 提供可观测性和调试支持
    """
    
    agent: Union[BaseSingleActionAgent, BaseMultiActionAgent, Runnable]
    tools: Sequence[BaseTool]
    
    # 执行控制参数
    max_iterations: Optional[int] = 15
    max_execution_time: Optional[float] = None
    early_stopping_method: str = "force"
    
    # 错误处理配置
    handle_parsing_errors: Union[bool, str, Callable[[OutputParserException], str]] = False
    
    # 调试和监控
    verbose: bool = False
    return_intermediate_steps: bool = False
    
    def _call(
        self,
        inputs: Dict[str, str],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, Any]:
        """
        核心执行循环实现
        """
        # 1. 初始化执行状态
        name_to_tool_map = {tool.name: tool for tool in self.tools}
        color_mapping = get_color_mapping([tool.name for tool in self.tools], excluded_colors=["green"])
        intermediate_steps: List[Tuple[AgentAction, str]] = []
        
        # 2. 执行循环控制变量
        iterations = 0
        time_elapsed = 0.0
        start_time = time.time()
        
        # 3. 主执行循环
        while self._should_continue(iterations, time_elapsed):
            # 检查是否应该继续执行
            if iterations >= self.max_iterations:
                break
                
            if self.max_execution_time and time_elapsed >= self.max_execution_time:
                break
            
            # 执行下一步
            next_step_output = self._take_next_step(
                name_to_tool_map,
                color_mapping,
                inputs,
                intermediate_steps,
                run_manager=run_manager,
            )
            
            # 处理步骤输出
            if isinstance(next_step_output, AgentFinish):
                # Agent完成任务
                return self._return(
                    next_step_output,
                    intermediate_steps,
                    run_manager=run_manager,
                )
            
            # 更新中间步骤
            intermediate_steps.extend(next_step_output)
            
            if len(next_step_output) == 1:
                next_step_action = next_step_output[0]
                # 检查工具是否返回直接结果
                tool_return = name_to_tool_map[next_step_action[0].tool]
                if tool_return.return_direct:
                    return self._return(
                        AgentFinish(
                            {self.agent.return_values[0]: next_step_action[1]},
                            next_step_action[1],
                        ),
                        intermediate_steps,
                        run_manager=run_manager,
                    )
            
            # 更新循环变量
            iterations += 1
            time_elapsed = time.time() - start_time
        
        # 4. 处理执行限制情况
        output = self.agent.return_stopped_response(
            self.early_stopping_method, intermediate_steps, **inputs
        )
        
        return self._return(output, intermediate_steps, run_manager=run_manager)
    
    def _take_next_step(
        self,
        name_to_tool_map: Dict[str, BaseTool],
        color_mapping: Dict[str, str],
        inputs: Dict[str, str],
        intermediate_steps: List[Tuple[AgentAction, str]],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Union[AgentFinish, List[Tuple[AgentAction, str]]]:
        """
        执行Agent的下一步决策和行动
        """
        try:
            # 1. Agent进行决策规划
            intermediate_steps = self._prepare_intermediate_steps(intermediate_steps)
            
            # 获取完整输入
            full_inputs = self.agent.get_full_inputs(intermediate_steps, **inputs)
            
            # Agent规划下一步
            output = self.agent.plan(
                intermediate_steps,
                callbacks=run_manager.get_child() if run_manager else None,
                **full_inputs,
            )
            
        except OutputParserException as e:
            # 2. 处理解析错误
            if isinstance(self.handle_parsing_errors, bool):
                raise e if not self.handle_parsing_errors else e
            elif isinstance(self.handle_parsing_errors, str):
                return self._handle_parsing_error(e, run_manager)
            else:
                return self._handle_parsing_error(e, run_manager)
        
        # 3. 处理Agent决策结果
        if isinstance(output, AgentFinish):
            return output
        
        # 4. 执行Agent选择的动作
        if isinstance(output, AgentAction):
            actions = [output]
        else:
            actions = output
            
        result = []
        for agent_action in actions:
            # 执行工具调用
            if run_manager:
                run_manager.on_agent_action(agent_action, color=color_mapping[agent_action.tool])
            
            # 获取工具并执行
            tool = name_to_tool_map[agent_action.tool]
            
            observation = tool.run(
                agent_action.tool_input,
                verbose=self.verbose,
                color=color_mapping[agent_action.tool],
                callbacks=run_manager.get_child() if run_manager else None,
                **tool.get_run_manager_kwargs(),
            )
            
            result.append((agent_action, observation))
        
        return result
    
    def _should_continue(self, iterations: int, time_elapsed: float) -> bool:
        """判断是否应该继续执行循环"""
        if self.max_iterations is not None and iterations >= self.max_iterations:
            return False
        if self.max_execution_time is not None and time_elapsed >= self.max_execution_time:
            return False
        return True
```

### 执行流程的状态管理

```python
class AgentExecutionState:
    """Agent执行状态管理"""
    
    def __init__(self):
        self.intermediate_steps: List[Tuple[AgentAction, str]] = []
        self.iteration_count: int = 0
        self.start_time: float = time.time()
        self.total_tokens_used: int = 0
        self.tool_call_count: Dict[str, int] = defaultdict(int)
        self.error_count: int = 0
        
    def add_step(self, action: AgentAction, observation: str):
        """添加执行步骤"""
        self.intermediate_steps.append((action, observation))
        self.iteration_count += 1
        self.tool_call_count[action.tool] += 1
    
    def add_error(self, error: Exception):
        """记录错误"""
        self.error_count += 1
        # 可以添加更详细的错误分析
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "total_steps": len(self.intermediate_steps),
            "iterations": self.iteration_count,
            "execution_time": time.time() - self.start_time,
            "tools_used": dict(self.tool_call_count),
            "error_count": self.error_count,
            "success": self.error_count == 0
        }

# 在AgentExecutor中集成状态管理
class StatefulAgentExecutor(AgentExecutor):
    """带状态管理的Agent执行器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_state = AgentExecutionState()
    
    def _take_next_step(self, *args, **kwargs):
        """重写以添加状态跟踪"""
        try:
            result = super()._take_next_step(*args, **kwargs)
            
            # 记录成功的步骤
            if isinstance(result, list):
                for action, observation in result:
                    self.execution_state.add_step(action, observation)
            
            return result
            
        except Exception as e:
            self.execution_state.add_error(e)
            raise
    
    def get_execution_summary(self):
        """获取执行摘要"""
        return self.execution_state.get_execution_summary()
```

---

## Agent类型与策略

### ReAct Agent - 推理与行动

ReAct（Reasoning + Acting）是最经典的Agent模式，通过"思考-行动-观察"的循环来解决问题。

```python
class ReActSingleInputAgent(Agent):
    """ReAct模式的单输入Agent实现"""
    
    @classmethod
    def create_prompt(cls, tools: Sequence[BaseTool], prefix: str = None, suffix: str = None) -> PromptTemplate:
        """创建ReAct提示模板"""
        
        tool_strings = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
        tool_names = ", ".join([tool.name for tool in tools])
        
        prefix = prefix or """你是一个能够使用工具解决问题的AI助手。你有以下工具可以使用：

{tools}

使用以下格式回应：

Question: 输入的问题
Thought: 你应该总是思考要做什么
Action: 要采取的行动，应该是 [{tool_names}] 中的一个
Action Input: 行动的输入
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 原始输入问题的最终答案"""
        
        suffix = suffix or """开始!

Question: {input}
Thought: {agent_scratchpad}"""
        
        return PromptTemplate(
            template=prefix + "\n\n" + suffix,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "tools": tool_strings,
                "tool_names": tool_names,
            }
        )
    
    def _extract_tool_and_input(self, text: str) -> Tuple[str, str]:
        """从Agent输出中提取工具和输入"""
        # 解析Action和Action Input
        action_match = re.search(r"Action: (.*?)\n", text)
        action_input_match = re.search(r"Action Input: (.*?)(?:\n|$)", text, re.DOTALL)
        
        if action_match and action_input_match:
            action = action_match.group(1).strip()
            action_input = action_input_match.group(1).strip()
            return action, action_input
        else:
            raise OutputParserException(f"Could not parse LLM output: `{text}`")
    
    def plan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """ReAct推理规划"""
        
        # 构建agent_scratchpad
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += f"Thought: {action.log}\n"
            thoughts += f"Action: {action.tool}\n"
            thoughts += f"Action Input: {action.tool_input}\n"
            thoughts += f"Observation: {observation}\n"
        
        # 准备输入
        full_inputs = {**kwargs, "agent_scratchpad": thoughts}
        full_inputs = {k: v for k, v in full_inputs.items() if k in self.prompt.input_variables}
        
        # 调用LLM
        prompt_text = self.prompt.format(**full_inputs)
        response = self.llm_chain.predict(
            **full_inputs,
            callbacks=callbacks,
        )
        
        # 解析响应
        return self._parse_llm_output(response)
    
    def _parse_llm_output(self, text: str) -> Union[AgentAction, AgentFinish]:
        """解析LLM输出"""
        
        # 检查是否为最终答案
        if "Final Answer:" in text:
            final_answer_match = re.search(r"Final Answer: (.*?)(?:\n|$)", text, re.DOTALL)
            if final_answer_match:
                return AgentFinish(
                    return_values={"output": final_answer_match.group(1).strip()},
                    log=text,
                )
        
        # 解析Action
        try:
            tool, tool_input = self._extract_tool_and_input(text)
            return AgentAction(
                tool=tool,
                tool_input=tool_input,
                log=text
            )
        except OutputParserException:
            # 如果无法解析，尝试修复或返回错误
            return self._handle_parsing_error(text)

# ReAct Agent的实际使用
def create_react_agent():
    """创建ReAct Agent"""
    
    # 准备工具
    tools = [
        DuckDuckGoSearchRun(name="search", description="搜索最新信息"),
        PythonREPLTool(name="python", description="执行Python代码"),
        ShellTool(name="shell", description="执行Shell命令")
    ]
    
    # 创建Agent
    llm = ChatOpenAI(temperature=0, model="gpt-4")
    agent = ReActSingleInputAgent.from_llm_and_tools(
        llm=llm,
        tools=tools,
        verbose=True
    )
    
    # 创建执行器
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=10,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent_executor
```

### OpenAI Functions Agent - 函数调用

利用OpenAI的函数调用能力，提供更精确和结构化的工具调用。

```python
from langchain.agents import create_openai_functions_agent

class OpenAIFunctionsAgent:
    """基于OpenAI函数调用的Agent实现"""
    
    def __init__(self, llm, tools, system_message: str = None):
        self.llm = llm
        self.tools = tools
        self.system_message = system_message or "You are a helpful assistant."
        
        # 创建函数描述
        self.functions = self._tools_to_functions(tools)
    
    def _tools_to_functions(self, tools: List[BaseTool]) -> List[Dict]:
        """将工具转换为OpenAI函数格式"""
        functions = []
        
        for tool in tools:
            function_def = {
                "name": tool.name,
                "description": tool.description,
            }
            
            # 添加参数架构
            if hasattr(tool, 'args_schema') and tool.args_schema:
                # 从Pydantic模型生成JSON Schema
                schema = tool.args_schema.schema()
                function_def["parameters"] = {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", [])
                }
            else:
                # 简单参数
                function_def["parameters"] = {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "Tool input"
                        }
                    },
                    "required": ["input"]
                }
            
            functions.append(function_def)
        
        return functions
    
    def invoke(self, input_text: str) -> str:
        """执行Agent推理和工具调用"""
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": input_text}
        ]
        
        max_iterations = 10
        for iteration in range(max_iterations):
            
            # 调用LLM
            response = self.llm.invoke(
                messages,
                functions=self.functions,
                function_call="auto"
            )
            
            message = response.message
            messages.append({
                "role": "assistant", 
                "content": message.content,
                "function_call": getattr(message, 'function_call', None)
            })
            
            # 检查是否需要调用函数
            if hasattr(message, 'function_call') and message.function_call:
                function_call = message.function_call
                function_name = function_call.name
                function_args = json.loads(function_call.arguments)
                
                # 执行工具
                tool = next((t for t in self.tools if t.name == function_name), None)
                if tool:
                    try:
                        result = tool.run(function_args)
                        messages.append({
                            "role": "function",
                            "name": function_name,
                            "content": str(result)
                        })
                    except Exception as e:
                        messages.append({
                            "role": "function", 
                            "name": function_name,
                            "content": f"Error: {str(e)}"
                        })
                else:
                    messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": "Error: Tool not found"
                    })
            else:
                # 没有函数调用，返回最终答案
                return message.content or ""
        
        return "达到最大迭代次数限制"

# 使用OpenAI Functions Agent
def create_openai_functions_agent():
    """创建OpenAI函数调用Agent"""
    
    from langchain_openai import ChatOpenAI
    from langchain.agents import create_openai_functions_agent, AgentExecutor
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    
    # 准备工具
    tools = [
        DuckDuckGoSearchRun(),
        Calculator(),
        WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    ]
    
    # LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    
    # 提示模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that can use tools to answer questions."),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # 创建Agent
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    # 执行器
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        max_iterations=15,
        return_intermediate_steps=True
    )
    
    return agent_executor
```

### 结构化输出Agent

```python
from pydantic import BaseModel, Field
from typing import List

class StructuredOutputAgent:
    """生成结构化输出的Agent"""
    
    class TaskAnalysis(BaseModel):
        """任务分析结果"""
        task_type: str = Field(description="任务类型")
        complexity: int = Field(description="复杂度(1-10)", ge=1, le=10)
        required_tools: List[str] = Field(description="需要的工具列表")
        estimated_steps: int = Field(description="预估步骤数")
        confidence: float = Field(description="完成信心(0-1)", ge=0, le=1)
    
    class ActionPlan(BaseModel):
        """行动计划"""
        step_number: int = Field(description="步骤编号")
        action_type: str = Field(description="行动类型")
        tool_name: str = Field(description="使用的工具")
        tool_input: str = Field(description="工具输入")
        expected_output: str = Field(description="预期输出")
        rationale: str = Field(description="选择理由")
    
    class ExecutionResult(BaseModel):
        """执行结果"""
        success: bool = Field(description="是否成功")
        result: str = Field(description="执行结果")
        insights: List[str] = Field(description="获得的见解")
        next_actions: List[str] = Field(description="建议的后续行动")
        confidence_score: float = Field(description="结果可信度", ge=0, le=1)
    
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}
    
    def analyze_task(self, task: str) -> TaskAnalysis:
        """分析任务复杂度和需求"""
        
        from langchain_core.output_parsers import PydanticOutputParser
        
        parser = PydanticOutputParser(pydantic_object=self.TaskAnalysis)
        
        prompt = f"""
        分析以下任务，提供结构化的分析结果：
        
        任务：{task}
        
        可用工具：{[tool.name for tool in self.tools]}
        
        {parser.get_format_instructions()}
        """
        
        response = self.llm.invoke(prompt)
        return parser.parse(response)
    
    def create_action_plan(self, task: str, analysis: TaskAnalysis) -> List[ActionPlan]:
        """创建详细的行动计划"""
        
        from langchain_core.output_parsers import PydanticOutputParser
        
        class ActionPlanList(BaseModel):
            plans: List[StructuredOutputAgent.ActionPlan]
        
        parser = PydanticOutputParser(pydantic_object=ActionPlanList)
        
        prompt = f"""
        基于任务分析结果，创建详细的行动计划：
        
        任务：{task}
        分析结果：{analysis.json()}
        
        {parser.get_format_instructions()}
        """
        
        response = self.llm.invoke(prompt)
        plan_list = parser.parse(response)
        return plan_list.plans
    
    def execute_plan(self, plans: List[ActionPlan]) -> ExecutionResult:
        """执行行动计划"""
        
        results = []
        insights = []
        
        for plan in plans:
            try:
                # 执行工具
                tool = self.tool_map.get(plan.tool_name)
                if not tool:
                    results.append(f"工具 {plan.tool_name} 不可用")
                    continue
                
                result = tool.run(plan.tool_input)
                results.append(f"步骤 {plan.step_number}: {result}")
                
                # 分析结果并提取见解
                insight = self._extract_insight(plan, result)
                if insight:
                    insights.append(insight)
                    
            except Exception as e:
                results.append(f"步骤 {plan.step_number} 失败: {str(e)}")
        
        # 生成结构化结果
        return self.ExecutionResult(
            success=len([r for r in results if "失败" not in r]) > len(results) / 2,
            result="\n".join(results),
            insights=insights,
            next_actions=self._suggest_next_actions(results),
            confidence_score=self._calculate_confidence(results)
        )
    
    def _extract_insight(self, plan: ActionPlan, result: str) -> str:
        """从执行结果中提取见解"""
        # 使用LLM分析结果并提取见解
        prompt = f"""
        分析以下执行结果，提取关键见解：
        
        计划：{plan.json()}
        结果：{result}
        
        请提供一个简洁的见解（一句话）：
        """
        
        try:
            insight = self.llm.invoke(prompt)
            return insight.strip()
        except:
            return None
    
    def _suggest_next_actions(self, results: List[str]) -> List[str]:
        """基于结果建议后续行动"""
        # 简化实现
        if any("失败" in result for result in results):
            return ["重新分析任务", "调整执行策略", "寻求人工协助"]
        else:
            return ["总结成果", "完善结果", "准备汇报"]
    
    def _calculate_confidence(self, results: List[str]) -> float:
        """计算结果可信度"""
        success_count = len([r for r in results if "失败" not in r])
        return success_count / len(results) if results else 0.0
```

---

## 工具调用系统

### BaseTool接口详解

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type, Any, Union

class BaseTool(RunnableSerializable[Union[str, Dict], Any]):
    """工具的基础抽象类"""
    
    # 工具标识和描述
    name: str = Field(..., description="工具的唯一名称")
    description: str = Field(..., description="工具的功能描述")
    
    # 参数定义
    args_schema: Optional[Type[BaseModel]] = Field(None, description="参数架构")
    
    # 行为控制
    return_direct: bool = Field(False, description="是否直接返回结果给用户")
    verbose: bool = Field(False, description="是否显示详细信息")
    
    # 回调系统
    callbacks: Callbacks = Field(default=None, exclude=True)
    
    @abstractmethod
    def _run(
        self,
        *args: Any,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """工具的同步执行逻辑"""
        
    async def _arun(
        self,
        *args: Any,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """工具的异步执行逻辑"""
        # 默认实现：在线程池中执行同步版本
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, *args, **kwargs)
    
    def run(
        self,
        tool_input: Union[str, Dict],
        verbose: Optional[bool] = None,
        start_color: Optional[str] = "green",
        color: Optional[str] = "green", 
        callbacks: Callbacks = None,
        **kwargs: Any,
    ) -> Any:
        """工具的主要调用接口"""
        
        # 设置详细输出
        verbose = verbose or self.verbose
        
        # 回调管理
        callback_manager = CallbackManager.configure(
            callbacks, 
            self.callbacks, 
            verbose=verbose,
            inheritable_tags=self.tags,
            local_tags=kwargs.get("tags", []),
            inheritable_metadata=self.metadata,
            local_metadata=kwargs.get("metadata", {}),
        )
        
        # 创建运行管理器
        new_arg_supported = signature(self._run).parameters.get("run_manager")
        run_manager = callback_manager.on_tool_start(
            {"name": self.name, "description": self.description},
            tool_input if isinstance(tool_input, str) else str(tool_input),
            color=start_color,
            **kwargs,
        )
        
        try:
            # 参数处理
            parsed_input = self._parse_input(tool_input)
            
            # 执行工具逻辑
            if new_arg_supported:
                tool_output = self._run(parsed_input, run_manager=run_manager, **kwargs)
            else:
                tool_output = self._run(parsed_input, **kwargs)
            
            # 处理输出
            if tool_output is None:
                tool_output = "Tool completed successfully with no output."
            
            # 通知回调管理器
            run_manager.on_tool_end(str(tool_output), color=color, **kwargs)
            
            return tool_output
            
        except Exception as e:
            # 错误处理
            run_manager.on_tool_error(e)
            raise e
    
    def _parse_input(self, tool_input: Union[str, Dict]) -> Union[str, Dict]:
        """解析和验证工具输入"""
        
        # 如果有参数架构，进行验证
        if self.args_schema:
            if isinstance(tool_input, str):
                # 尝试解析JSON
                try:
                    parsed_input = json.loads(tool_input)
                except json.JSONDecodeError:
                    # 如果不是JSON，作为单一字符串参数处理
                    parsed_input = {"input": tool_input}
            else:
                parsed_input = tool_input
            
            # Pydantic验证
            try:
                validated_input = self.args_schema(**parsed_input)
                return validated_input.dict()
            except ValidationError as e:
                raise ValueError(f"工具输入验证失败: {str(e)}")
        
        return tool_input
```

### 具体工具实现示例

```python
# 搜索工具实现
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

class AdvancedSearchTool(BaseTool):
    """增强的搜索工具"""
    
    name = "advanced_search"
    description = "搜索互联网获取最新信息，支持多种搜索模式"
    
    class SearchArgs(BaseModel):
        query: str = Field(description="搜索查询")
        num_results: int = Field(default=5, description="返回结果数量", ge=1, le=20)
        search_type: str = Field(default="general", description="搜索类型：general, news, academic")
        language: str = Field(default="zh", description="搜索语言")
    
    args_schema: Type[BaseModel] = SearchArgs
    
    def __init__(self):
        super().__init__()
        self.search_wrapper = DuckDuckGoSearchAPIWrapper()
    
    def _run(
        self,
        query: str,
        num_results: int = 5,
        search_type: str = "general",
        language: str = "zh",
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> str:
        """执行搜索"""
        
        try:
            # 根据搜索类型调整查询
            if search_type == "news":
                modified_query = f"{query} 最新新闻"
            elif search_type == "academic":
                modified_query = f"{query} 学术研究"
            else:
                modified_query = query
            
            # 执行搜索
            results = self.search_wrapper.run(modified_query)
            
            # 格式化结果
            if run_manager:
                run_manager.on_tool_end(f"搜索完成，找到 {num_results} 个结果")
            
            return f"搜索结果：\n{results}"
            
        except Exception as e:
            error_msg = f"搜索失败: {str(e)}"
            if run_manager:
                run_manager.on_tool_error(Exception(error_msg))
            return error_msg


# 代码执行工具
import subprocess
import tempfile
import os

class SafeCodeExecutor(BaseTool):
    """安全的代码执行工具"""
    
    name = "code_executor"
    description = "在安全环境中执行代码"
    
    class CodeArgs(BaseModel):
        code: str = Field(description="要执行的代码")
        language: str = Field(default="python", description="编程语言")
        timeout: int = Field(default=30, description="执行超时时间(秒)")
    
    args_schema: Type[BaseModel] = CodeArgs
    
    SUPPORTED_LANGUAGES = {
        "python": {
            "extension": ".py",
            "command": ["python"],
            "forbidden_imports": ["os", "subprocess", "sys", "__import__"]
        },
        "javascript": {
            "extension": ".js", 
            "command": ["node"],
            "forbidden_patterns": ["require('fs')", "require('child_process')"]
        }
    }
    
    def _run(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """安全执行代码"""
        
        # 验证语言支持
        if language not in self.SUPPORTED_LANGUAGES:
            return f"不支持的编程语言: {language}"
        
        lang_config = self.SUPPORTED_LANGUAGES[language]
        
        # 安全检查
        if not self._is_code_safe(code, lang_config):
            return "代码包含不安全的操作，执行被阻止"
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=lang_config["extension"],
            delete=False
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            # 执行代码
            result = subprocess.run(
                lang_config["command"] + [temp_file_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir()  # 在临时目录中执行
            )
            
            # 处理结果
            if result.returncode == 0:
                output = result.stdout or "代码执行成功，无输出"
            else:
                output = f"执行错误: {result.stderr}"
            
            if run_manager:
                run_manager.on_tool_end(f"代码执行完成，返回码: {result.returncode}")
            
            return output
            
        except subprocess.TimeoutExpired:
            return f"代码执行超时（>{timeout}秒）"
        except Exception as e:
            return f"执行失败: {str(e)}"
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    def _is_code_safe(self, code: str, lang_config: Dict) -> bool:
        """检查代码安全性"""
        
        code_lower = code.lower()
        
        # 检查禁止的导入（Python）
        if "forbidden_imports" in lang_config:
            for forbidden in lang_config["forbidden_imports"]:
                if f"import {forbidden}" in code_lower or f"from {forbidden}" in code_lower:
                    return False
        
        # 检查禁止的模式（JavaScript等）
        if "forbidden_patterns" in lang_config:
            for pattern in lang_config["forbidden_patterns"]:
                if pattern.lower() in code_lower:
                    return False
        
        # 通用危险操作检查
        dangerous_patterns = [
            "open(", "file(", "exec(", "eval(",  # Python
            "fs.", "child_process",  # Node.js
            "system(", "shell_exec(",  # PHP
            "__import__", "getattr", "setattr"  # Python反射
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                return False
        
        return True
```

### 工具包（Toolkit）组织模式

```python
from langchain_core.tools import BaseToolkit
from typing import List

class DataAnalysisToolkit(BaseToolkit):
    """数据分析工具包"""
    
    def __init__(self, data_sources: List[str] = None):
        self.data_sources = data_sources or []
    
    def get_tools(self) -> List[BaseTool]:
        """获取数据分析相关的所有工具"""
        
        tools = [
            # 数据加载工具
            CSVLoaderTool(),
            JSONLoaderTool(),
            DatabaseConnectorTool(),
            
            # 数据处理工具
            DataCleanerTool(),
            StatisticsCalculatorTool(),
            DataVisualizationTool(),
            
            # 机器学习工具
            ModelTrainerTool(),
            PredictionTool(),
            
            # 导出工具
            ReportGeneratorTool(),
            ChartExporterTool()
        ]
        
        return tools


class WebScrapingToolkit(BaseToolkit):
    """网页抓取工具包"""
    
    def get_tools(self) -> List[BaseTool]:
        return [
            URLFetcherTool(),
            HTMLParserTool(), 
            CSSelectorTool(),
            ImageDownloaderTool(),
            SitemapParserTool(),
            RobotsTxtCheckerTool()
        ]


# 工具包的动态组合
class DynamicToolkitManager:
    """动态工具包管理器"""
    
    def __init__(self):
        self.registered_toolkits = {}
        self.active_tools = {}
    
    def register_toolkit(self, name: str, toolkit: BaseToolkit):
        """注册工具包"""
        self.registered_toolkits[name] = toolkit
    
    def activate_toolkit(self, name: str):
        """激活工具包"""
        if name in self.registered_toolkits:
            toolkit = self.registered_toolkits[name]
            tools = toolkit.get_tools()
            self.active_tools[name] = {tool.name: tool for tool in tools}
    
    def get_all_active_tools(self) -> List[BaseTool]:
        """获取所有激活的工具"""
        all_tools = []
        for toolkit_tools in self.active_tools.values():
            all_tools.extend(toolkit_tools.values())
        return all_tools
    
    def get_tool_by_name(self, tool_name: str) -> Optional[BaseTool]:
        """根据名称获取工具"""
        for toolkit_tools in self.active_tools.values():
            if tool_name in toolkit_tools:
                return toolkit_tools[tool_name]
        return None

# 使用示例
def setup_dynamic_agent():
    """设置动态工具Agent"""
    
    # 初始化工具包管理器
    toolkit_manager = DynamicToolkitManager()
    
    # 注册各种工具包
    toolkit_manager.register_toolkit("data_analysis", DataAnalysisToolkit())
    toolkit_manager.register_toolkit("web_scraping", WebScrapingToolkit())
    toolkit_manager.register_toolkit("file_operations", FileOperationsToolkit())
    
    # 根据任务需求激活工具包
    def activate_toolkits_for_task(task: str):
        if "数据" in task or "分析" in task:
            toolkit_manager.activate_toolkit("data_analysis")
        if "网页" in task or "爬取" in task:
            toolkit_manager.activate_toolkit("web_scraping")
        if "文件" in task:
            toolkit_manager.activate_toolkit("file_operations")
    
    return toolkit_manager, activate_toolkits_for_task
```

---

## 执行器与控制

### 高级执行控制

```python
class AdvancedAgentExecutor(AgentExecutor):
    """高级Agent执行器，支持更多控制功能"""
    
    def __init__(self, *args, **kwargs):
        # 扩展配置参数
        self.enable_parallel_tools = kwargs.pop("enable_parallel_tools", False)
        self.tool_timeout = kwargs.pop("tool_timeout", 60)
        self.memory_limit_mb = kwargs.pop("memory_limit_mb", 512)
        self.cost_tracking = kwargs.pop("cost_tracking", True)
        
        super().__init__(*args, **kwargs)
        
        # 执行统计
        self.execution_stats = {
            "total_tokens": 0,
            "api_calls": 0,
            "tool_calls": 0,
            "errors": 0,
            "execution_time": 0
        }
    
    def _take_next_step(
        self,
        name_to_tool_map: Dict[str, BaseTool],
        color_mapping: Dict[str, str], 
        inputs: Dict[str, str],
        intermediate_steps: List[Tuple[AgentAction, str]],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Union[AgentFinish, List[Tuple[AgentAction, str]]]:
        """增强的步骤执行"""
        
        step_start_time = time.time()
        
        try:
            # 内存检查
            self._check_memory_usage()
            
            # 获取Agent决策
            output = self._get_agent_decision(inputs, intermediate_steps, run_manager)
            
            if isinstance(output, AgentFinish):
                return output
            
            # 并行工具执行支持
            if isinstance(output, list) and self.enable_parallel_tools:
                return self._execute_parallel_tools(output, name_to_tool_map, color_mapping, run_manager)
            else:
                # 单个工具执行
                if isinstance(output, AgentAction):
                    actions = [output]
                else:
                    actions = output
                
                results = []
                for action in actions:
                    result = self._execute_single_tool(action, name_to_tool_map, color_mapping, run_manager)
                    results.append(result)
                
                return results
                
        except Exception as e:
            self.execution_stats["errors"] += 1
            raise e
        finally:
            self.execution_stats["execution_time"] += time.time() - step_start_time
    
    def _execute_parallel_tools(
        self,
        actions: List[AgentAction],
        name_to_tool_map: Dict[str, BaseTool],
        color_mapping: Dict[str, str],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> List[Tuple[AgentAction, str]]:
        """并行执行多个工具"""
        
        import concurrent.futures
        
        def execute_tool(action: AgentAction) -> Tuple[AgentAction, str]:
            return self._execute_single_tool(action, name_to_tool_map, color_mapping, run_manager)
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(actions), 5)) as executor:
            # 提交所有任务
            future_to_action = {
                executor.submit(execute_tool, action): action
                for action in actions
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(
                future_to_action,
                timeout=self.tool_timeout
            ):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    action = future_to_action[future]
                    results.append((action, f"工具执行失败: {str(e)}"))
        
        return results
    
    def _execute_single_tool(
        self,
        action: AgentAction,
        name_to_tool_map: Dict[str, BaseTool],
        color_mapping: Dict[str, str],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Tuple[AgentAction, str]:
        """执行单个工具"""
        
        if run_manager:
            run_manager.on_agent_action(action, color=color_mapping.get(action.tool, "blue"))
        
        # 获取工具
        tool = name_to_tool_map.get(action.tool)
        if not tool:
            return (action, f"工具 '{action.tool}' 不存在")
        
        # 工具超时控制
        try:
            with timeout_context(self.tool_timeout):
                observation = tool.run(
                    action.tool_input,
                    verbose=self.verbose,
                    color=color_mapping.get(action.tool, "blue"),
                    callbacks=run_manager.get_child() if run_manager else None,
                )
            
            self.execution_stats["tool_calls"] += 1
            return (action, str(observation))
            
        except TimeoutError:
            return (action, f"工具执行超时（>{self.tool_timeout}秒）")
        except Exception as e:
            return (action, f"工具执行错误: {str(e)}")
    
    def _check_memory_usage(self):
        """检查内存使用情况"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.memory_limit_mb:
                raise MemoryError(f"内存使用超限: {memory_mb:.1f}MB > {self.memory_limit_mb}MB")
                
        except ImportError:
            # psutil不可用，跳过检查
            pass
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return self.execution_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        for key in self.execution_stats:
            self.execution_stats[key] = 0


# 超时上下文管理器
import signal
from contextlib import contextmanager

@contextmanager
def timeout_context(seconds: int):
    """超时控制上下文管理器"""
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"操作超时：{seconds}秒")
    
    # 设置信号处理器
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # 恢复原始处理器
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
```

---

## 实际应用案例

### 智能客服Agent

```python
class IntelligentCustomerServiceAgent:
    """智能客服Agent实现"""
    
    def __init__(self):
        self.setup_tools()
        self.setup_knowledge_base()
        self.setup_agent()
    
    def setup_tools(self):
        """设置客服工具"""
        
        # 知识库搜索
        class KnowledgeSearchTool(BaseTool):
            name = "knowledge_search"
            description = "搜索公司知识库"
            
            def _run(self, query: str) -> str:
                # 实际实现会连接知识库
                return f"从知识库搜索 '{query}' 的结果..."
        
        # 订单查询
        class OrderLookupTool(BaseTool):
            name = "order_lookup"
            description = "查询订单信息"
            
            class OrderArgs(BaseModel):
                order_id: str = Field(description="订单号")
            
            args_schema = OrderArgs
            
            def _run(self, order_id: str) -> str:
                # 实际实现会查询订单系统
                return f"订单 {order_id} 的详细信息..."
        
        # 工单创建
        class TicketCreationTool(BaseTool):
            name = "create_ticket"
            description = "创建客服工单"
            
            class TicketArgs(BaseModel):
                title: str = Field(description="问题标题")
                description: str = Field(description="问题描述")
                priority: str = Field(default="medium", description="优先级")
                category: str = Field(description="问题分类")
            
            args_schema = TicketArgs
            
            def _run(self, **kwargs) -> str:
                return f"已创建工单: {kwargs['title']}"
        
        self.tools = [
            KnowledgeSearchTool(),
            OrderLookupTool(),
            TicketCreationTool()
        ]
    
    def setup_knowledge_base(self):
        """设置知识库"""
        # 这里会设置向量数据库、文档检索等
        pass
    
    def setup_agent(self):
        """设置Agent"""
        
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_openai_tools_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        
        # 专业客服提示
        system_prompt = """你是一个专业的智能客服助手，具备以下能力：

1. 友好耐心地回答客户问题
2. 快速搜索和提供准确信息
3. 处理订单查询和售后问题
4. 识别复杂问题并创建工单
5. 始终保持礼貌和专业态度

当客户提出问题时，你应该：
- 首先尝试从知识库搜索相关信息
- 如果涉及具体订单，使用订单查询工具
- 对于复杂问题，创建工单转交专家处理
- 始终以解决客户问题为目标

请用礼貌、专业的语气回复。"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
        
        # 创建Agent
        agent = create_openai_tools_agent(llm, self.tools, prompt)
        
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            max_iterations=10,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    def handle_customer_inquiry(self, customer_input: str, customer_id: str = None) -> dict:
        """处理客户咨询"""
        
        try:
            result = self.agent_executor.invoke({
                "input": customer_input,
                "customer_id": customer_id or "anonymous"
            })
            
            return {
                "success": True,
                "response": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
                "needs_human": self._needs_human_intervention(result)
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": "抱歉，系统出现问题，请稍后重试或联系人工客服。",
                "error": str(e),
                "needs_human": True
            }
    
    def _needs_human_intervention(self, result: dict) -> bool:
        """判断是否需要人工介入"""
        
        # 检查是否创建了工单
        steps = result.get("intermediate_steps", [])
        for action, observation in steps:
            if action.tool == "create_ticket":
                return True
        
        # 检查响应中的关键词
        response = result.get("output", "")
        human_keywords = ["转人工", "专家处理", "无法解决", "需要进一步"]
        
        return any(keyword in response for keyword in human_keywords)

# 使用示例
def demo_customer_service():
    """客服系统演示"""
    
    cs_agent = IntelligentCustomerServiceAgent()
    
    # 客户咨询示例
    inquiries = [
        "我的订单什么时候发货？订单号是 ORD-12345",
        "如何申请退款？",
        "产品使用过程中出现故障，需要技术支持",
        "我想了解一下会员权益"
    ]
    
    for inquiry in inquiries:
        print(f"\n客户咨询: {inquiry}")
        result = cs_agent.handle_customer_inquiry(inquiry)
        print(f"客服回复: {result['response']}")
        if result['needs_human']:
            print("建议转人工处理")
```

### 代码审查Agent

```python
class CodeReviewAgent:
    """代码审查Agent"""
    
    def __init__(self):
        self.setup_tools()
        self.setup_agent()
    
    def setup_tools(self):
        """设置代码审查工具"""
        
        # 静态代码分析工具
        class StaticAnalysisTool(BaseTool):
            name = "static_analysis"
            description = "执行静态代码分析"
            
            def _run(self, code: str) -> str:
                issues = []
                
                # 简单的静态分析规则
                lines = code.split('\n')
                for i, line in enumerate(lines):
                    if len(line) > 120:
                        issues.append(f"行 {i+1}: 行过长 ({len(line)} 字符)")
                    
                    if 'eval(' in line or 'exec(' in line:
                        issues.append(f"行 {i+1}: 使用了危险函数")
                    
                    if line.strip().startswith('print(') and 'debug' not in line.lower():
                        issues.append(f"行 {i+1}: 可能的调试代码")
                
                return '\n'.join(issues) if issues else "未发现明显问题"
        
        # 复杂度分析工具
        class ComplexityAnalysisTool(BaseTool):
            name = "complexity_analysis"
            description = "分析代码复杂度"
            
            def _run(self, code: str) -> str:
                # 简化的复杂度分析
                complexity_score = 1
                for keyword in ['if', 'for', 'while', 'try', 'except', 'elif']:
                    complexity_score += code.lower().count(keyword)
                
                if complexity_score > 10:
                    level = "高"
                elif complexity_score > 5:
                    level = "中"
                else:
                    level = "低"
                
                return f"代码复杂度: {level} (得分: {complexity_score})"
        
        # 安全检查工具
        class SecurityCheckTool(BaseTool):
            name = "security_check"
            description = "检查代码安全问题"
            
            def _run(self, code: str) -> str:
                security_issues = []
                
                # 安全检查规则
                dangerous_patterns = {
                    'sql injection': ['execute(', 'format(', '%s'],
                    'path traversal': ['../', '..\\'],
                    'command injection': ['system(', 'subprocess.'],
                    'unsafe eval': ['eval(', 'exec(']
                }
                
                for issue_type, patterns in dangerous_patterns.items():
                    for pattern in patterns:
                        if pattern in code:
                            security_issues.append(f"潜在{issue_type}风险: 使用了 {pattern}")
                
                return '\n'.join(security_issues) if security_issues else "未发现安全问题"
        
        # 最佳实践检查
        class BestPracticesTool(BaseTool):
            name = "best_practices"
            description = "检查最佳实践"
            
            def _run(self, code: str) -> str:
                suggestions = []
                
                # Python最佳实践检查
                if 'def ' in code:
                    functions = [line.strip() for line in code.split('\n') if line.strip().startswith('def ')]
                    for func in functions:
                        if '"""' not in code[code.find(func):code.find(func)+200]:
                            suggestions.append(f"函数 {func.split('(')[0][4:]} 缺少文档字符串")
                
                if 'import' in code:
                    import_lines = [line.strip() for line in code.split('\n') if 'import' in line]
                    for imp in import_lines:
                        if imp.startswith('from') and '*' in imp:
                            suggestions.append(f"避免使用 'from ... import *': {imp}")
                
                return '\n'.join(suggestions) if suggestions else "代码遵循最佳实践"
        
        self.tools = [
            StaticAnalysisTool(),
            ComplexityAnalysisTool(), 
            SecurityCheckTool(),
            BestPracticesTool()
        ]
    
    def setup_agent(self):
        """设置代码审查Agent"""
        
        system_prompt = """你是一个资深的代码审查专家，负责对提交的代码进行全面审查。

审查重点：
1. 代码质量和可读性
2. 性能和效率
3. 安全性问题
4. 最佳实践遵循
5. 潜在的bug和问题

审查流程：
1. 使用静态分析工具检查基本问题
2. 使用复杂度分析工具评估代码复杂度
3. 使用安全检查工具识别安全风险
4. 使用最佳实践工具检查编码规范
5. 综合所有工具结果提供审查报告

请提供详细、建设性的审查意见。"""
        
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_openai_tools_agent
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "请审查以下代码:\n\n{code}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        llm = ChatOpenAI(model="gpt-4", temperature=0.1)
        
        agent = create_openai_tools_agent(llm, self.tools, prompt)
        
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            max_iterations=8,
            verbose=True,
            return_intermediate_steps=True
        )
    
    def review_code(self, code: str, file_path: str = None) -> dict:
        """审查代码"""
        
        try:
            result = self.agent_executor.invoke({
                "code": code,
                "file_path": file_path or "unknown"
            })
            
            # 分析审查结果
            issues = self._extract_issues(result)
            
            return {
                "success": True,
                "review_summary": result["output"],
                "issues_found": len(issues),
                "critical_issues": [issue for issue in issues if issue["severity"] == "critical"],
                "recommendations": self._generate_recommendations(result),
                "intermediate_steps": result.get("intermediate_steps", [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "review_summary": "代码审查过程中发生错误"
            }
    
    def _extract_issues(self, result: dict) -> list:
        """从审查结果中提取问题"""
        issues = []
        
        steps = result.get("intermediate_steps", [])
        for action, observation in steps:
            if "问题" in observation or "风险" in observation:
                # 简化的问题提取逻辑
                issue_lines = observation.split('\n')
                for line in issue_lines:
                    if line.strip() and ("问题" in line or "风险" in line or "建议" in line):
                        severity = "critical" if "危险" in line or "风险" in line else "warning"
                        issues.append({
                            "description": line.strip(),
                            "severity": severity,
                            "tool": action.tool
                        })
        
        return issues
    
    def _generate_recommendations(self, result: dict) -> list:
        """生成改进建议"""
        recommendations = [
            "添加更多单元测试",
            "改善代码注释和文档",
            "考虑重构复杂的函数",
            "使用类型提示提高代码可读性"
        ]
        
        return recommendations

# 使用示例
def demo_code_review():
    """代码审查演示"""
    
    reviewer = CodeReviewAgent()
    
    # 示例代码
    sample_code = '''
def process_user_data(user_input):
    # 这是一个有问题的函数示例
    result = eval(user_input)  # 安全风险
    if result > 100 and result < 200 and isinstance(result, int) and result % 2 == 0:  # 复杂条件
        print("Debug: processing " + str(result))  # 调试代码
        query = "SELECT * FROM users WHERE id = %s" % result  # SQL注入风险
        return query
    return None
    '''
    
    print("开始代码审查...")
    review_result = reviewer.review_code(sample_code, "sample.py")
    
    if review_result["success"]:
        print(f"\n审查结果:")
        print(f"发现问题: {review_result['issues_found']} 个")
        print(f"严重问题: {len(review_result['critical_issues'])} 个")
        print(f"\n审查报告:\n{review_result['review_summary']}")
    else:
        print(f"审查失败: {review_result['error']}")
```

---

## 最佳实践指南

### 1. Agent设计原则

```python
# ✅ 好的Agent设计
class WellDesignedAgent:
    """设计良好的Agent示例"""
    
    def __init__(self, llm, tools, max_iterations=10):
        # 清晰的角色定义
        self.role = "专业的数据分析助手"
        self.capabilities = ["数据处理", "统计分析", "可视化", "报告生成"]
        self.limitations = ["不能访问敏感数据", "不能修改原始数据"]
        
        # 合理的工具选择
        self.tools = self._validate_tools(tools)
        self.max_iterations = max_iterations
        
        # 建立清晰的决策流程
        self.decision_framework = {
            "数据加载": ["csv_loader", "db_connector"],
            "数据清洗": ["data_cleaner", "outlier_detector"],
            "分析计算": ["statistics_calculator", "correlation_analyzer"],
            "结果展示": ["chart_generator", "report_writer"]
        }
    
    def _validate_tools(self, tools):
        """验证工具的合适性"""
        validated_tools = []
        for tool in tools:
            if self._is_tool_suitable(tool):
                validated_tools.append(tool)
            else:
                logger.warning(f"工具 {tool.name} 不适合当前Agent角色")
        return validated_tools
    
    def _is_tool_suitable(self, tool):
        """检查工具是否适合Agent角色"""
        # 实现工具适配性检查逻辑
        return True

# ❌ 不好的Agent设计
class PoorlyDesignedAgent:
    """设计不佳的Agent示例"""
    
    def __init__(self, llm, tools):
        # 角色不清晰
        self.tools = tools  # 没有工具验证
        # 没有明确的能力边界
        # 缺乏决策框架
```

### 2. 工具选择和组织

```python
# 工具选择的最佳实践
class ToolSelectionBestPractices:
    
    @staticmethod
    def select_tools_for_domain(domain: str) -> List[BaseTool]:
        """根据领域选择合适的工具"""
        
        tool_registry = {
            "data_analysis": [
                CSVReaderTool(),
                StatisticsCalculatorTool(),
                ChartGeneratorTool(),
                DataCleanerTool()
            ],
            "web_research": [
                SearchTool(),
                WebScrapingTool(),
                URLValidatorTool(),
                ContentSummarizerTool()
            ],
            "code_development": [
                CodeExecutorTool(),
                SyntaxCheckerTool(),
                DocumentationGeneratorTool(),
                TestRunnerTool()
            ]
        }
        
        return tool_registry.get(domain, [])
    
    @staticmethod
    def validate_tool_compatibility(tools: List[BaseTool]) -> bool:
        """验证工具间的兼容性"""
        
        # 检查工具名称冲突
        tool_names = [tool.name for tool in tools]
        if len(tool_names) != len(set(tool_names)):
            return False
        
        # 检查工具依赖
        for tool in tools:
            if hasattr(tool, 'dependencies'):
                for dep in tool.dependencies:
                    if dep not in tool_names:
                        return False
        
        return True
    
    @staticmethod
    def optimize_tool_order(tools: List[BaseTool]) -> List[BaseTool]:
        """优化工具执行顺序"""
        
        # 按工具类型和依赖关系排序
        data_tools = [t for t in tools if 'data' in t.name.lower()]
        analysis_tools = [t for t in tools if 'analysis' in t.name.lower()]
        output_tools = [t for t in tools if 'output' in t.name.lower() or 'report' in t.name.lower()]
        
        return data_tools + analysis_tools + output_tools
```

### 3. 错误处理和恢复

```python
class RobustAgentExecutor(AgentExecutor):
    """具有强大错误处理能力的Agent执行器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_recovery_strategies = {
            'parsing_error': self._handle_parsing_error,
            'tool_error': self._handle_tool_error,
            'timeout_error': self._handle_timeout_error,
            'rate_limit_error': self._handle_rate_limit_error
        }
        self.max_recovery_attempts = 3
    
    def _handle_parsing_error(self, error: Exception, attempt: int) -> str:
        """处理解析错误"""
        if attempt < self.max_recovery_attempts:
            return "输出格式不正确，请重新格式化响应。使用正确的Action和Action Input格式。"
        return "多次尝试后仍无法解析输出，请简化回答。"
    
    def _handle_tool_error(self, error: Exception, attempt: int) -> str:
        """处理工具错误"""
        if "not found" in str(error).lower():
            return "工具不存在，请检查可用工具列表并使用正确的工具名称。"
        elif "timeout" in str(error).lower():
            return "工具执行超时，请尝试使用更简单的输入或其他工具。"
        else:
            return f"工具执行失败: {str(error)}，请尝试其他方法。"
    
    def _handle_timeout_error(self, error: Exception, attempt: int) -> str:
        """处理超时错误"""
        return "操作超时，请尝试将复杂任务分解为更小的步骤。"
    
    def _handle_rate_limit_error(self, error: Exception, attempt: int) -> str:
        """处理速率限制错误"""
        return "API调用频率过高，请稍等片刻后继续。"
    
    def recover_from_error(self, error: Exception, attempt: int) -> str:
        """通用错误恢复机制"""
        
        error_type = self._classify_error(error)
        
        if error_type in self.error_recovery_strategies:
            return self.error_recovery_strategies[error_type](error, attempt)
        
        # 默认恢复策略
        if attempt < self.max_recovery_attempts:
            return f"遇到错误: {str(error)}，正在重试..."
        else:
            return f"多次尝试后仍无法解决问题: {str(error)}，请寻求人工协助。"
    
    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_str = str(error).lower()
        
        if 'parse' in error_str or 'format' in error_str:
            return 'parsing_error'
        elif 'timeout' in error_str:
            return 'timeout_error'
        elif 'rate limit' in error_str:
            return 'rate_limit_error'
        elif 'tool' in error_str:
            return 'tool_error'
        else:
            return 'unknown_error'
```

### 4. 性能监控和优化

```python
class PerformanceMonitoringAgent(AgentExecutor):
    """带性能监控的Agent"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.performance_metrics = {
            'total_execution_time': 0,
            'average_step_time': 0,
            'tool_usage_count': defaultdict(int),
            'success_rate': 0,
            'token_usage': 0,
            'error_count': 0
        }
        self.execution_history = []
    
    def _call(self, inputs: Dict[str, str], run_manager=None) -> Dict[str, Any]:
        """重写调用方法以添加性能监控"""
        
        start_time = time.time()
        
        try:
            result = super()._call(inputs, run_manager)
            
            # 记录成功执行
            execution_time = time.time() - start_time
            self._record_execution(inputs, result, execution_time, success=True)
            
            return result
            
        except Exception as e:
            # 记录失败执行
            execution_time = time.time() - start_time
            self._record_execution(inputs, str(e), execution_time, success=False)
            raise
    
    def _record_execution(self, inputs: dict, result: any, execution_time: float, success: bool):
        """记录执行信息"""
        
        execution_record = {
            'timestamp': time.time(),
            'inputs': inputs,
            'result': result,
            'execution_time': execution_time,
            'success': success
        }
        
        self.execution_history.append(execution_record)
        
        # 更新性能指标
        self.performance_metrics['total_execution_time'] += execution_time
        
        if success:
            self.performance_metrics['success_rate'] = len([e for e in self.execution_history if e['success']]) / len(self.execution_history)
        else:
            self.performance_metrics['error_count'] += 1
        
        self.performance_metrics['average_step_time'] = (
            self.performance_metrics['total_execution_time'] / len(self.execution_history)
        )
    
    def get_performance_report(self) -> dict:
        """获取性能报告"""
        
        if not self.execution_history:
            return {"message": "没有执行历史"}
        
        recent_executions = self.execution_history[-10:]  # 最近10次执行
        recent_avg_time = sum(e['execution_time'] for e in recent_executions) / len(recent_executions)
        
        return {
            "总执行次数": len(self.execution_history),
            "成功率": f"{self.performance_metrics['success_rate']:.2%}",
            "平均执行时间": f"{self.performance_metrics['average_step_time']:.2f}秒",
            "最近10次平均时间": f"{recent_avg_time:.2f}秒",
            "错误次数": self.performance_metrics['error_count'],
            "最频繁使用的工具": dict(self.performance_metrics['tool_usage_count']),
            "性能趋势": self._analyze_performance_trend()
        }
    
    def _analyze_performance_trend(self) -> str:
        """分析性能趋势"""
        
        if len(self.execution_history) < 5:
            return "数据不足，无法分析趋势"
        
        # 计算最近一半和前一半的平均执行时间
        mid = len(self.execution_history) // 2
        early_avg = sum(e['execution_time'] for e in self.execution_history[:mid]) / mid
        recent_avg = sum(e['execution_time'] for e in self.execution_history[mid:]) / (len(self.execution_history) - mid)
        
        if recent_avg < early_avg * 0.9:
            return "性能正在改善"
        elif recent_avg > early_avg * 1.1:
            return "性能有所下降"
        else:
            return "性能保持稳定"
    
    def optimize_performance(self) -> dict:
        """性能优化建议"""
        
        suggestions = []
        
        # 基于性能数据生成建议
        if self.performance_metrics['average_step_time'] > 30:
            suggestions.append("考虑减少max_iterations或优化工具性能")
        
        if self.performance_metrics['error_count'] > len(self.execution_history) * 0.2:
            suggestions.append("错误率较高，建议改善错误处理机制")
        
        tool_usage = self.performance_metrics['tool_usage_count']
        if tool_usage:
            unused_tools = [tool.name for tool in self.tools if tool.name not in tool_usage]
            if unused_tools:
                suggestions.append(f"考虑移除未使用的工具: {unused_tools}")
        
        return {
            "优化建议": suggestions,
            "推荐配置": {
                "max_iterations": min(15, max(5, int(self.max_iterations * 0.8))),
                "enable_caching": True,
                "parallel_tools": len(self.tools) > 3
            }
        }
```

---

## 总结

LangChain的Agent系统通过精心设计的架构实现了智能化的任务执行和决策：

1. **清晰的抽象层次**：从BaseAgent到AgentExecutor的分层设计，职责明确
2. **灵活的决策机制**：支持多种Agent策略，适应不同场景需求
3. **强大的工具生态**：统一的工具接口，丰富的工具库支持
4. **可靠的执行控制**：完善的错误处理、超时控制和状态管理
5. **企业级特性**：监控、日志、性能优化等生产环境必需功能

通过深入理解这些设计原理和实现细节，开发者可以构建出高效、可靠的智能Agent应用，充分发挥LLM的推理和决策能力。