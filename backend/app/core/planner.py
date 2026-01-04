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
        
        动态调整策略：
        1. 如果步骤失败，生成替代方案
        2. 如果发现新信息，添加额外步骤
        3. 如果任务比预期简单，简化后续步骤
        4. 如果任务比预期复杂，拆分步骤
        
        Args:
            original_plan: 原始计划
            execution_results: 已执行步骤的结果
        
        Returns:
            优化后的计划
        """
        logger.info("Refining plan based on execution results")
        
        if not execution_results:
            return original_plan
        
        # 分析执行结果
        failed_steps = [r for r in execution_results if not r.get("success", True)]
        successful_steps = [r for r in execution_results if r.get("success", True)]
        
        # 如果没有失败，检查是否需要添加步骤
        if not failed_steps:
            # 检查是否发现了新信息需要额外处理
            new_info = self._extract_new_info(successful_steps)
            if new_info:
                return self._add_follow_up_steps(original_plan, new_info)
            return original_plan
        
        # 有失败的步骤，需要调整计划
        try:
            refined_plan = await self._generate_refined_plan(
                original_plan, 
                execution_results
            )
            return refined_plan
        except Exception as e:
            logger.error(f"Plan refinement failed: {e}")
            return self._create_fallback_plan(original_plan, failed_steps)
    
    def _extract_new_info(self, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """从执行结果中提取新发现的信息"""
        new_info = {}
        
        for result in results:
            output = result.get("output", "")
            
            # 检测是否发现了额外的任务
            if any(keyword in str(output).lower() for keyword in 
                   ["also need", "另外需要", "还需要", "additionally", "furthermore"]):
                new_info["additional_tasks"] = output
            
            # 检测是否发现了依赖
            if any(keyword in str(output).lower() for keyword in 
                   ["depends on", "依赖", "prerequisite", "先决条件"]):
                new_info["dependencies"] = output
            
            # 检测是否发现了更多细节
            if any(keyword in str(output).lower() for keyword in 
                   ["multiple", "多个", "several", "各个"]):
                new_info["details"] = output
        
        return new_info if new_info else None
    
    def _add_follow_up_steps(
        self, 
        plan: Dict[str, Any], 
        new_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """根据新信息添加后续步骤"""
        refined_plan = plan.copy()
        steps = list(refined_plan.get("steps", []))
        
        next_step_num = len(steps) + 1
        
        if "additional_tasks" in new_info:
            steps.append({
                "step_number": next_step_num,
                "action": "处理额外发现的任务",
                "requires_tool": False,
                "expected_output": "完成额外任务",
                "added_reason": "执行过程中发现需要额外处理",
            })
            next_step_num += 1
        
        if "dependencies" in new_info:
            # 将依赖步骤插入到合适位置
            dependency_step = {
                "step_number": 0,  # 会被重新编号
                "action": "处理发现的依赖项",
                "requires_tool": True,
                "expected_output": "解决依赖问题",
                "added_reason": "发现依赖关系",
            }
            steps.insert(0, dependency_step)
            # 重新编号
            for i, step in enumerate(steps):
                step["step_number"] = i + 1
        
        refined_plan["steps"] = steps
        refined_plan["refined"] = True
        refined_plan["refinement_reason"] = "发现新信息，添加了后续步骤"
        
        return refined_plan
    
    async def _generate_refined_plan(
        self,
        original_plan: Dict[str, Any],
        execution_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """使用 LLM 生成优化的计划"""
        import json
        
        prompt = f"""你是一个任务规划专家。原始计划在执行过程中遇到了问题，请根据执行结果优化计划。

## 原始计划
```json
{json.dumps(original_plan, ensure_ascii=False, indent=2)}
```

## 执行结果
```json
{json.dumps(execution_results, ensure_ascii=False, indent=2)}
```

## 请分析失败原因并输出优化后的计划

优化策略：
1. 对于失败的步骤，提供替代方案
2. 如果需要，添加额外的准备步骤
3. 调整步骤顺序以避免类似问题
4. 简化不必要的复杂步骤

请输出与原始计划相同格式的 JSON：
```json
{{
  "task_type": "...",
  "summary": "优化后的计划概要",
  "steps": [...],
  "complexity": "...",
  "refined": true,
  "refinement_reason": "优化原因说明"
}}
```
"""
        
        response = await self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        return self._parse_plan(response)
    
    def _create_fallback_plan(
        self, 
        original_plan: Dict[str, Any], 
        failed_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建降级计划（当 LLM 优化失败时）"""
        fallback_plan = original_plan.copy()
        steps = list(fallback_plan.get("steps", []))
        
        # 标记失败的步骤并添加重试
        failed_step_nums = {r.get("step_number") for r in failed_steps}
        
        new_steps = []
        for step in steps:
            new_steps.append(step)
            if step.get("step_number") in failed_step_nums:
                # 添加重试步骤
                retry_step = step.copy()
                retry_step["step_number"] = step["step_number"] + 0.5
                retry_step["action"] = f"[重试] {step.get('action', '')}"
                retry_step["is_retry"] = True
                new_steps.append(retry_step)
        
        # 重新编号
        for i, step in enumerate(new_steps):
            step["step_number"] = i + 1
        
        fallback_plan["steps"] = new_steps
        fallback_plan["refined"] = True
        fallback_plan["refinement_reason"] = "添加重试步骤处理失败情况"
        
        return fallback_plan
    
    def should_use_planning(self, message: str) -> bool:
        """
        判断是否需要规划
        
        使用多维度评估：
        1. 任务复杂度关键词
        2. 消息长度
        3. 多任务指示词
        4. 工具调用暗示
        
        简单问题直接回答，复杂问题才规划
        """
        message_lower = message.lower()
        
        # 1. 明确的多步骤任务关键词
        multi_step_keywords = [
            "首先", "然后", "接着", "最后", "第一步", "第二步",
            "first", "then", "next", "finally", "step 1", "step 2",
            "1.", "2.", "1)", "2)",
        ]
        if any(keyword in message_lower for keyword in multi_step_keywords):
            return True
        
        # 2. 复杂任务指示词
        complex_keywords = [
            "帮我", "分析", "比较", "总结", "调研", "评估",
            "设计", "规划", "制定", "整理", "梳理", "汇总",
            "analyze", "compare", "summarize", "research", "evaluate",
            "design", "plan", "organize", "compile",
        ]
        complex_count = sum(1 for kw in complex_keywords if kw in message_lower)
        if complex_count >= 2:
            return True
        
        # 3. 多任务指示词
        multi_task_keywords = [
            "多个", "几个", "所有", "各个", "每个", "批量",
            "multiple", "several", "all", "each", "batch",
            "和", "以及", "同时", "另外", "还要",
            "and also", "as well as", "in addition",
        ]
        if any(keyword in message_lower for keyword in multi_task_keywords):
            if len(message) > 50:  # 结合消息长度判断
                return True
        
        # 4. 消息很长，可能包含复杂需求
        if len(message) > 200:
            return True
        
        # 5. 包含文件路径或代码相关操作
        code_keywords = [
            "@", "文件", "代码", "函数", "类", "模块",
            "file", "code", "function", "class", "module",
            "重构", "优化", "修复", "实现", "创建",
            "refactor", "optimize", "fix", "implement", "create",
        ]
        code_count = sum(1 for kw in code_keywords if kw in message_lower)
        if code_count >= 2:
            return True
        
        return False
    
    def estimate_complexity(self, message: str) -> str:
        """
        估计任务复杂度
        
        Returns:
            "low", "medium", "high"
        """
        score = 0
        message_lower = message.lower()
        
        # 长度因素
        if len(message) > 300:
            score += 2
        elif len(message) > 150:
            score += 1
        
        # 关键词因素
        high_complexity_keywords = [
            "全部", "所有", "完整", "详细", "彻底",
            "重构", "重新设计", "从头", "整体",
            "all", "complete", "detailed", "thorough",
            "refactor", "redesign", "from scratch", "entire",
        ]
        score += sum(2 for kw in high_complexity_keywords if kw in message_lower)
        
        medium_complexity_keywords = [
            "分析", "比较", "总结", "优化", "改进",
            "analyze", "compare", "summarize", "optimize", "improve",
        ]
        score += sum(1 for kw in medium_complexity_keywords if kw in message_lower)
        
        # 多任务因素
        if "和" in message and "以及" in message:
            score += 1
        
        # 判断复杂度等级
        if score >= 5:
            return "high"
        elif score >= 2:
            return "medium"
        else:
            return "low"
