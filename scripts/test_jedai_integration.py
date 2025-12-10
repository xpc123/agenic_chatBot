
import os
import sys
import asyncio
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.config import settings
from app.llm.client import LLMClient, EmbeddingClient

async def test_jedai_config():
    print("Testing JedAI Configuration...")
    
    # Mock settings
    with patch("app.config.settings.JEDAI_API_BASE", "https://jedai.cadence.com/api/copilot/v1/llm"), \
         patch("app.config.settings.JEDAI_API_KEY", "test-key"), \
         patch("app.config.settings.JEDAI_MODEL", "gpt-4-jedai"), \
         patch("app.config.settings.JEDAI_VERIFY_SSL", False):
        
        # Test LLMClient initialization with JedAI
        print("Initializing LLMClient with provider='jedai'...")
        client = LLMClient(provider="jedai")
        
        assert client.provider == "jedai"
        assert client.model == "gpt-4-jedai"
        
        # Verify underlying ChatOpenAI configuration
        # We can't easily check private attributes, but we can check if it initialized without error
        print("LLMClient initialized successfully.")
        
        # Test EmbeddingClient initialization with JedAI
        print("Initializing EmbeddingClient with provider='jedai'...")
        embed_client = EmbeddingClient(provider="jedai")
        
        assert embed_client.provider == "jedai"
        print("EmbeddingClient initialized successfully.")

if __name__ == "__main__":
    asyncio.run(test_jedai_config())
