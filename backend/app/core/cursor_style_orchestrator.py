# -*- coding: utf-8 -*-
"""
Cursor 风格编排器 - Cursor-Style Orchestrator

这是 agentic_chatBot 的核心引擎，整合所有能力：
1. 深度意图识别 (IntentRecognizer)
2. 自主执行循环 (AgentLoop)
3. 智能工具编排 (ToolOrchestrator)
4. 上下文工程 (ContextManager)
5. 用户偏好学习 (UserPreferences)
6. RAG 知识检索
7. 技能系统 (Skills)
8. 记忆管理 (Memory)

目标：让 ChatBot 能力媲美 Cursor！
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
import asyncio
import traceback

# 核心组件导入
from .intent_recognizer import (
    IntentRecognizer, Intent, TaskType, RequiredCapability, get_intent_recognizer
)
from .agent_loop import (
    AgentLoop, ProgressUpdate, ExecutionPlan, LoopState
)
from .tool_orchestrator import (
    ToolOrchestrator, ToolSelection, get_tool_orchestrator
)
from .context_manager import (
    ContextManager, ContextSource, build_context
)
from .user_preferences import (
    UserPreferenceManager, get_preference_manager
)
from .planner import AgentPlanner
from .memory import MemoryManager
from .skills import SkillsManager, get_skills_manager


@dataclass
class ChatResponse:
    """
    聊天响应
    
    包含完整的响应信息
    """
    content: str
    intent: Optional[Intent] = None
    used_tools: List[str] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)
    execution_steps: int = 0
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "intent": self.intent.to_dict() if self.intent else None,
            "used_tools": self.used_tools,
            "citations": self.citations,
            "execution_steps": self.execution_steps,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class StreamChunk:
    """
    流式输出块
    """
    type: str  # text, thinking, tool_call, tool_result, progress, complete, error
    content: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
        }


class CursorStyleOrchestrator:
    """
    Cursor 风格编排器
    
    统一管理所有 AI 能力，提供 Cursor 级别的 ChatBot 体验。
    
    使用示例:
    ```python
    orchestrator = CursorStyleOrchestrator(llm_client)
    
    # 流式对话
    async for chunk in orchestrator.chat_stream("分析这个项目", session_id):
        if chunk.type == "text":
            print(chunk.content, end="")
        elif chunk.type == "thinking":
            print(f"💭 {chunk.content}")
    
    # 非流式对话
    response = await orchestrator.chat("你好", session_id)
    print(response.content)
    ```
    """
    
    def __init__(
        self,
        llm_client,
        tools: Optional[List[Callable]] = None,
        enable_rag: bool = True,
        enable_skills: bool = True,
        enable_memory: bool = True,
        enable_preferences: bool = True,
        max_context_tokens: int = 8000,
    ):
        """
        初始化编排器
        
        Args:
            llm_client: LLM 客户端
            tools: 工具函数列表
            enable_rag: 是否启用 RAG
            enable_skills: 是否启用技能系统
            enable_memory: 是否启用记忆
            enable_preferences: 是否启用用户偏好学习
            max_context_tokens: 最大上下文 Token 数
        """
        self.llm = llm_client
        self.max_context_tokens = max_context_tokens
        
        # 功能开关
        self.enable_rag = enable_rag
        self.enable_skills = enable_skills
        self.enable_memory = enable_memory
        self.enable_preferences = enable_preferences
        
        # 初始化核心组件
        self.intent_recognizer = get_intent_recognizer(llm_client)
        self.planner = AgentPlanner(llm_client)
        self.tool_orchestrator = get_tool_orchestrator(llm_client)
        self.preference_manager = get_preference_manager() if enable_preferences else None
        self.memory_manager = MemoryManager() if enable_memory else None
        self.skill_manager = get_skills_manager() if enable_skills else None
        
        # 注册工具
        if tools:
            self.tool_orchestrator.register_many(tools)
        
        # 会话状态
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            f"CursorStyleOrchestrator initialized: "
            f"RAG={enable_rag}, Skills={enable_skills}, "
            f"Memory={enable_memory}, Preferences={enable_preferences}"
        )
    
    async def chat_stream(
        self,
        message: str,
        session_id: str,
        user_id: Optional[str] = None,
        files: Optional[Dict[str, str]] = None,
        rag_query: Optional[str] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        流式对话接口 - 纯 ReAct 模式
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            user_id: 用户 ID（可选）
            files: 引用的文件 {path: content}
            rag_query: RAG 查询（可选，默认使用 message）
        
        Yields:
            StreamChunk 流式输出块
        """
        start_time = datetime.now()
        user_id = user_id or session_id
        used_tools = []
        
        try:
            # ==================== 1. 构建上下文 ====================
            yield StreamChunk(type="thinking", content="📚 收集相关信息...")
            
            # 简单意图识别（仅用于上下文构建，不用于路由）
            intent = await self.intent_recognizer.recognize(
                message,
                history=self._get_conversation_history(session_id),
                available_tools=list(self.tool_orchestrator.tools.keys()),
            )
            
            logger.info(f"Intent (for context): {intent.task_type.value}")
            
            context = await self._build_context(
                message=message,
                session_id=session_id,
                user_id=user_id,
                intent=intent,
                files=files,
                rag_query=rag_query,
            )
            
            # ==================== 2. 纯 ReAct 模式处理 ====================
            
            assistant_response_parts = []
            
            async for chunk in self._handle_react(message, context, session_id, user_id):
                if chunk.type == "text":
                    assistant_response_parts.append(chunk.content or "")
                yield chunk
                if chunk.metadata and chunk.metadata.get("tool"):
                    used_tools.append(chunk.metadata["tool"])
            
            # ==================== 4. 学习和记录 ====================
            if self.enable_preferences:
                self.preference_manager.learn_from_message(user_id, message)
                for tool in used_tools:
                    self.preference_manager.learn_from_tool_usage(user_id, tool, True)
            
            # 记录对话 - 用户消息和助手回复
            await self._save_conversation(session_id, message, "user")
            assistant_response = "".join(assistant_response_parts)
            if assistant_response:
                await self._save_conversation(session_id, assistant_response, "assistant")
            
            # 计算耗时
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            yield StreamChunk(
                type="complete",
                content="",
                metadata={
                    "duration_ms": int(duration),
                    "used_tools": used_tools,
                    "intent": intent.to_dict(),
                },
            )
            
        except Exception as e:
            logger.error(f"Chat error: {e}\n{traceback.format_exc()}")
            yield StreamChunk(
                type="error",
                content=f"❌ 处理失败: {str(e)}",
            )
    
    async def chat(
        self,
        message: str,
        session_id: str,
        user_id: Optional[str] = None,
        files: Optional[Dict[str, str]] = None,
    ) -> ChatResponse:
        """
        非流式对话接口
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            user_id: 用户 ID
            files: 引用的文件
        
        Returns:
            ChatResponse 完整响应
        """
        content_parts = []
        used_tools = []
        intent = None
        duration = 0
        
        async for chunk in self.chat_stream(message, session_id, user_id, files):
            if chunk.type == "text":
                content_parts.append(chunk.content)
            elif chunk.type in ["tool_call", "tool_result"]:
                if chunk.metadata and chunk.metadata.get("tool"):
                    used_tools.append(chunk.metadata["tool"])
            elif chunk.type == "complete" and chunk.metadata:
                intent_data = chunk.metadata.get("intent")
                if intent_data:
                    intent = Intent(**intent_data) if isinstance(intent_data, dict) else intent_data
                duration = chunk.metadata.get("duration_ms", 0)
        
        return ChatResponse(
            content="".join(content_parts),
            intent=intent,
            used_tools=list(set(used_tools)),
            duration_ms=duration,
        )
    
    async def _build_context(
        self,
        message: str,
        session_id: str,
        user_id: str,
        intent: Intent,
        files: Optional[Dict[str, str]] = None,
        rag_query: Optional[str] = None,
    ) -> str:
        """构建完整上下文"""
        cm = ContextManager(max_tokens=self.max_context_tokens)
        
        # 1. 用户偏好（风格提示）- 仅对非简单对话应用
        # 对于简单对话（如问候），跳过详细偏好以加快响应
        if self.enable_preferences and intent.task_type != TaskType.CONVERSATION:
            style_prompt = self.preference_manager.get_style_prompt(user_id)
            if style_prompt:
                cm.add(
                    content=style_prompt,
                    source=ContextSource.SYSTEM,
                    title="用户偏好",
                )
        
        # 2. 技能指令
        if self.enable_skills and RequiredCapability.SKILLS in intent.required_capabilities:
            relevant_skills = self.skill_manager.match_skills(message)
            for skill in relevant_skills[:2]:
                # Convert examples from Dict to formatted strings
                examples_str = []
                if skill.examples:
                    for ex in skill.examples:
                        if isinstance(ex, dict):
                            examples_str.append(f"用户: {ex.get('user', '')}\n助手: {ex.get('assistant', '')}")
                        else:
                            examples_str.append(str(ex))
                cm.add_skill_instructions(
                    skill.name,
                    skill.instructions,
                    examples_str if examples_str else None,
                )
        
        # 3. RAG 检索
        if self.enable_rag and RequiredCapability.RAG in intent.required_capabilities:
            try:
                from ..rag import retriever
                rag_results = await retriever.retrieve(
                    query=rag_query or message,
                    top_k=5,
                )
                cm.add_rag_results(rag_results)
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")
        
        # 4. 文件内容
        if files:
            for path, content in files.items():
                cm.add_file_content(path, content)
        
        # 5. 长期记忆
        if self.enable_memory and RequiredCapability.MEMORY in intent.required_capabilities:
            try:
                memories = await self.memory_manager.get_relevant_long_term_memory(
                    session_id, message
                )
                cm.add_memory(memories)
            except Exception as e:
                logger.warning(f"Memory retrieval failed: {e}")
        
        # 6. 对话历史
        history = self._get_conversation_history(session_id)
        if history:
            cm.add_conversation_history(history, max_messages=5)
        
        return cm.build()
    
    async def _handle_react(
        self,
        message: str,
        context: str,
        session_id: str,
        user_id: str,
        max_iterations: int = 5,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        纯 ReAct 模式处理
        
        ReAct 循环:
        1. Thought: LLM 分析问题，决定下一步
        2. Action: 如果需要，调用工具
        3. Observation: 获取工具结果
        4. 重复直到 LLM 给出 Final Answer
        """
        import re
        import json
        
        tool_info = self._get_tool_info_for_react()
        
        # ReAct 系统提示
        system_prompt = f"""你是一个智能 AI 助手，使用 ReAct（Reasoning + Acting）模式来帮助用户。

## 可用工具

{tool_info}

## ReAct 格式

每次回复请使用以下格式：

**如果需要使用工具：**
```
Thought: [分析当前情况，思考下一步该做什么]
Action: <tool_call>{{"tool": "工具名", "args": {{"参数": "值"}}}}</tool_call>
```

**如果可以直接回答（不需要工具或已获得足够信息）：**
```
Thought: [总结思考过程]
Final Answer: [给用户的完整回复]
```

## 重要规则

1. **每次只执行一个 Action**，等待 Observation 后再决定下一步
2. **文件/目录操作**：用户提到路径时，使用 list_directory 或 file_read_enhanced
3. **系统命令**：用户需要执行命令时，使用 shell_execute
4. **永远不要说"我无法访问"**，你有工具可以访问文件系统
5. **简单对话**（如问候、感谢）可以直接给出 Final Answer

## 上下文信息

{context}
"""
        
        # 对话历史（用于 ReAct 循环）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]
        
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            
            yield StreamChunk(
                type="thinking", 
                content=f"🧠 思考中... (步骤 {iteration}/{max_iterations})"
            )
            
            try:
                response = await self.llm.chat_completion(
                    messages=messages,
                    temperature=0.3,
                )
            except Exception as e:
                yield StreamChunk(type="error", content=f"LLM 调用失败: {str(e)}")
                return
            
            # 检查是否有 Final Answer
            final_match = re.search(r'Final Answer:\s*(.+)', response, re.DOTALL)
            if final_match:
                final_answer = final_match.group(1).strip()
                yield StreamChunk(type="text", content=final_answer)
                return
            
            # 检查是否有工具调用
            tool_match = re.search(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', response, re.DOTALL)
            if tool_match:
                try:
                    call = json.loads(tool_match.group(1))
                    tool_name = call.get("tool")
                    args = call.get("args", {})
                    
                    if tool_name and tool_name in self.tool_orchestrator.tools:
                        yield StreamChunk(
                            type="tool_call",
                            content=f"🔧 执行 {tool_name}...",
                            metadata={"tool": tool_name, "args": args},
                        )
                        
                        success, output = await self.tool_orchestrator.execute(tool_name, args)
                        
                        # 限制输出长度
                        output_str = str(output)[:3000]
                        
                        yield StreamChunk(
                            type="tool_result",
                            content=f"{'✅' if success else '❌'} {tool_name}",
                            metadata={"tool": tool_name, "success": success},
                        )
                        
                        # 将结果添加到对话历史，继续 ReAct 循环
                        messages.append({"role": "assistant", "content": response})
                        messages.append({
                            "role": "user", 
                            "content": f"Observation: {output_str}\n\n请继续分析并决定下一步。如果已有足够信息，请给出 Final Answer。"
                        })
                        continue
                    else:
                        # 工具不存在
                        messages.append({"role": "assistant", "content": response})
                        messages.append({
                            "role": "user",
                            "content": f"Observation: 错误 - 工具 '{tool_name}' 不存在。可用工具: {list(self.tool_orchestrator.tools.keys())}"
                        })
                        continue
                        
                except json.JSONDecodeError as e:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": f"Observation: 工具调用格式错误: {str(e)}。请使用正确的 JSON 格式。"
                    })
                    continue
            
            # 没有工具调用也没有 Final Answer，可能是直接回复
            # 尝试提取 Thought 后的内容作为回复
            thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Final Answer:|$)', response, re.DOTALL)
            if thought_match and not tool_match:
                # LLM 可能忘记了 Final Answer 格式，直接使用回复
                yield StreamChunk(type="text", content=response)
                return
            
            # 其他情况，直接返回 LLM 的回复
            yield StreamChunk(type="text", content=response)
            return
        
        # 达到最大迭代次数
        yield StreamChunk(
            type="text", 
            content="抱歉，这个问题比较复杂，我尝试了多次但未能完全解决。以下是我目前的分析结果..."
        )
    
    async def _handle_conversation(
        self,
        message: str,
        context: str,
        user_id: str,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        处理对话 - 已弃用，统一使用 _handle_react
        """
        # 保留此方法以兼容，但实际上已不再使用
        tool_info = self._get_tool_info_for_react()
        
        prompt = f"""你是一个智能 AI 助手，可以使用以下工具来帮助用户：

{tool_info}

{context}

用户: {message}

## 回复规则

1. **如果需要使用工具**，请用以下格式（可多次使用）：
   <tool_call>
   {{"tool": "工具名", "args": {{"参数名": "参数值"}}}}
   </tool_call>

2. **如果不需要工具**，直接回复用户。

3. **关于文件操作**：
   - 用户提到路径时，直接使用 list_directory 或 file_read_enhanced
   - 用户说"分析项目"时，先用 list_directory 查看结构
   - 不要说"我无法访问文件系统"，你有工具可以访问

请回复："""
        
        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            if "<tool_call>" in response:
                async for chunk in self._execute_react_tools(response, message, context):
                    yield chunk
            else:
                yield StreamChunk(type="text", content=response)
            
        except Exception as e:
            yield StreamChunk(type="error", content=f"回复失败: {str(e)}")
    
    async def _execute_react_tools(
        self,
        llm_response: str,
        original_message: str,
        context: str,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        执行 ReAct 模式中 LLM 请求的工具调用
        """
        import re
        import json
        
        # 提取所有工具调用
        tool_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        tool_calls = re.findall(tool_pattern, llm_response, re.DOTALL)
        
        if not tool_calls:
            # 没有有效的工具调用，返回原始响应
            yield StreamChunk(type="text", content=llm_response)
            return
        
        results = []
        for call_json in tool_calls:
            try:
                call = json.loads(call_json)
                tool_name = call.get("tool")
                args = call.get("args", {})
                
                if tool_name and tool_name in self.tool_orchestrator.tools:
                    yield StreamChunk(
                        type="tool_call",
                        content=f"🔧 执行 {tool_name}...",
                        metadata={"tool": tool_name, "args": args},
                    )
                    
                    success, output = await self.tool_orchestrator.execute(tool_name, args)
                    
                    results.append({
                        "tool": tool_name,
                        "success": success,
                        "output": str(output)[:2000],  # 限制长度
                    })
                    
                    yield StreamChunk(
                        type="tool_result",
                        content=f"{'✅' if success else '❌'} {tool_name}",
                        metadata={"tool": tool_name, "success": success},
                    )
            except json.JSONDecodeError:
                continue
        
        if not results:
            yield StreamChunk(type="text", content=llm_response)
            return
        
        # 根据工具结果生成最终回复
        results_text = "\n\n".join([
            f"### {r['tool']}\n```\n{r['output']}\n```" for r in results
        ])
        
        summary_prompt = f"""
{context}

用户问题: {original_message}

工具执行结果:
{results_text}

请根据以上工具执行结果，给用户一个完整、有帮助的回复。如果是分析项目，请总结项目的主要内容和结构。"""
        
        try:
            summary = await self.llm.chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.5,
            )
            yield StreamChunk(type="text", content=summary)
        except Exception as e:
            # 降级：直接返回工具结果
            yield StreamChunk(type="text", content=f"工具执行结果:\n{results_text}")
    
    async def _handle_simple_task(
        self,
        message: str,
        context: str,
        user_id: str,
    ) -> AsyncGenerator[StreamChunk, None]:
        """处理简单任务"""
        prompt = f"""
{context}

用户请求: {message}

请根据上下文信息，完成用户的请求。"""
        
        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            
            yield StreamChunk(type="text", content=response)
            
        except Exception as e:
            yield StreamChunk(type="error", content=f"处理失败: {str(e)}")
    
    async def _handle_tool_task(
        self,
        message: str,
        intent: Intent,
        context: str,
        user_id: str,
    ) -> AsyncGenerator[StreamChunk, None]:
        """处理工具任务"""
        # 选择工具
        yield StreamChunk(type="thinking", content="🔧 选择合适的工具...")
        
        # 优先使用意图中建议的工具
        selections = []
        if intent.suggested_tools:
            for tool_name in intent.suggested_tools:
                if tool_name in self.tool_orchestrator.tools:
                    # 从消息中提取参数
                    args = self._extract_tool_args(tool_name, message, intent)
                    selections.append(ToolSelection(
                        tool_name=tool_name,
                        confidence=0.9,
                        reason=f"意图建议使用 {tool_name}",
                        arguments=args,
                    ))
        
        # 如果意图没有建议工具，则使用关键词匹配
        if not selections:
            selections = await self.tool_orchestrator.select_tools(message, max_tools=3)
        
        if not selections:
            # 没有合适的工具，降级为普通回复
            async for chunk in self._handle_simple_task(message, context, user_id):
                yield chunk
            return
        
        # 执行工具
        results = []
        for sel in selections:
            yield StreamChunk(
                type="tool_call",
                content=f"🔧 执行 {sel.tool_name}...",
                metadata={"tool": sel.tool_name, "reason": sel.reason},
            )
            
            success, output = await self.tool_orchestrator.execute(
                sel.tool_name,
                sel.arguments,
            )
            
            results.append({
                "tool": sel.tool_name,
                "success": success,
                "output": output,
            })
            
            yield StreamChunk(
                type="tool_result",
                content=f"{'✅' if success else '❌'} {sel.tool_name}: {str(output)[:200]}",
                metadata={"tool": sel.tool_name, "success": success},
            )
        
        # 生成最终回复
        result_text = "\n".join([
            f"- {r['tool']}: {r['output']}" for r in results
        ])
        
        prompt = f"""
{context}

用户请求: {message}

工具执行结果:
{result_text}

请根据工具执行结果，给用户一个完整的回复。"""
        
        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            
            yield StreamChunk(type="text", content=response)
            
        except Exception as e:
            yield StreamChunk(type="error", content=f"回复生成失败: {str(e)}")
    
    async def _handle_complex_task(
        self,
        message: str,
        intent: Intent,
        context: str,
        session_id: str,
        user_id: str,
    ) -> AsyncGenerator[StreamChunk, None]:
        """处理复杂任务（使用 Agent Loop）"""
        yield StreamChunk(
            type="thinking",
            content=f"🎯 检测到复杂任务 (预计 {intent.estimated_steps} 步)，启动 Agent 模式...",
        )
        
        # 创建 Agent Loop
        loop = AgentLoop(
            llm_client=self.llm,
            tools=self.tool_orchestrator.tools,
            planner=self.planner,
            max_steps=min(intent.estimated_steps + 5, 15),
        )
        
        # 执行
        final_content = ""
        
        async for update in loop.execute(message, intent, {"context": context}):
            if update.type == "thinking":
                yield StreamChunk(type="thinking", content=update.message)
                
            elif update.type == "action":
                tool_name = update.data.get("step", {}).get("tool_name", "") if update.data else ""
                yield StreamChunk(
                    type="tool_call",
                    content=update.message,
                    metadata={"tool": tool_name, "step": update.step},
                )
                
            elif update.type == "result":
                yield StreamChunk(
                    type="tool_result",
                    content=update.message,
                    metadata=update.data,
                )
                
            elif update.type == "progress":
                yield StreamChunk(
                    type="progress",
                    content=update.message,
                    metadata={
                        "step": update.step,
                        "total": update.total_steps,
                    },
                )
                
            elif update.type == "complete":
                final_content = update.message
                yield StreamChunk(type="text", content=update.message)
                
            elif update.type == "error":
                yield StreamChunk(type="error", content=update.message)
    
    def _get_conversation_history(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> List[Dict[str, str]]:
        """获取对话历史"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {"history": []}
        
        history = self.sessions[session_id].get("history", [])
        return history[-max_messages:]
    
    def _extract_tool_args(self, tool_name: str, message: str, intent: Intent) -> Dict[str, Any]:
        """
        从消息和意图中提取工具参数
        
        Args:
            tool_name: 工具名称
            message: 用户消息
            intent: 识别的意图
        
        Returns:
            工具参数字典
        """
        import re
        args = {}
        
        # 提取路径参数 - 只匹配 ASCII 路径字符（不包含中文）
        path_match = re.search(r'([/\\][a-zA-Z0-9_\-\.\/\\]+)', message)
        
        if tool_name == "list_directory":
            if path_match:
                args["path"] = path_match.group(1)
            else:
                args["path"] = "."  # 默认当前目录
                
        elif tool_name == "file_read_enhanced":
            if path_match:
                args["file_path"] = path_match.group(1)
            # 从意图实体中获取
            if intent.entities and "file_paths" in intent.entities:
                paths = intent.entities["file_paths"]
                if paths:
                    args["file_path"] = paths[0]
                    
        elif tool_name == "shell_execute":
            # 对于 shell 命令，提取引号内容或关键词后内容
            cmd_match = re.search(r'[`\'\"](.*?)[`\'\"]', message)
            if cmd_match:
                args["command"] = cmd_match.group(1)
                
        elif tool_name == "env_info":
            pass  # 无需参数
            
        elif tool_name == "process_list":
            pass  # 无需参数
        
        return args
    
    def _get_tool_info_for_prompt(self) -> str:
        """获取工具信息用于提示词"""
        tool_lines = ["## 可用工具\n"]
        
        for name, meta in self.tool_orchestrator.metadata.items():
            desc = meta.description[:80] if meta.description else "无描述"
            tool_lines.append(f"- **{name}**: {desc}")
        
        tool_lines.append("\n如果用户需要使用这些功能，请告知用户你可以帮忙执行。")
        return "\n".join(tool_lines)
    
    def _get_tool_info_for_react(self) -> str:
        """获取工具信息用于 ReAct 模式（包含参数说明）"""
        tool_lines = ["## 可用工具\n"]
        
        for name, meta in self.tool_orchestrator.metadata.items():
            desc = meta.description if meta.description else "无描述"
            tool_lines.append(f"### {name}")
            tool_lines.append(f"描述: {desc}")
            
            # 添加参数说明
            if meta.input_schema and "properties" in meta.input_schema:
                params = []
                for param_name, param_info in meta.input_schema["properties"].items():
                    param_type = param_info.get("type", "string")
                    param_desc = param_info.get("description", "")
                    required = param_name in meta.input_schema.get("required", [])
                    params.append(f"  - {param_name} ({param_type}{'*' if required else ''}): {param_desc}")
                if params:
                    tool_lines.append("参数:")
                    tool_lines.extend(params)
            tool_lines.append("")
        
        return "\n".join(tool_lines)
    
    async def _save_conversation(
        self,
        session_id: str,
        content: str,
        role: str,
    ) -> None:
        """保存对话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {"history": []}
        
        self.sessions[session_id]["history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        
        # 限制历史长度
        if len(self.sessions[session_id]["history"]) > 50:
            self.sessions[session_id]["history"] = self.sessions[session_id]["history"][-50:]
    
    def clear_session(self, session_id: str) -> None:
        """清除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        logger.info(f"Session {session_id} cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "active_sessions": len(self.sessions),
            "total_tools": len(self.tool_orchestrator.tools),
            "enabled_features": {
                "rag": self.enable_rag,
                "skills": self.enable_skills,
                "memory": self.enable_memory,
                "preferences": self.enable_preferences,
            },
        }


# 全局实例
_orchestrator: Optional[CursorStyleOrchestrator] = None


def get_orchestrator(
    llm_client=None,
    tools: Optional[List[Callable]] = None,
    **kwargs,
) -> CursorStyleOrchestrator:
    """获取编排器实例"""
    global _orchestrator
    if _orchestrator is None:
        if llm_client is None:
            raise ValueError("First call requires llm_client")
        _orchestrator = CursorStyleOrchestrator(llm_client, tools, **kwargs)
    return _orchestrator

