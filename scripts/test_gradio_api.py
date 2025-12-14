# -*- coding: utf-8 -*-
"""Test Gradio API - Quick Test"""
from gradio_client import Client
import sys

client = Client('http://shbjlnxade5:7861')
print("✅ Connected to Gradio server")

# Simple test
print("\n" + "="*50)
message = sys.argv[1] if len(sys.argv) > 1 else "1+1等于几"
print(f"Query: {message}")
print("="*50)
result = client.predict(message=message, api_name="/chat")
print(result)
print("Response:", result)
