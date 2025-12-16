# -*- coding: utf-8 -*-
"""Test Gradio - Direct sync call with output"""
from gradio_client import Client
import time

print("Connecting to Gradio...")
client = Client('http://shbjlnxade5:7861')
print("✅ Connected!\n")

# Test Python code execution
print("=" * 60)
print("Query: 用 Python 计算 1 到 10 的和")
print("=" * 60)

start = time.time()
_, result = client.predict(message="用 Python 计算 1 到 10 的和", history=[], api_name="/respond")
elapsed = time.time() - start

print(f"\n⏱️  Response time: {elapsed:.1f}s")
print("-" * 60)
print("📝 Response:")
print("-" * 60)
# 从 chatbot 格式提取最后一条消息
if result and len(result) > 0:
    last_msg = result[-1]
    if isinstance(last_msg, dict):
        content = last_msg.get('content', [])
        for item in content:
            if item.get('type') == 'text':
                print(item.get('text', ''))
    else:
        print(last_msg)
print("=" * 60)
