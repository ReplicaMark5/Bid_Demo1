#!/usr/bin/env python3
"""
Run both backend APIs simultaneously for the supplier data submission system.
"""

import subprocess
import sys
import os
import time
import signal
import threading
from pathlib import Path

def run_backend(script_name, port, log_prefix):
    """Run a backend API script"""
    try:
        # Change to the backend directory
        backend_dir = Path(__file__).parent / "backend"
        os.chdir(backend_dir)
        
        # Start the backend process
        cmd = [sys.executable, script_name]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            print(f"[{log_prefix}] {line.strip()}")
        
        # Wait for process to complete
        process.wait()
        
    except Exception as e:
        print(f"Error running {script_name}: {e}")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down backends...")
    sys.exit(0)

def main():
    print("🚀 Starting Full Backend Services...")
    print("=" * 50)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create threads for both backends
    backend_main = threading.Thread(
        target=run_backend,
        args=("backend_api.py", 8000, "MAIN-API"),
        daemon=True
    )
    
    backend_supplier = threading.Thread(
        target=run_backend,
        args=("supplier_api.py", 8001, "SUPPLIER-API"),
        daemon=True
    )
    
    # Start both backends
    print("Starting Main Backend API on port 8000...")
    backend_main.start()
    
    time.sleep(2)  # Small delay to let the first API start
    
    print("Starting Supplier Backend API on port 8001...")
    backend_supplier.start()
    
    print("\n✅ Both backends started successfully!")
    print("📊 Main API: http://localhost:8000")
    print("👥 Supplier API: http://localhost:8001")
    print("🌐 Frontend: http://localhost:3000")
    print("\nPress Ctrl+C to stop all services...")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()