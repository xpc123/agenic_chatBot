import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

print("Importing settings...", flush=True)
try:
    from app.config import settings
    print("Settings imported.", flush=True)
except Exception as e:
    print(f"Error importing settings: {e}", flush=True)
