#!/usr/bin/env python3
"""
Standalone frontend launcher for the Supply Chain Optimizer React app
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the React frontend development server"""
    print("🚀 Starting Supply Chain Optimizer Frontend...")
    print("📍 Frontend will be available at: http://localhost:3000")
    print("🔧 Development server with hot reload enabled")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("package.json").exists():
        print("❌ package.json not found. Please run from the react directory.")
        return 1
    
    # Check if node_modules exists
    if not Path("node_modules").exists():
        print("❌ node_modules not found. Please run: npm install")
        return 1
    
    try:
        # Start the development server
        result = subprocess.run(
            ["npm", "run", "dev"],
            cwd=Path.cwd(),
            check=True
        )
        
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting frontend: {e}")
        return e.returncode
    
    except FileNotFoundError:
        print("❌ npm not found. Please install Node.js and npm.")
        return 1
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())