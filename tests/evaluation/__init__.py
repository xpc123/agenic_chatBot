# -*- coding: utf-8 -*-
"""
ChatBot 产品评估框架

覆盖：
1. 通用 ChatBot 能力 - 基础对话、上下文、推理、代码、语言、创意、安全、鲁棒性、性能
2. 本产品独有功能 - RAG、MCP、Skills、Tools、意图识别

运行:
    python -m tests.evaluation.chatbot_evaluator
"""
from .chatbot_evaluator import (
    ChatBotEvaluator,
    EvalCase,
    EvalResult,
    EvalCategory,
    EvalDimension,
    DimScore,
    LLMJudge,
    SemanticMatcher,
    EVAL_CASES,
)

__all__ = [
    "ChatBotEvaluator",
    "EvalCase",
    "EvalResult",
    "EvalCategory",
    "EvalDimension",
    "DimScore",
    "LLMJudge",
    "SemanticMatcher",
    "EVAL_CASES",
]
