#!/usr/bin/env python3

import requests
import threading
import time
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, method="GET", data=None, thread_id=0):
    """Test a specific endpoint"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=10)
        
        print(f"Thread {thread_id}: {method} {endpoint} -> Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Thread {thread_id}: Error response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Thread {thread_id}: Exception on {method} {endpoint}: {e}")
        return False

def concurrent_test():
    """Test concurrent requests to various endpoints"""
    print("Testing concurrent requests...")
    
    # List of endpoints to test concurrently
    test_cases = [
        ("/api/suppliers/", "GET"),
        ("/api/depots/", "GET"),
        ("/api/bwm/weights/", "GET"),
        ("/api/supplier-evaluations/summary", "GET"),
        ("/api/health", "GET"),
    ]
    
    threads = []
    results = []
    
    def run_test(endpoint, method, thread_id):
        success = test_endpoint(endpoint, method, thread_id=thread_id)
        results.append(success)
    
    # Create multiple threads for each endpoint
    thread_id = 0
    for endpoint, method in test_cases:
        for i in range(3):  # 3 concurrent requests per endpoint
            thread = threading.Thread(target=run_test, args=(endpoint, method, thread_id))
            threads.append(thread)
            thread_id += 1
    
    # Start all threads
    start_time = time.time()
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    print(f"\nTest completed in {end_time - start_time:.2f} seconds")
    print(f"Success rate: {sum(results)}/{len(results)} ({100*sum(results)/len(results):.1f}%)")
    
    return all(results)

if __name__ == "__main__":
    print("Starting concurrent request test...")
    print("Make sure the FastAPI server is running on http://localhost:8000")
    print("You can start it with: uvicorn unified_api:app --reload\n")
    
    # Wait a bit for user to start server if needed
    input("Press Enter when the server is ready...")
    
    success = concurrent_test()
    if success:
        print("\n✅ All concurrent requests succeeded! Database locking issues appear to be resolved.")
    else:
        print("\n❌ Some requests failed. Check the output above for details.")