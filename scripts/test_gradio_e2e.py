#!/usr/bin/env python3
"""Test Gradio chat endpoint"""
from gradio_client import Client

print("Connecting to Gradio...")
client = Client("http://localhost:7861")

print("\n=== Test 1: Calculator ===")
_, result = client.predict("1+2+3+4+5", [], api_name="/respond")
if result:
    print("Response:", result[-1]["content"][:300])
else:
    print("No response")

print("\n=== Test 2: Time ===")
_, result = client.predict("now time?", [], api_name="/respond")
if result:
    print("Response:", result[-1]["content"][:300])
else:
    print("No response")

print("\nDone!")
