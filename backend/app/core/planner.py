# -*- coding: utf-8 -*-
"""
任务规划器 - Planning 能力
基于 Chain-of-Thought 和任务分解

注意：LangChain 1.0 提供了 TodoListMiddleware，可以自动为 Agent 添加任务规划能力。
本模块作为独立的规划器实现，可用于:
1. 需要独立于 Agent 进行规划的场景
2. 需要自定义规划逻辑的场景
3. 与非 LangChain Agent 集成的场景

推荐使用方式：
- 简单场景：使用 TodoListMiddleware
- 复杂场景：使用本模块的 AgentPlanner
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from ..models.chat import ChatMessage


class AgentPlanner:
    """
    任务规划器
    
    职责:
    1. 分析用户意图
    2. 将复杂任务分解为子任务
    3. 生成执行计划
    4. 动态调整计划
    
    LangChain 1.0 替代方案:
    - 使用 TodoListMiddleware 可以让 Agent 自动管理任务列表
    - 使用 create_agent 的 system_prompt 可以引导 Agent 进行规划
    """
    
    def __init__(self, llm_client):
        self.llm = llm_client
        logger.info("AgentPlanner initialized")
    
    async def create_plan(
        self,
        user_message: str,
        history: Optional[List[ChatMessage]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        创建执行计划
        
        Args:
            user_message: 用户消息
            history: 对话历史
            context: 额外上下文
        
        Returns:
            计划字典，包含步骤和策略
        """
        logger.info(f"Creating plan for: {user_message[:50]}...")
        
        # 构建规划提示词
        prompt = self._build_planning_prompt(user_message, history, context)
        
        # 调用LLM生成计划
        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # 较低温度，更确定性
            )
            
            # 解析计划
            plan = self._parse_plan(response)
            
            logger.info(f"Plan created with {len(plan.get('steps', []))} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Planning error: {e}")
            return None
    
    def _build_planning_prompt(
        self,
        message: str,
        history: Optional[List[ChatMessage]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """构建规划提示词"""
        
        prompt_parts = [
            "你是一个任务规划专家。请为以下用户请求创建详细的执行计划。",
            "",
            "## 用户请求",
            message,
        ]
        
        if history:
            prompt_parts.extend([
                "",
                "## 对话上下文",
            ])
            for msg in history[-3:]:
                prompt_parts.append(f"{msg.role.value}: {msg.content[:100]}")
        
        prompt_parts.extend([
            "",
            "## 请输出以下格式的计划:",
            "```json",
            "{",
            '  "task_type": "simple/complex",',
            '  "summary": "计划概要",',
            '  "steps": [',
            '    {',
            '      "step_number": 1,',
            '      "action": "步骤描述",',
            '      "requires_tool": true/false,',
            '      "tool_name": "工具名称(如果需要)",',
            '      "expected_output": "期望输出"',
            '    }',
            '  ],',
            '  "complexity": "low/medium/high"',
            "}",
            "```",
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_plan(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的计划"""
        import json
        import re
        
        # 提取JSON
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        
        if json_match:
            try:
                plan = json.loads(json_match.group(1))
                return plan
            except json.JSONDecodeError:
                logger.error("Failed to parse plan JSON")
        
        # 降级: 简单计划
        return {
            "task_type": "simple",
            "summary": "直接回答用户问题",
            "steps": [
                {
                    "step_number": 1,
                    "action": "理解问题并给出答案",
                    "requires_tool": False,
                }
            ],
            "complexity": "low",
        }
    
    async def refine_plan(
        self,
        original_plan: Dict[str, Any],
        execution_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        根据执行结果优化计划
        
        Args:
            original_plan: 原始计划
            execution_results: 已执行步骤的结果
        
        Returns:
            优化后的计划
        """
        logger.info("Refining plan based on execution results")
        
        # TODO: 实现计划优化逻辑
        # 可以根据执行结果动态调整后续步骤
        
        return original_plan
    
    def should_use_planning(self, message: str) -> bool:
        """
        判断是否需要规划
        
        简单问题直接回答，复杂问题才规划
        """
        # 简单启发式规则
        complex_keywords = [
            "帮我", "需要", "分析", "比较", "总结",
            "多个", "步骤", "计划", "流程",
        ]
        
        return any(keyword in message for keyword in complex_keywords)
