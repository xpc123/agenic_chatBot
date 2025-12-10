import sys
import os
from pathlib import Path

print("Starting verification script...", flush=True)

# Add backend to sys.path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

try:
    print("Importing settings...", flush=True)
    from app.config import settings
    print("Importing client...", flush=True)
    from app.llm.client import get_llm_client, get_embedding_client, reset_clients
    print("Importing embeddings...", flush=True)
    from app.rag.embeddings import EmbeddingGenerator
    print("Imports successful.", flush=True)
except Exception as e:
    print(f"Import failed: {e}", flush=True)
    sys.exit(1)

def test_openai_provider():
    print("\nTesting OpenAI Provider Configuration...", flush=True)
    reset_clients()
    settings.LLM_PROVIDER = "openai"
    settings.EMBEDDING_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    
    llm_client = get_llm_client()
    print(f"LLM Provider: {llm_client.provider}", flush=True)
    print(f"LLM Model: {llm_client.model}", flush=True)
    
    emb_client = get_embedding_client()
    print(f"Embedding Provider: {emb_client.provider}", flush=True)
    print(f"Embedding Model: {emb_client.model}", flush=True)
    
    assert llm_client.provider == "openai"
    assert emb_client.provider == "openai"

def test_jedai_provider():
    print("\nTesting JedAI Provider Configuration...", flush=True)
    reset_clients()
    settings.LLM_PROVIDER = "jedai"
    settings.EMBEDDING_PROVIDER = "jedai"
    settings.JEDAI_API_KEY = "jedai-test-key"
    settings.JEDAI_MODEL = "jedai-gpt-4"
    
    llm_client = get_llm_client()
    print(f"LLM Provider: {llm_client.provider}", flush=True)
    print(f"LLM Model: {llm_client.model}", flush=True)
    
    emb_client = get_embedding_client()
    print(f"Embedding Provider: {emb_client.provider}", flush=True)
    print(f"Embedding Model: {emb_client.model}", flush=True)
    
    assert llm_client.provider == "jedai"
    assert llm_client.model == "jedai-gpt-4"
    assert emb_client.provider == "jedai"

def test_embedding_generator():
    print("\nTesting EmbeddingGenerator...", flush=True)
    reset_clients()
    settings.EMBEDDING_PROVIDER = "openai" 
    
    gen = EmbeddingGenerator()
    print(f"Generator Client Provider: {gen.client.provider}", flush=True)
    assert gen.client.provider == "openai"

if __name__ == "__main__":
    try:
        test_openai_provider()
        test_jedai_provider()
        test_embedding_generator()
        print("\n✅ All provider verification tests passed!", flush=True)
    except Exception as e:
        print(f"\n❌ Test failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
