# -*- coding: utf-8 -*-
"""
深度意图识别器 - Intent Recognition

模仿 Cursor 的意图理解能力：
1. 表层意图：用户直接表达的需求
2. 隐含意图：需要推断的真实目的
3. 任务类型：分类用户请求
4. 能力需求：判断需要哪些能力来完成
5. 上下文关联：结合历史对话理解
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import json
import re


class TaskType(Enum):
    """任务类型枚举"""
    QUERY = "query"              # 信息查询
    ACTION = "action"            # 执行操作
    ANALYSIS = "analysis"        # 分析任务
    CREATION = "creation"        # 创建内容
    MODIFICATION = "modification" # 修改内容
    CONVERSATION = "conversation" # 普通对话
    COMPLEX = "complex"          # 复杂多步骤任务


class RequiredCapability(Enum):
    """所需能力枚举"""
    RAG = "rag"                  # 知识库检索
    TOOLS = "tools"              # 工具调用
    PLANNING = "planning"        # 任务规划
    MEMORY = "memory"            # 记忆检索
    SKILLS = "skills"            # 技能调用
    WEB = "web"                  # 网络访问
    CODE = "code"                # 代码执行


@dataclass
class Intent:
    """
    意图数据结构
    
    包含对用户请求的全面理解
    """
    # 基本信息
    surface_intent: str              # 表层意图
    deep_intent: str                 # 深层意图
    task_type: TaskType              # 任务类型
    
    # 能力需求
    required_capabilities: List[RequiredCapability] = field(default_factory=list)
    suggested_tools: List[str] = field(default_factory=list)
    
    # 任务特征
    complexity: str = "low"          # low/medium/high
    is_multi_step: bool = False      # 是否需要多步骤
    estimated_steps: int = 1         # 预估步骤数
    
    # 上下文关联
    references_history: bool = False # 是否引用了历史对话
    context_keywords: List[str] = field(default_factory=list)
    
    # 输出期望
    expected_output_format: str = "text"  # text/code/table/list/json
    response_style: str = "detailed"      # concise/detailed/technical
    
    # 置信度
    confidence: float = 0.8
    
    # 额外信息
    entities: Dict[str, Any] = field(default_factory=dict)  # 提取的实体
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "surface_intent": self.surface_intent,
            "deep_intent": self.deep_intent,
            "task_type": self.task_type.value,
            "required_capabilities": [c.value for c in self.required_capabilities],
            "suggested_tools": self.suggested_tools,
            "complexity": self.complexity,
            "is_multi_step": self.is_multi_step,
            "estimated_steps": self.estimated_steps,
            "references_history": self.references_history,
            "context_keywords": self.context_keywords,
            "expected_output_format": self.expected_output_format,
            "response_style": self.response_style,
            "confidence": self.confidence,
            "entities": self.entities,
            "metadata": self.metadata,
        }


class IntentRecognizer:
    """
    深度意图识别器
    
    使用 LLM 进行语义分析，而非简单关键词匹配。
    类似 Cursor 的意图理解能力。
    """
    
    # 工具能力映射
    TOOL_CAPABILITIES = {
        "shell_execute": ["执行命令", "运行", "shell", "bash", "terminal"],
        "file_read_enhanced": ["读取文件", "查看", "打开", "文件内容"],
        "file_write": ["写入文件", "保存", "创建文件", "写文件"],
        "web_fetch": ["获取网页", "url", "网址", "链接"],
        "search_knowledge_base": ["搜索", "查找", "知识库", "文档"],
        "run_python_code": ["计算", "python", "代码", "执行代码"],
        "list_directory": ["列出目录", "文件列表", "ls", "目录"],
        "process_list": ["进程", "运行中", "ps"],
    }
    
    def __init__(self, llm_client=None):
        """
        初始化意图识别器
        
        Args:
            llm_client: LLM 客户端（可选，用于深度分析）
        """
        self.llm = llm_client
        self._intent_cache: Dict[str, Intent] = {}
        logger.info("IntentRecognizer initialized")
    
    async def recognize(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        available_tools: Optional[List[str]] = None,
    ) -> Intent:
        """
        识别用户意图
        
        Args:
            message: 用户消息
            history: 对话历史
            available_tools: 可用工具列表
        
        Returns:
            Intent 对象
        """
        logger.info(f"Recognizing intent for: {message[:50]}...")
        
        # 1. 快速规则匹配（处理明确意图）
        quick_intent = self._quick_match(message)
        if quick_intent and quick_intent.confidence > 0.9:
            logger.debug(f"Quick match successful: {quick_intent.task_type}")
            return quick_intent
        
        # 2. LLM 深度分析
        if self.llm:
            try:
                deep_intent = await self._llm_analyze(message, history, available_tools)
                if deep_intent:
                    return deep_intent
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")
        
        # 3. 降级：增强规则匹配
        return self._enhanced_rule_match(message, history)
    
    def _quick_match(self, message: str) -> Optional[Intent]:
        """
        快速规则匹配
        
        处理明确、简单的意图
        """
        message_lower = message.lower().strip()
        
        # 简单问候
        greetings = ["hi", "hello", "你好", "嗨", "hey", "早上好", "晚上好"]
        if message_lower in greetings or len(message_lower) < 5:
            return Intent(
                surface_intent="问候",
                deep_intent="用户想开始对话",
                task_type=TaskType.CONVERSATION,
                required_capabilities=[],
                complexity="low",
                confidence=0.95,
            )
        
        # 简单感谢
        thanks = ["谢谢", "thanks", "thank you", "感谢", "thx"]
        if any(t in message_lower for t in thanks) and len(message) < 20:
            return Intent(
                surface_intent="感谢",
                deep_intent="用户表达感谢",
                task_type=TaskType.CONVERSATION,
                required_capabilities=[],
                complexity="low",
                confidence=0.95,
            )
        
        # 明确的时间查询
        time_queries = ["几点", "什么时间", "current time", "时间是", "现在时间"]
        if any(q in message_lower for q in time_queries):
            return Intent(
                surface_intent="查询时间",
                deep_intent="用户想知道当前时间",
                task_type=TaskType.QUERY,
                required_capabilities=[RequiredCapability.TOOLS],
                suggested_tools=["get_current_time"],
                complexity="low",
                confidence=0.95,
            )
        
        # Shell 命令执行 - 检测执行命令的意图
        shell_keywords = ["执行命令", "运行命令", "execute", "run command", "shell", "终端", "terminal"]
        has_command = bool(re.search(r'[`\'\"](.*?)[`\'\"]', message))  # 检测引号包裹的命令
        if any(kw in message_lower for kw in shell_keywords) or (has_command and "命令" in message):
            return Intent(
                surface_intent="执行Shell命令",
                deep_intent="用户想要执行系统命令",
                task_type=TaskType.ACTION,
                required_capabilities=[RequiredCapability.TOOLS],
                suggested_tools=["shell_execute"],
                complexity="medium",
                confidence=0.95,
            )
        
        # 文件/目录操作 - 检测路径或文件相关关键词
        path_match = re.search(r'([/\\][a-zA-Z0-9_\-\.\/\\]+)', message)
        has_path = bool(path_match)
        path_str = path_match.group(1) if path_match else ""
        
        # 判断是文件还是目录
        is_file_path = bool(re.search(r'\.\w+$', path_str))  # 有扩展名则是文件
        
        file_keywords = ["文件", "目录", "读取", "查看", "分析项目", "项目结构", 
                        "file", "directory", "folder", "read", "list", "analyze"]
        if has_path or any(kw in message_lower for kw in file_keywords):
            # 决定具体工具
            tools = []
            if is_file_path:
                # 是文件，使用 file_read
                tools.append("file_read_enhanced")
            elif has_path:
                # 是目录或路径不确定
                if any(kw in message_lower for kw in ["读取", "内容", "read", "查看文件", "代码"]):
                    tools.append("file_read_enhanced")
                tools.append("list_directory")
            else:
                tools.extend(["list_directory", "file_read_enhanced"])
            
            return Intent(
                surface_intent="文件/项目操作",
                deep_intent="用户想要查看或分析文件系统内容",
                task_type=TaskType.ANALYSIS,
                required_capabilities=[RequiredCapability.TOOLS],
                suggested_tools=tools,
                complexity="medium",
                is_multi_step=True,
                confidence=0.92,
            )
        
        # 系统/环境查询
        env_keywords = ["环境", "进程", "运行中", "系统", "environment", "process", "running"]
        if any(kw in message_lower for kw in env_keywords):
            return Intent(
                surface_intent="系统信息查询",
                deep_intent="用户想了解系统或环境信息",
                task_type=TaskType.QUERY,
                required_capabilities=[RequiredCapability.TOOLS],
                suggested_tools=["env_info", "process_list"],
                complexity="low",
                confidence=0.92,
            )
        
        return None
    
    def _enhanced_rule_match(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Intent:
        """
        增强规则匹配
        
        当 LLM 不可用时的降级方案
        """
        message_lower = message.lower()
        
        # 分析任务类型
        task_type = self._detect_task_type(message_lower)
        
        # 分析复杂度
        complexity = self._estimate_complexity(message)
        
        # 分析所需能力
        capabilities = self._detect_capabilities(message_lower)
        
        # 推荐工具
        suggested_tools = self._suggest_tools(message_lower)
        
        # 检测多步骤
        is_multi_step = self._detect_multi_step(message_lower)
        
        # 检测历史引用
        references_history = self._detect_history_reference(message_lower, history)
        
        # 检测输出格式
        output_format = self._detect_output_format(message_lower)
        
        # 提取实体
        entities = self._extract_entities(message)
        
        return Intent(
            surface_intent=self._summarize_intent(message),
            deep_intent=self._infer_deep_intent(message, task_type),
            task_type=task_type,
            required_capabilities=capabilities,
            suggested_tools=suggested_tools,
            complexity=complexity,
            is_multi_step=is_multi_step,
            estimated_steps=self._estimate_steps(message, complexity),
            references_history=references_history,
            expected_output_format=output_format,
            entities=entities,
            confidence=0.7,
        )
    
    async def _llm_analyze(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]],
        available_tools: Optional[List[str]],
    ) -> Optional[Intent]:
        """
        使用 LLM 进行深度意图分析
        """
        # 构建分析提示
        history_text = ""
        if history:
            recent = history[-3:]  # 最近3轮
            history_text = "\n".join([
                f"{h['role']}: {h['content'][:100]}" for h in recent
            ])
        
        tools_text = ", ".join(available_tools) if available_tools else "shell_execute, file_read, file_write, search_knowledge_base, run_python_code"
        
        prompt = f"""分析用户意图，返回 JSON 格式：

用户消息: {message}

对话历史:
{history_text if history_text else "（无历史）"}

可用工具: {tools_text}

请分析并返回以下 JSON（不要其他内容）:
```json
{{
  "surface_intent": "用户直接表达的需求",
  "deep_intent": "用户真正想要达成的目标",
  "task_type": "query/action/analysis/creation/modification/conversation/complex",
  "required_capabilities": ["rag", "tools", "planning", "memory", "skills", "web", "code"],
  "suggested_tools": ["工具名1", "工具名2"],
  "complexity": "low/medium/high",
  "is_multi_step": true/false,
  "estimated_steps": 1-10,
  "references_history": true/false,
  "expected_output_format": "text/code/table/list/json",
  "response_style": "concise/detailed/technical",
  "entities": {{"file_paths": [], "urls": [], "numbers": [], "keywords": []}}
}}
```"""
        
        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 低温度，更确定性
            )
            
            # 解析 JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # 尝试直接解析
                data = json.loads(response)
            
            return Intent(
                surface_intent=data.get("surface_intent", ""),
                deep_intent=data.get("deep_intent", ""),
                task_type=TaskType(data.get("task_type", "conversation")),
                required_capabilities=[
                    RequiredCapability(c) for c in data.get("required_capabilities", [])
                    if c in [e.value for e in RequiredCapability]
                ],
                suggested_tools=data.get("suggested_tools", []),
                complexity=data.get("complexity", "medium"),
                is_multi_step=data.get("is_multi_step", False),
                estimated_steps=data.get("estimated_steps", 1),
                references_history=data.get("references_history", False),
                expected_output_format=data.get("expected_output_format", "text"),
                response_style=data.get("response_style", "detailed"),
                entities=data.get("entities", {}),
                confidence=0.85,
            )
            
        except Exception as e:
            logger.error(f"LLM intent analysis failed: {e}")
            return None
    
    def _detect_task_type(self, message: str) -> TaskType:
        """检测任务类型"""
        # 查询类
        query_keywords = ["是什么", "什么是", "how", "what", "why", "when", "where", "who",
                         "怎么", "如何", "为什么", "哪里", "谁", "多少", "?", "？"]
        if any(kw in message for kw in query_keywords):
            return TaskType.QUERY
        
        # 执行操作类
        action_keywords = ["执行", "运行", "删除", "创建", "安装", "启动", "停止", "重启",
                          "execute", "run", "delete", "create", "install", "start", "stop"]
        if any(kw in message for kw in action_keywords):
            return TaskType.ACTION
        
        # 分析类
        analysis_keywords = ["分析", "比较", "评估", "检查", "诊断", "审查",
                            "analyze", "compare", "evaluate", "check", "diagnose", "review"]
        if any(kw in message for kw in analysis_keywords):
            return TaskType.ANALYSIS
        
        # 创建类
        creation_keywords = ["写", "生成", "创建", "编写", "设计", "制作",
                            "write", "generate", "create", "design", "make", "build"]
        if any(kw in message for kw in creation_keywords):
            return TaskType.CREATION
        
        # 修改类
        modification_keywords = ["修改", "更新", "改", "优化", "重构", "调整",
                                "modify", "update", "change", "optimize", "refactor", "adjust"]
        if any(kw in message for kw in modification_keywords):
            return TaskType.MODIFICATION
        
        # 复杂任务（多个关键词或长消息）
        keyword_count = sum(1 for kw in action_keywords + analysis_keywords + creation_keywords 
                           if kw in message)
        if keyword_count >= 2 or len(message) > 200:
            return TaskType.COMPLEX
        
        return TaskType.CONVERSATION
    
    def _estimate_complexity(self, message: str) -> str:
        """估计复杂度"""
        score = 0
        message_lower = message.lower()
        
        # 长度因素
        if len(message) > 300:
            score += 3
        elif len(message) > 150:
            score += 2
        elif len(message) > 50:
            score += 1
        
        # 高复杂度关键词
        high_keywords = ["全部", "所有", "完整", "详细", "彻底", "整体", "系统性",
                        "重构", "重新设计", "从头", "全面", "深入",
                        "all", "complete", "comprehensive", "thorough", "systematic"]
        score += sum(2 for kw in high_keywords if kw in message_lower)
        
        # 中复杂度关键词
        medium_keywords = ["分析", "比较", "总结", "优化", "改进", "集成",
                          "analyze", "compare", "summarize", "optimize", "integrate"]
        score += sum(1 for kw in medium_keywords if kw in message_lower)
        
        # 多步骤指示
        if any(kw in message_lower for kw in ["首先", "然后", "最后", "第一", "第二"]):
            score += 2
        
        if score >= 5:
            return "high"
        elif score >= 2:
            return "medium"
        return "low"
    
    def _detect_capabilities(self, message: str) -> List[RequiredCapability]:
        """检测所需能力"""
        capabilities = []
        
        # RAG 知识库
        rag_keywords = ["文档", "知识库", "搜索", "查找资料", "参考", "根据"]
        if any(kw in message for kw in rag_keywords):
            capabilities.append(RequiredCapability.RAG)
        
        # 工具调用
        tool_keywords = ["执行", "运行", "文件", "目录", "命令", "shell", "读取", "写入"]
        if any(kw in message for kw in tool_keywords):
            capabilities.append(RequiredCapability.TOOLS)
        
        # 任务规划
        planning_keywords = ["计划", "步骤", "规划", "设计", "策略", "方案"]
        if any(kw in message for kw in planning_keywords):
            capabilities.append(RequiredCapability.PLANNING)
        
        # 记忆检索
        memory_keywords = ["之前", "上次", "刚才", "我们讨论过", "你说的", "记得"]
        if any(kw in message for kw in memory_keywords):
            capabilities.append(RequiredCapability.MEMORY)
        
        # 技能调用
        skill_keywords = ["代码审查", "文档撰写", "数据分析", "调试"]
        if any(kw in message for kw in skill_keywords):
            capabilities.append(RequiredCapability.SKILLS)
        
        # 网络访问
        web_keywords = ["网页", "url", "http", "链接", "网站", "在线"]
        if any(kw in message for kw in web_keywords):
            capabilities.append(RequiredCapability.WEB)
        
        # 代码执行
        code_keywords = ["代码", "python", "计算", "脚本", "程序"]
        if any(kw in message for kw in code_keywords):
            capabilities.append(RequiredCapability.CODE)
        
        return capabilities
    
    def _suggest_tools(self, message: str) -> List[str]:
        """推荐工具"""
        suggestions = []
        
        for tool_name, keywords in self.TOOL_CAPABILITIES.items():
            if any(kw in message for kw in keywords):
                suggestions.append(tool_name)
        
        return suggestions[:5]  # 最多5个
    
    def _detect_multi_step(self, message: str) -> bool:
        """检测是否需要多步骤"""
        multi_step_keywords = [
            "首先", "然后", "接着", "最后", "第一步", "第二步",
            "first", "then", "next", "finally", "step",
            "1.", "2.", "1)", "2)",
            "和", "以及", "同时", "另外", "还要", "并且",
        ]
        
        count = sum(1 for kw in multi_step_keywords if kw in message)
        return count >= 2 or len(message) > 200
    
    def _detect_history_reference(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]],
    ) -> bool:
        """检测是否引用历史"""
        history_keywords = [
            "之前", "上次", "刚才", "你说的", "我们讨论",
            "previously", "earlier", "you said", "we discussed",
            "那个", "这个", "它", "继续",
        ]
        
        return any(kw in message for kw in history_keywords)
    
    def _detect_output_format(self, message: str) -> str:
        """检测期望输出格式"""
        if any(kw in message for kw in ["代码", "code", "脚本", "函数"]):
            return "code"
        if any(kw in message for kw in ["表格", "table", "对比", "列表"]):
            return "table"
        if any(kw in message for kw in ["json", "JSON"]):
            return "json"
        if any(kw in message for kw in ["列出", "list", "枚举"]):
            return "list"
        return "text"
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """提取实体"""
        entities = {
            "file_paths": [],
            "urls": [],
            "numbers": [],
            "keywords": [],
        }
        
        # 文件路径
        path_pattern = r'[/\\][\w\-./\\]+\.\w+'
        entities["file_paths"] = re.findall(path_pattern, message)
        
        # URL
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        entities["urls"] = re.findall(url_pattern, message)
        
        # 数字
        number_pattern = r'\b\d+(?:\.\d+)?\b'
        entities["numbers"] = re.findall(number_pattern, message)
        
        # @引用
        at_pattern = r'@[\w\-./\\]+'
        entities["at_references"] = re.findall(at_pattern, message)
        
        return entities
    
    def _summarize_intent(self, message: str) -> str:
        """生成意图摘要"""
        if len(message) <= 50:
            return message
        return message[:47] + "..."
    
    def _infer_deep_intent(self, message: str, task_type: TaskType) -> str:
        """推断深层意图"""
        intent_templates = {
            TaskType.QUERY: "用户想要获取关于「{topic}」的信息",
            TaskType.ACTION: "用户想要执行「{action}」操作",
            TaskType.ANALYSIS: "用户想要分析和理解「{subject}」",
            TaskType.CREATION: "用户想要创建「{content}」",
            TaskType.MODIFICATION: "用户想要修改或优化「{target}」",
            TaskType.COMPLEX: "用户想要完成一个复杂的多步骤任务",
            TaskType.CONVERSATION: "用户想要进行对话交流",
        }
        
        template = intent_templates.get(task_type, "用户有一个请求")
        
        # 简单提取主题词
        words = message[:50].split()
        topic = " ".join(words[:5]) if words else message[:20]
        
        return template.format(
            topic=topic, action=topic, subject=topic, 
            content=topic, target=topic
        )
    
    def _estimate_steps(self, message: str, complexity: str) -> int:
        """估计步骤数"""
        if complexity == "low":
            return 1
        elif complexity == "medium":
            return 2 + message.count("和") + message.count("并")
        else:
            return 3 + message.count("和") + message.count("并") + message.count("然后")


# 全局实例
_intent_recognizer: Optional[IntentRecognizer] = None


def get_intent_recognizer(llm_client=None) -> IntentRecognizer:
    """获取意图识别器实例"""
    global _intent_recognizer
    if _intent_recognizer is None:
        _intent_recognizer = IntentRecognizer(llm_client)
    return _intent_recognizer

