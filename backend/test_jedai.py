import asyncio
import os
from app.llm.client import LLMClient
from app.config import settings

async def test_jedai():
    print("Testing JedAI Integration...")
    
    # Configure to use JedAI
    # In a real scenario, these would be set via env vars or config file
    # For this test, we'll instantiate the client directly with provider="jedai"
    
    try:
        client = LLMClient(provider="jedai", model="gpt-4")
        print(f"Client initialized: {client.provider}/{client.model}")
        
        # Test chat completion
        messages = [
            {"role": "user", "content": "Hello, are you working?"}
        ]
        
        print("Sending request...")
        # We expect this to fail if we don't have a valid API key or network access
        # But we want to verify the code path works
        try:
            response = await client.chat_completion(messages)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Request failed (expected if no access): {e}")
            
    except Exception as e:
        print(f"Initialization failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_jedai())
