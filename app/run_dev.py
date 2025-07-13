#!/usr/bin/env python3
"""
Development launcher for the Supply Chain Optimizer
Starts both backend and frontend servers concurrently
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(message, color):
    print(f"{color}{message}{Colors.ENDC}")

def check_dependencies():
    """Check if required dependencies are installed"""
    print_colored("🔍 Checking dependencies...", Colors.OKBLUE)
    
    # Check Python dependencies
    try:
        import fastapi
        import uvicorn
        import pandas
        import numpy
        print_colored("✅ Python dependencies found", Colors.OKGREEN)
    except ImportError as e:
        print_colored(f"❌ Missing Python dependency: {e}", Colors.FAIL)
        print_colored("Run: pip install -r backend/requirements.txt", Colors.WARNING)
        return False
    
    # Check Node.js dependencies
    react_dir = Path("react")
    if not (react_dir / "node_modules").exists():
        print_colored("❌ Node.js dependencies not found", Colors.FAIL)
        print_colored("Run: cd react && npm install", Colors.WARNING)
        return False
    
    print_colored("✅ Node.js dependencies found", Colors.OKGREEN)
    return True

def start_backend():
    """Start the FastAPI backend server"""
    print_colored("🚀 Starting backend server...", Colors.OKBLUE)
    
    backend_dir = Path("backend")
    env = os.environ.copy()
    
    # Ensure we use the virtual environment's Python path
    if 'VIRTUAL_ENV' in env:
        venv_path = env['VIRTUAL_ENV']
        env['PATH'] = f"{venv_path}/bin:{env.get('PATH', '')}"
        print_colored(f"Using VIRTUAL_ENV: {venv_path}", Colors.OKGREEN)
    
    # Use current Python (should have venv activated since you're in venv)
    python_executable = sys.executable
    print_colored(f"Using current Python: {python_executable}", Colors.OKGREEN)
    
    # Start backend with uvicorn
    cmd = [
        python_executable, "-m", "uvicorn", 
        "backend_api:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    
    return subprocess.Popen(
        cmd, 
        cwd=backend_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

def start_frontend():
    """Start the React frontend server"""
    print_colored("🚀 Starting frontend server...", Colors.OKBLUE)
    
    react_dir = Path("react")
    
    # Start frontend with Vite
    cmd = ["npm", "run", "dev"]
    
    return subprocess.Popen(
        cmd,
        cwd=react_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

def monitor_process(process, name, color):
    """Monitor a process and print its output"""
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print_colored(f"[{name}] {output.strip()}", color)

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print_colored("\n🛑 Shutting down servers...", Colors.WARNING)
    sys.exit(0)

def main():
    """Main function to orchestrate the development environment"""
    print_colored("=" * 60, Colors.HEADER)
    print_colored("🏭 SUPPLY CHAIN OPTIMIZER - DEVELOPMENT MODE", Colors.HEADER)
    print_colored("=" * 60, Colors.HEADER)
    
    # Check if we're in the right directory
    if not Path("backend").exists() or not Path("react").exists():
        print_colored("❌ Please run this script from the app directory", Colors.FAIL)
        print_colored("Expected structure: app/backend/ and app/react/", Colors.WARNING)
        return 1
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    processes = []
    
    try:
        # Start backend
        backend_process = start_backend()
        processes.append(("backend", backend_process))
        
        # Wait a bit for backend to start
        time.sleep(2)
        
        # Start frontend
        frontend_process = start_frontend()
        processes.append(("frontend", frontend_process))
        
        # Wait a bit for frontend to start
        time.sleep(3)
        
        # Print startup information
        print_colored("\n" + "=" * 60, Colors.OKGREEN)
        print_colored("🎉 SERVERS STARTED SUCCESSFULLY!", Colors.OKGREEN)
        print_colored("=" * 60, Colors.OKGREEN)
        print_colored("🖥️  Frontend: http://localhost:3000", Colors.OKCYAN)
        print_colored("🔧 Backend:  http://localhost:8000", Colors.OKCYAN)
        print_colored("📚 API Docs: http://localhost:8000/docs", Colors.OKCYAN)
        print_colored("=" * 60, Colors.OKGREEN)
        print_colored("Press Ctrl+C to stop all servers", Colors.WARNING)
        print_colored("=" * 60, Colors.OKGREEN)
        
        # Monitor processes
        import threading
        
        def monitor_backend():
            monitor_process(backend_process, "BACKEND", Colors.OKBLUE)
        
        def monitor_frontend():
            monitor_process(frontend_process, "FRONTEND", Colors.OKCYAN)
        
        backend_thread = threading.Thread(target=monitor_backend)
        frontend_thread = threading.Thread(target=monitor_frontend)
        
        backend_thread.daemon = True
        frontend_thread.daemon = True
        
        backend_thread.start()
        frontend_thread.start()
        
        # Wait for processes to complete
        while True:
            time.sleep(1)
            
            # Check if any process has died
            for name, process in processes:
                if process.poll() is not None:
                    print_colored(f"❌ {name} process has stopped", Colors.FAIL)
                    return 1
    
    except KeyboardInterrupt:
        print_colored("\n🛑 Received shutdown signal", Colors.WARNING)
    
    except Exception as e:
        print_colored(f"❌ Error: {e}", Colors.FAIL)
        return 1
    
    finally:
        # Clean up processes
        print_colored("🧹 Cleaning up processes...", Colors.WARNING)
        for name, process in processes:
            if process.poll() is None:
                print_colored(f"🛑 Terminating {name}...", Colors.WARNING)
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print_colored(f"🔨 Force killing {name}...", Colors.WARNING)
                    process.kill()
        
        print_colored("✅ All processes stopped", Colors.OKGREEN)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())