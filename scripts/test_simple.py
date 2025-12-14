# -*- coding: utf-8 -*-
"""Test Gradio - Direct sync call with output"""
from gradio_client import Client
import time

print("Connecting to Gradio...")
client = Client('http://shbjlnxade5:7861')
print("✅ Connected!\n")

# Test: Time query
print("=" * 60)
print("Query: 现在几点了？")
print("=" * 60)

start = time.time()
result = client.predict(message="现在几点了？", api_name="/chat")
elapsed = time.time() - start

print(f"\n⏱️  Response time: {elapsed:.1f}s")
print("-" * 60)
print("📝 Response:")
print("-" * 60)
print(result)
print("=" * 60)
