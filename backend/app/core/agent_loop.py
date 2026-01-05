# -*- coding: utf-8 -*-
"""
自主执行循环 - Agent Loop

模仿 Cursor 的 Agent 模式：
1. ReAct 循环: Reason → Act → Observe → Repeat
2. 自动任务分解和执行
3. 动态计划调整
4. 错误恢复和重试
5. 进度追踪和状态管理
6. 人工干预点

这是 ChatBot 达到 Cursor 级别的关键能力！
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger
import asyncio
import json
import traceback

from .intent_recognizer import Intent, TaskType, RequiredCapability
from .planner import AgentPlanner


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


class LoopState(Enum):
    """循环状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class Action:
    """
    动作定义
    
    表示 Agent 要执行的一个动作
    """
    type: str                        # tool_call, respond, think, plan, ask_user
    name: str = ""                   # 工具名或动作名
    arguments: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""              # 为什么要执行这个动作
    expected_outcome: str = ""       # 期望结果
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "arguments": self.arguments,
            "reasoning": self.reasoning,
            "expected_outcome": self.expected_outcome,
        }


@dataclass
class StepResult:
    """
    步骤执行结果
    """
    step_number: int
    action: Action
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "action": self.action.to_dict(),
            "status": self.status.value,
            "output": str(self.output)[:500] if self.output else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ExecutionPlan:
    """
    执行计划
    """
    task: str
    intent: Optional[Intent] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    results: List[StepResult] = field(default_factory=list)
    state: LoopState = LoopState.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "intent": self.intent.to_dict() if self.intent else None,
            "steps": self.steps,
            "current_step": self.current_step,
            "results": [r.to_dict() for r in self.results],
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ProgressUpdate:
    """
    进度更新
    
    用于流式输出执行进度
    """
    type: str                  # thinking, action, result, progress, complete, error
    step: int = 0
    total_steps: int = 0
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "step": self.step,
            "total_steps": self.total_steps,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class AgentLoop:
    """
    自主执行循环
    
    Cursor 风格的 Agent 执行引擎：
    - 自动分解任务
    - 循环执行步骤
    - 动态调整计划
    - 错误恢复
    - 进度追踪
    
    使用示例:
    ```python
    loop = AgentLoop(llm_client, tools)
    
    async for update in loop.execute("分析这个项目并给出优化建议"):
        if update.type == "thinking":
            print(f"💭 {update.message}")
        elif update.type == "action":
            print(f"🔧 {update.message}")
        elif update.type == "result":
            print(f"✅ {update.message}")
        elif update.type == "complete":
            print(f"🎉 {update.message}")
    ```
    """
    
    # 配置
    MAX_STEPS = 15
    MAX_RETRIES = 3
    STEP_TIMEOUT = 60  # 秒
    
    def __init__(
        self,
        llm_client,
        tools: Optional[Dict[str, Callable]] = None,
        planner: Optional[AgentPlanner] = None,
        max_steps: int = MAX_STEPS,
        require_approval_for: Optional[List[str]] = None,
    ):
        """
        初始化 Agent Loop
        
        Args:
            llm_client: LLM 客户端
            tools: 可用工具字典 {name: function}
            planner: 任务规划器
            max_steps: 最大步骤数
            require_approval_for: 需要人工审批的工具列表
        """
        self.llm = llm_client
        self.tools = tools or {}
        self.planner = planner or AgentPlanner(llm_client)
        self.max_steps = max_steps
        self.require_approval = set(require_approval_for or [])
        
        # 状态
        self.current_plan: Optional[ExecutionPlan] = None
        self.execution_history: List[ExecutionPlan] = []
        
        logger.info(f"AgentLoop initialized with {len(self.tools)} tools")
    
    async def execute(
        self,
        task: str,
        intent: Optional[Intent] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[ProgressUpdate, None]:
        """
        执行任务
        
        Args:
            task: 用户任务描述
            intent: 已识别的意图（可选）
            context: 额外上下文
        
        Yields:
            ProgressUpdate 进度更新
        """
        logger.info(f"Starting execution: {task[:50]}...")
        
        try:
            # 1. 判断是否需要规划
            if not self._needs_planning(task, intent):
                # 检查是否需要轻量多步骤执行
                if self._needs_lightweight_planning(task, intent):
                    async for update in self._execute_lightweight_multistep(task, intent, context):
                        yield update
                    return
                
                # 简单任务，直接执行
                async for update in self._execute_simple(task, context):
                    yield update
                return
            
            # 2. 创建执行计划
            yield ProgressUpdate(
                type="thinking",
                message="🤔 分析任务，制定执行计划...",
            )
            
            plan = await self._create_plan(task, intent, context)
            self.current_plan = plan
            
            yield ProgressUpdate(
                type="progress",
                step=0,
                total_steps=len(plan.steps),
                message=f"📋 计划创建完成，共 {len(plan.steps)} 个步骤",
                data={"plan": plan.to_dict()},
            )
            
            # 3. 执行循环
            plan.state = LoopState.RUNNING
            
            while plan.current_step < len(plan.steps) and plan.current_step < self.max_steps:
                step = plan.steps[plan.current_step]
                step_num = plan.current_step + 1
                
                # 发送步骤开始通知
                yield ProgressUpdate(
                    type="action",
                    step=step_num,
                    total_steps=len(plan.steps),
                    message=f"🔧 步骤 {step_num}: {step.get('action', 'Unknown')}",
                    data={"step": step},
                )
                
                # 执行步骤
                result = await self._execute_step(step, step_num, context)
                plan.results.append(result)
                
                # 发送步骤结果
                if result.status == StepStatus.COMPLETED:
                    yield ProgressUpdate(
                        type="result",
                        step=step_num,
                        total_steps=len(plan.steps),
                        message=f"✅ 步骤 {step_num} 完成",
                        data={"result": result.to_dict()},
                    )
                elif result.status == StepStatus.FAILED:
                    yield ProgressUpdate(
                        type="error",
                        step=step_num,
                        total_steps=len(plan.steps),
                        message=f"❌ 步骤 {step_num} 失败: {result.error}",
                        data={"result": result.to_dict()},
                    )
                    
                    # 尝试恢复
                    recovery = await self._try_recover(plan, result)
                    if recovery:
                        yield ProgressUpdate(
                            type="thinking",
                            message=f"🔄 尝试恢复: {recovery}",
                        )
                    else:
                        # 无法恢复，终止
                        break
                
                # 检查是否需要调整计划
                if self._should_replan(plan, result):
                    yield ProgressUpdate(
                        type="thinking",
                        message="🔄 根据执行结果调整计划...",
                    )
                    
                    plan = await self._replan(plan, result)
                    self.current_plan = plan
                
                plan.current_step += 1
            
            # 4. 生成最终报告
            plan.state = LoopState.COMPLETED
            
            final_response = await self._generate_final_response(plan)
            
            yield ProgressUpdate(
                type="complete",
                step=len(plan.steps),
                total_steps=len(plan.steps),
                message=final_response,
                data={"plan": plan.to_dict()},
            )
            
            # 保存历史
            self.execution_history.append(plan)
            
        except Exception as e:
            logger.error(f"Execution failed: {e}\n{traceback.format_exc()}")
            
            if self.current_plan:
                self.current_plan.state = LoopState.FAILED
            
            yield ProgressUpdate(
                type="error",
                message=f"❌ 执行失败: {str(e)}",
            )
    
    def _needs_planning(self, task: str, intent: Optional[Intent]) -> bool:
        """判断是否需要规划"""
        # 如果有意图分析结果，使用它
        if intent:
            # 只有高复杂度任务才需要完整规划
            # medium 复杂度使用轻量模式
            return intent.complexity == "high"
        
        # 否则使用 planner 的判断
        return self.planner.should_use_planning(task)
    
    def _needs_lightweight_planning(self, task: str, intent: Optional[Intent]) -> bool:
        """判断是否需要轻量规划（直接工具链）"""
        if intent:
            return intent.is_multi_step and intent.complexity == "medium"
        return False
    
    async def _execute_simple(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
    ) -> AsyncGenerator[ProgressUpdate, None]:
        """执行简单任务（不需要规划）"""
        yield ProgressUpdate(
            type="thinking",
            message="💭 处理请求中...",
        )
        
        try:
            # 直接调用 LLM
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": task}],
                temperature=0.7,
            )
            
            yield ProgressUpdate(
                type="complete",
                message=response,
            )
            
        except Exception as e:
            yield ProgressUpdate(
                type="error",
                message=f"❌ 处理失败: {str(e)}",
            )
    
    async def _execute_lightweight_multistep(
        self,
        task: str,
        intent: Optional[Intent],
        context: Optional[Dict[str, Any]],
    ) -> AsyncGenerator[ProgressUpdate, None]:
        """
        轻量多步骤执行 - 不使用完整规划
        
        直接根据意图执行工具链，只在最后调用一次 LLM 总结
        """
        yield ProgressUpdate(
            type="thinking",
            message="⚡ 快速执行模式...",
        )
        
        tool_results = []
        suggested_tools = intent.suggested_tools if intent else []
        
        # 不需要参数的工具列表
        no_args_tools = {"process_list", "env_info", "get_current_time"}
        
        # 如果有建议的工具，只执行无参数的
        if suggested_tools:
            safe_tools = [t for t in suggested_tools if t in no_args_tools]
            
            for i, tool_name in enumerate(safe_tools[:3], 1):  # 最多 3 个工具
                tool = self.tools.get(tool_name)
                if not tool:
                    continue
                
                yield ProgressUpdate(
                    type="action",
                    step=i,
                    total_steps=len(safe_tools),
                    message=f"🔧 执行: {tool_name}",
                )
                
                try:
                    # 执行工具
                    if hasattr(tool, 'ainvoke'):
                        result = await tool.ainvoke({})
                    elif hasattr(tool, 'invoke'):
                        result = tool.invoke({})
                    elif asyncio.iscoroutinefunction(tool):
                        result = await tool()
                    else:
                        result = tool()
                    
                    tool_results.append({
                        "tool": tool_name,
                        "result": str(result)[:2000],  # 限制长度
                    })
                    
                    yield ProgressUpdate(
                        type="result",
                        step=i,
                        total_steps=len(safe_tools),
                        message=f"✅ {tool_name} 完成",
                    )
                    
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    yield ProgressUpdate(
                        type="error",
                        step=i,
                        message=f"❌ {tool_name} 失败: {str(e)}",
                    )
        
        # 如果没有工具结果，尝试智能推断工具
        if not tool_results:
            # 根据任务关键词选择工具（仅无参数工具）
            task_lower = task.lower()
            auto_tools = []
            
            # 只选择不需要参数的工具
            if "进程" in task_lower or "process" in task_lower:
                auto_tools.append("process_list")
            if "环境" in task_lower or "env" in task_lower:
                auto_tools.append("env_info")
            # 注意：list_directory 和 shell_execute 需要参数，不自动执行
            
            for tool_name in auto_tools:
                tool = self.tools.get(tool_name)
                if not tool:
                    continue
                
                yield ProgressUpdate(
                    type="action",
                    message=f"🔧 自动执行: {tool_name}",
                )
                
                try:
                    if hasattr(tool, 'ainvoke'):
                        result = await tool.ainvoke({})
                    elif hasattr(tool, 'invoke'):
                        result = tool.invoke({})
                    elif asyncio.iscoroutinefunction(tool):
                        result = await tool()
                    else:
                        result = tool()
                    
                    tool_results.append({
                        "tool": tool_name,
                        "result": str(result)[:2000],
                    })
                    
                    yield ProgressUpdate(
                        type="result",
                        message=f"✅ {tool_name} 完成",
                    )
                except Exception as e:
                    logger.error(f"Auto tool {tool_name} failed: {e}")
        
        # 生成简洁总结（单次 LLM 调用）
        if tool_results:
            yield ProgressUpdate(
                type="thinking",
                message="📝 生成分析结果...",
            )
            
            # 构建简洁的总结提示
            results_text = "\n".join([
                f"**{r['tool']}**:\n{r['result'][:1000]}"
                for r in tool_results
            ])
            
            summary_prompt = f"""用户任务: {task}

工具执行结果:
{results_text}

请简洁地总结分析结果（不超过 300 字）:"""
            
            try:
                summary = await self.llm.chat_completion(
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=0.3,
                    max_tokens=500,  # 限制输出长度
                )
                
                yield ProgressUpdate(
                    type="complete",
                    message=summary,
                )
            except Exception as e:
                # 如果总结失败，直接返回工具结果
                yield ProgressUpdate(
                    type="complete",
                    message=f"工具执行完成:\n{results_text[:1500]}",
                )
        else:
            # 没有工具结果，降级到简单执行
            async for update in self._execute_simple(task, context):
                yield update
    
    async def _create_plan(
        self,
        task: str,
        intent: Optional[Intent],
        context: Optional[Dict[str, Any]],
    ) -> ExecutionPlan:
        """创建执行计划"""
        # 使用 planner 创建计划
        plan_data = await self.planner.create_plan(task, context=context)
        
        if plan_data:
            steps = plan_data.get("steps", [])
        else:
            # 降级：单步骤计划
            steps = [{
                "step_number": 1,
                "action": task,
                "requires_tool": False,
            }]
        
        return ExecutionPlan(
            task=task,
            intent=intent,
            steps=steps,
        )
    
    async def _execute_step(
        self,
        step: Dict[str, Any],
        step_num: int,
        context: Optional[Dict[str, Any]],
    ) -> StepResult:
        """执行单个步骤"""
        start_time = datetime.now()
        
        action = Action(
            type="tool_call" if step.get("requires_tool") else "think",
            name=step.get("tool_name", ""),
            arguments=step.get("tool_args", {}),
            reasoning=step.get("action", ""),
        )
        
        try:
            if step.get("requires_tool") and step.get("tool_name"):
                # 执行工具调用
                tool_name = step["tool_name"]
                
                # 检查是否需要审批
                if tool_name in self.require_approval:
                    return StepResult(
                        step_number=step_num,
                        action=action,
                        status=StepStatus.WAITING_APPROVAL,
                        output="需要人工审批",
                    )
                
                # 获取工具
                tool = self.tools.get(tool_name)
                if not tool:
                    raise ValueError(f"工具 '{tool_name}' 不存在")
                
                # 执行工具
                tool_args = step.get("tool_args", {})
                
                # 检查是否是 StructuredTool (LangChain 工具)
                if hasattr(tool, 'invoke'):
                    # StructuredTool 使用 invoke/ainvoke
                    if hasattr(tool, 'ainvoke'):
                        result = await tool.ainvoke(tool_args)
                    else:
                        result = tool.invoke(tool_args)
                elif asyncio.iscoroutinefunction(tool):
                    result = await tool(**tool_args)
                else:
                    result = tool(**tool_args)
                
                output = result
                
            else:
                # 思考步骤，使用 LLM
                think_prompt = f"""
当前任务: {self.current_plan.task if self.current_plan else "Unknown"}
当前步骤: {step.get("action", "")}

请完成这个步骤并给出结果。
"""
                output = await self.llm.chat_completion(
                    messages=[{"role": "user", "content": think_prompt}],
                    temperature=0.5,
                )
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return StepResult(
                step_number=step_num,
                action=action,
                status=StepStatus.COMPLETED,
                output=output,
                duration_ms=int(duration),
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return StepResult(
                step_number=step_num,
                action=action,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=int(duration),
            )
    
    def _should_replan(self, plan: ExecutionPlan, result: StepResult) -> bool:
        """判断是否需要重新规划"""
        # 失败了需要重新规划
        if result.status == StepStatus.FAILED:
            return True
        
        # 检查输出是否表明需要额外步骤
        if result.output:
            output_str = str(result.output).lower()
            if any(kw in output_str for kw in ["需要", "还要", "另外", "additionally"]):
                return True
        
        return False
    
    async def _replan(
        self,
        plan: ExecutionPlan,
        result: StepResult,
    ) -> ExecutionPlan:
        """重新规划"""
        # 收集已执行结果
        execution_results = [r.to_dict() for r in plan.results]
        
        # 使用 planner 调整计划
        refined = await self.planner.refine_plan(
            {"task": plan.task, "steps": plan.steps},
            execution_results,
        )
        
        # 更新计划
        plan.steps = refined.get("steps", plan.steps)
        
        return plan
    
    async def _try_recover(
        self,
        plan: ExecutionPlan,
        failed_result: StepResult,
    ) -> Optional[str]:
        """尝试从失败中恢复"""
        # 简单重试
        if len([r for r in plan.results if r.status == StepStatus.FAILED]) < self.MAX_RETRIES:
            return "重试失败的步骤"
        
        # 跳过可选步骤
        step = plan.steps[plan.current_step]
        if step.get("optional"):
            return "跳过可选步骤，继续执行"
        
        return None
    
    async def _generate_final_response(self, plan: ExecutionPlan) -> str:
        """生成最终响应"""
        # 汇总所有结果
        results_summary = []
        for result in plan.results:
            if result.status == StepStatus.COMPLETED:
                results_summary.append(f"✅ 步骤 {result.step_number}: {result.action.reasoning}")
                if result.output:
                    output_preview = str(result.output)[:200]
                    results_summary.append(f"   结果: {output_preview}")
        
        # 使用 LLM 生成最终响应
        summary_prompt = f"""
任务: {plan.task}

执行结果:
{chr(10).join(results_summary)}

请根据以上执行结果，生成一个完整、有条理的最终响应给用户。
"""
        
        try:
            final_response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.7,
            )
            return final_response
        except Exception as e:
            logger.error(f"Failed to generate final response: {e}")
            return f"任务已完成。执行了 {len(plan.results)} 个步骤。"
    
    def abort(self):
        """中止当前执行"""
        if self.current_plan:
            self.current_plan.state = LoopState.ABORTED
            logger.info("Execution aborted")
    
    def pause(self):
        """暂停执行"""
        if self.current_plan and self.current_plan.state == LoopState.RUNNING:
            self.current_plan.state = LoopState.PAUSED
            logger.info("Execution paused")
    
    def resume(self):
        """恢复执行"""
        if self.current_plan and self.current_plan.state == LoopState.PAUSED:
            self.current_plan.state = LoopState.RUNNING
            logger.info("Execution resumed")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        if not self.current_plan:
            return {"state": "idle", "plan": None}
        
        return {
            "state": self.current_plan.state.value,
            "task": self.current_plan.task,
            "current_step": self.current_plan.current_step,
            "total_steps": len(self.current_plan.steps),
            "completed_steps": len([r for r in self.current_plan.results 
                                   if r.status == StepStatus.COMPLETED]),
            "failed_steps": len([r for r in self.current_plan.results 
                                if r.status == StepStatus.FAILED]),
        }


class LoopManager:
    """
    循环管理器
    
    管理多个会话的 AgentLoop
    """
    
    def __init__(self, llm_client, tools: Optional[Dict[str, Callable]] = None):
        self.llm = llm_client
        self.tools = tools or {}
        self.loops: Dict[str, AgentLoop] = {}
    
    def get_or_create(self, session_id: str) -> AgentLoop:
        """获取或创建会话的 AgentLoop"""
        if session_id not in self.loops:
            self.loops[session_id] = AgentLoop(
                llm_client=self.llm,
                tools=self.tools,
            )
        return self.loops[session_id]
    
    def remove(self, session_id: str):
        """移除会话的 AgentLoop"""
        if session_id in self.loops:
            del self.loops[session_id]


# 全局实例
_loop_manager: Optional[LoopManager] = None


def get_loop_manager(llm_client=None, tools=None) -> LoopManager:
    """获取循环管理器实例"""
    global _loop_manager
    if _loop_manager is None:
        if llm_client is None:
            raise ValueError("First call requires llm_client")
        _loop_manager = LoopManager(llm_client, tools)
    return _loop_manager

