#!/usr/bin/env python3
"""
Standalone backend launcher for the Supply Chain Optimizer API
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def main():
    """Launch the FastAPI backend server"""
    print("🚀 Starting Supply Chain Optimizer Backend...")
    print("📍 Backend will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔧 Interactive API Explorer: http://localhost:8000/redoc")
    print("=" * 50)
    
    try:
        import uvicorn
        from backend_api import app
        
        # Configure and run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["."],
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Please install requirements: pip install -r requirements.txt")
        return 1
    
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())