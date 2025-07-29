#!/usr/bin/env python3
"""
Test script to verify the batch submission database locking fix.

This script tests:
1. Batch submission succeeds
2. Database remains accessible after batch submission
3. No database lock errors occur
4. Subsequent operations work correctly
"""

import requests
import json
import time
import sys
import os

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def test_health_check():
    """Test basic API health"""
    try:
        response = requests.get(f"{API_BASE}/health-simple")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_batch_submission():
    """Test the batch submission endpoint"""
    try:
        # Prepare test data for batch submission
        test_evaluations = [
            {"supplier_id": 1, "criterion_name": "Quality", "score": 8.5},
            {"supplier_id": 1, "criterion_name": "Delivery", "score": 7.0},
            {"supplier_id": 1, "criterion_name": "Price", "score": 9.0},
            {"supplier_id": 2, "criterion_name": "Quality", "score": 7.5},
            {"supplier_id": 2, "criterion_name": "Delivery", "score": 8.0},
            {"supplier_id": 2, "criterion_name": "Price", "score": 6.5},
        ]
        
        batch_request = {
            "participant_name": "Test Manager",
            "participant_email": "test@example.com",
            "evaluations": test_evaluations
        }
        
        print("📤 Submitting batch evaluation...")
        response = requests.post(
            f"{API_BASE}/supplier-evaluations/submit-batch",
            json=batch_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch submission successful: {result}")
            return True
        else:
            print(f"❌ Batch submission failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Batch submission error: {e}")
        return False

def test_database_accessibility_after_batch():
    """Test that database is still accessible after batch submission"""
    try:
        # Try multiple different database operations
        operations = [
            ("Get suppliers", f"{API_BASE}/suppliers/"),
            ("Get evaluations", f"{API_BASE}/supplier-evaluations/"),
            ("Get evaluation summary", f"{API_BASE}/supplier-evaluations/summary"),
            ("Health check", f"{API_BASE}/health")
        ]
        
        all_passed = True
        
        for name, url in operations:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code in [200, 404]:  # 404 is OK if no data exists
                    print(f"✅ {name}: Accessible")
                else:
                    print(f"❌ {name}: Failed ({response.status_code})")
                    if response.status_code == 503:
                        print(f"   Service unavailable error: {response.text}")
                    all_passed = False
            except requests.exceptions.Timeout:
                print(f"❌ {name}: Timeout (possible database lock)")
                all_passed = False
            except Exception as e:
                print(f"❌ {name}: Error - {e}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Database accessibility test error: {e}")
        return False

def test_concurrent_operations():
    """Test concurrent database operations to check for locking issues"""
    import threading
    import time
    
    results = {"success": 0, "failure": 0, "lock_errors": 0}
    
    def make_request(thread_id):
        try:
            response = requests.get(f"{API_BASE}/suppliers/", timeout=5)
            if response.status_code == 200:
                results["success"] += 1
            elif response.status_code == 503:
                results["lock_errors"] += 1
                print(f"🔒 Thread {thread_id}: Database lock error")
            else:
                results["failure"] += 1
        except requests.exceptions.Timeout:
            results["lock_errors"] += 1
            print(f"🔒 Thread {thread_id}: Request timeout (possible lock)")
        except Exception as e:
            results["failure"] += 1
            print(f"❌ Thread {thread_id}: Error - {e}")
    
    # Launch multiple concurrent requests
    threads = []
    for i in range(5):
        thread = threading.Thread(target=make_request, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"🔄 Concurrent test results: {results['success']} success, {results['failure']} failures, {results['lock_errors']} lock errors")
    
    return results["lock_errors"] == 0  # Pass if no lock errors

def main():
    """Run all tests"""
    print("🧪 Testing batch submission database locking fix\n")
    
    tests = [
        ("Initial health check", test_health_check),
        ("Batch submission", test_batch_submission),
        ("Database accessibility after batch", test_database_accessibility_after_batch),
        ("Concurrent operations", test_concurrent_operations),
        ("Final health check", test_health_check)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
        
        # Small delay between tests
        time.sleep(0.5)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Database locking issue appears to be fixed.")
        return 0
    else:
        print("⚠️  Some tests failed. Database locking issue may still exist.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)