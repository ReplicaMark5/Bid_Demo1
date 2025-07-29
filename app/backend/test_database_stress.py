#!/usr/bin/env python3
"""
Stress test for database connection handling and batch operations.

This script performs multiple batch submissions and database operations
to ensure the fix handles high-load scenarios without locking issues.
"""

import requests
import json
import time
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def make_batch_submission(thread_id, batch_size=6):
    """Make a batch submission with random data"""
    try:
        evaluations = []
        for i in range(batch_size):
            evaluations.append({
                "supplier_id": random.randint(1, 3),
                "criterion_name": random.choice(["Quality", "Delivery", "Price", "Service", "Reliability"]),
                "score": round(random.uniform(5.0, 9.5), 1)
            })
        
        batch_request = {
            "participant_name": f"Test Manager {thread_id}",
            "participant_email": f"test{thread_id}@example.com",
            "evaluations": evaluations
        }
        
        response = requests.post(
            f"{API_BASE}/supplier-evaluations/submit-batch",
            json=batch_request,
            timeout=15
        )
        
        if response.status_code == 200:
            return {"success": True, "thread_id": thread_id, "response": response.json()}
        else:
            return {"success": False, "thread_id": thread_id, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"success": False, "thread_id": thread_id, "error": str(e)}

def make_database_query(thread_id, endpoint):
    """Make a database query"""
    try:
        response = requests.get(f"{API_BASE}/{endpoint}", timeout=10)
        if response.status_code == 200:
            return {"success": True, "thread_id": thread_id, "endpoint": endpoint}
        else:
            return {"success": False, "thread_id": thread_id, "endpoint": endpoint, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "thread_id": thread_id, "endpoint": endpoint, "error": str(e)}

def stress_test_batch_submissions(num_threads=8, batches_per_thread=3):
    """Stress test batch submissions with concurrent threads"""
    print(f"🔥 Stress testing: {num_threads} threads, {batches_per_thread} batches each")
    
    results = {"success": 0, "failure": 0, "errors": []}
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit multiple batch requests concurrently
        futures = []
        for thread_id in range(num_threads):
            for batch_num in range(batches_per_thread):
                future = executor.submit(make_batch_submission, f"{thread_id}-{batch_num}")
                futures.append(future)
        
        # Collect results
        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                results["success"] += 1
                print(f"✅ Thread {result['thread_id']}: Batch submitted successfully")
            else:
                results["failure"] += 1
                results["errors"].append(result["error"])
                print(f"❌ Thread {result['thread_id']}: {result['error']}")
    
    return results

def stress_test_mixed_operations(num_threads=10, operations_per_thread=5):
    """Stress test mixed database operations"""
    print(f"🔄 Mixed operations test: {num_threads} threads, {operations_per_thread} ops each")
    
    endpoints = ["suppliers/", "supplier-evaluations/", "supplier-evaluations/summary", "health"]
    results = {"success": 0, "failure": 0, "errors": []}
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for thread_id in range(num_threads):
            for op_num in range(operations_per_thread):
                endpoint = random.choice(endpoints)
                future = executor.submit(make_database_query, f"{thread_id}-{op_num}", endpoint)
                futures.append(future)
        
        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                results["success"] += 1
                print(f"✅ Thread {result['thread_id']}: {result['endpoint']} query success")
            else:
                results["failure"] += 1
                results["errors"].append(result["error"])
                print(f"❌ Thread {result['thread_id']}: {result['endpoint']} - {result['error']}")
    
    return results

def test_rapid_sequential_batches(num_batches=10):
    """Test rapid sequential batch submissions"""
    print(f"⚡ Rapid sequential test: {num_batches} batches")
    
    results = {"success": 0, "failure": 0, "errors": []}
    
    for i in range(num_batches):
        result = make_batch_submission(f"sequential-{i}")
        if result["success"]:
            results["success"] += 1
            print(f"✅ Batch {i}: Success")
        else:
            results["failure"] += 1
            results["errors"].append(result["error"])
            print(f"❌ Batch {i}: {result['error']}")
        
        # Small delay between batches
        time.sleep(0.1)
    
    return results

def main():
    """Run stress tests"""
    print("💪 Database Connection Stress Test\n")
    
    # Check initial health
    try:
        response = requests.get(f"{API_BASE}/health-simple")
        if response.status_code != 200:
            print("❌ Server not healthy, aborting tests")
            return 1
        print("✅ Server is healthy, starting stress tests\n")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return 1
    
    tests = [
        ("Rapid sequential batches", lambda: test_rapid_sequential_batches(10)),
        ("Concurrent batch submissions", lambda: stress_test_batch_submissions(6, 2)),
        ("Mixed database operations", lambda: stress_test_mixed_operations(8, 4)),
        ("Heavy concurrent load", lambda: stress_test_batch_submissions(12, 3))
    ]
    
    all_passed = True
    total_operations = 0
    total_successes = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        start_time = time.time()
        
        try:
            results = test_func()
            duration = time.time() - start_time
            
            total_operations += results["success"] + results["failure"]
            total_successes += results["success"]
            
            success_rate = (results["success"] / (results["success"] + results["failure"])) * 100 if (results["success"] + results["failure"]) > 0 else 0
            
            print(f"📊 {test_name} Results:")
            print(f"   Success: {results['success']}, Failures: {results['failure']}")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Duration: {duration:.2f}s")
            
            if results["failure"] > 0:
                print(f"   Errors: {results['errors'][:3]}...")  # Show first 3 errors
                all_passed = False
            else:
                print("   ✅ All operations successful!")
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            all_passed = False
        
        # Brief pause between tests
        time.sleep(1)
    
    # Final database accessibility check
    print(f"\n🏁 Final accessibility check...")
    try:
        response = requests.get(f"{API_BASE}/supplier-evaluations/summary", timeout=10)
        if response.status_code == 200:
            print("✅ Database still accessible after stress test")
        else:
            print(f"❌ Database accessibility issue: HTTP {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"❌ Database accessibility error: {e}")
        all_passed = False
    
    print(f"\n📈 Overall Results:")
    print(f"Total Operations: {total_operations}")
    print(f"Total Successes: {total_successes}")
    print(f"Overall Success Rate: {(total_successes/total_operations)*100:.1f}%" if total_operations > 0 else "No operations")
    
    if all_passed and total_successes == total_operations:
        print("🎉 All stress tests passed! Database connection fix is robust.")
        return 0
    else:
        print("⚠️  Some tests failed or had errors. Database may still have issues under load.")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)