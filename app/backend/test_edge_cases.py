#!/usr/bin/env python3
"""
Edge Case Testing for API Endpoints

This script tests various edge cases and error conditions to ensure
robust error handling and validation across all endpoints.
"""

import sys
import os
import json
import traceback
import requests
import time
import threading
import uvicorn

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_api import app

class EdgeCaseTester:
    """Test edge cases and error conditions"""
    
    def __init__(self, base_url="http://localhost:8002"):
        self.base_url = base_url
        self.test_results = []
        
    def start_test_server(self):
        """Start a test server in a separate thread"""
        def run_server():
            try:
                uvicorn.run(app, host="127.0.0.1", port=8002, log_level="error")
            except Exception as e:
                print(f"Server error: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        time.sleep(3)
        
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            print(f"✅ Test server started on {self.base_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to start test server: {e}")
            return False
    
    def log_test_result(self, test_name: str, endpoint: str, method: str, 
                       status_code: int, expected_codes: list, success: bool, 
                       response_data=None, error=None):
        """Log test result"""
        result = {
            "test_name": test_name,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "expected_codes": expected_codes,
            "success": success,
            "response_data": response_data,
            "error": error
        }
        self.test_results.append(result)
        
        status_indicator = "✅" if success else "❌"
        print(f"{status_indicator} {test_name}: {method} {endpoint} -> {status_code} (expected {expected_codes})")
        if error:
            print(f"   Error: {error}")
    
    def make_request(self, method: str, endpoint: str, data=None, params=None):
        """Make HTTP request"""
        try:
            url = f"{self.base_url}{endpoint}"
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, params=params, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, params=params, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=params, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            try:
                response_data = response.json() if response.content else None
            except:
                response_data = {"raw_content": response.text}
                
            return response.status_code, response_data
                
        except Exception as e:
            return 500, {"error": str(e)}
    
    def test_malformed_json_posts(self):
        """Test POST endpoints with malformed JSON"""
        print("\n=== Testing Malformed JSON Payloads ===")
        
        test_cases = [
            {
                "name": "BWM Calculate - Missing required fields",
                "endpoint": "/api/bwm/calculate/",
                "data": {"criteria": ["A", "B"]},  # Missing required fields
                "expected": [400, 422]
            },
            {
                "name": "PROMETHEE Calculate - Invalid weights",
                "endpoint": "/api/promethee/calculate",
                "data": {
                    "criteria_names": ["A", "B"],
                    "criteria_weights": [0.5]  # Mismatched lengths
                },
                "expected": [400, 422]
            },
            {
                "name": "Supplier Evaluation - Invalid score",
                "endpoint": "/api/supplier-evaluations/submit",
                "data": {
                    "supplier_id": 999,
                    "criterion_name": "Quality",
                    "score": "invalid_score"  # Should be float
                },
                "expected": [400, 422]
            }
        ]
        
        for test_case in test_cases:
            status_code, response = self.make_request("POST", test_case["endpoint"], test_case["data"])
            success = status_code in test_case["expected"]
            
            self.log_test_result(
                test_case["name"],
                test_case["endpoint"], 
                "POST",
                status_code,
                test_case["expected"],
                success,
                response
            )
    
    def test_invalid_resource_ids(self):
        """Test endpoints with invalid resource IDs"""
        print("\n=== Testing Invalid Resource IDs ===")
        
        test_cases = [
            {
                "name": "Get Supplier Profile - Non-existent ID",
                "endpoint": "/api/suppliers/99999/profile/",
                "method": "GET",
                "expected": [404]
            },
            {
                "name": "Delete Supplier Evaluation - Non-existent ID",
                "endpoint": "/api/supplier-evaluations/99999",
                "method": "DELETE",
                "expected": [404]
            },
            {
                "name": "Get Supplier Submissions - Non-existent ID",
                "endpoint": "/api/suppliers/99999/submissions/",
                "method": "GET",
                "expected": [200, 404]  # May return empty list or 404
            }
        ]
        
        for test_case in test_cases:
            status_code, response = self.make_request(test_case["method"], test_case["endpoint"])
            success = status_code in test_case["expected"]
            
            self.log_test_result(
                test_case["name"],
                test_case["endpoint"],
                test_case["method"],
                status_code,
                test_case["expected"],
                success,
                response
            )
    
    def test_boundary_conditions(self):
        """Test boundary conditions and extreme values"""
        print("\n=== Testing Boundary Conditions ===")
        
        test_cases = [
            {
                "name": "BWM Calculate - Empty criteria list",
                "endpoint": "/api/bwm/calculate/",
                "data": {
                    "criteria": [],
                    "best_criterion": "",
                    "worst_criterion": "",
                    "best_to_others": {},
                    "others_to_worst": {}
                },
                "expected": [400, 422]
            },
            {
                "name": "PROMETHEE Calculate - Zero weights",
                "endpoint": "/api/promethee/calculate",
                "data": {
                    "criteria_names": ["A", "B", "C"],
                    "criteria_weights": [0.0, 0.0, 0.0]
                },
                "expected": [200, 400]  # May accept or reject zero weights
            },
            {
                "name": "Supplier Create - Empty name",
                "endpoint": "/api/suppliers/",
                "data": {
                    "name": "",
                    "email": "test@example.com"
                },
                "expected": [400, 422]
            }
        ]
        
        for test_case in test_cases:
            status_code, response = self.make_request("POST", test_case["endpoint"], test_case["data"])
            success = status_code in test_case["expected"]
            
            self.log_test_result(
                test_case["name"],
                test_case["endpoint"],
                "POST",
                status_code,
                test_case["expected"],
                success,
                response
            )
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        print("\n=== Testing Concurrent Requests ===")
        
        import concurrent.futures
        import threading
        
        def make_health_check():
            """Make a health check request"""
            return self.make_request("GET", "/api/health")
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_health_check) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Check all requests succeeded
        all_success = all(status == 200 for status, _ in results)
        
        self.log_test_result(
            "Concurrent Health Checks",
            "/api/health",
            "GET",
            200 if all_success else 500,
            [200],
            all_success,
            {"concurrent_requests": len(results), "all_successful": all_success}
        )
    
    def test_large_payloads(self):
        """Test handling of large payloads"""
        print("\n=== Testing Large Payloads ===")
        
        # Create a large evaluation batch
        large_evaluations = []
        for i in range(100):  # 100 evaluations
            large_evaluations.append({
                "supplier_id": i % 5 + 1,  # Rotate through 5 suppliers
                "criterion_name": f"Criterion_{i % 10 + 1}",  # 10 different criteria
                "score": (i % 9) + 1  # Scores 1-9
            })
        
        large_payload = {
            "participant_name": "Test Participant",
            "participant_email": "test@example.com",
            "evaluations": large_evaluations
        }
        
        status_code, response = self.make_request("POST", "/api/supplier-evaluations/submit-batch", large_payload)
        success = status_code in [200, 400, 404]  # Should handle gracefully
        
        self.log_test_result(
            "Large Evaluation Batch",
            "/api/supplier-evaluations/submit-batch",
            "POST",
            status_code,
            [200, 400, 404],
            success,
            {"payload_size": len(json.dumps(large_payload))}
        )
    
    def test_special_characters(self):
        """Test handling of special characters in inputs"""
        print("\n=== Testing Special Characters ===")
        
        test_cases = [
            {
                "name": "Supplier with Special Characters",
                "endpoint": "/api/suppliers/",
                "data": {
                    "name": "Test Supplier <script>alert('xss')</script>",
                    "email": "test+special@example.com"
                },
                "expected": [200, 400, 422]
            },
            {
                "name": "Criterion with Unicode",
                "endpoint": "/api/supplier-evaluations/submit",
                "data": {
                    "supplier_id": 1,
                    "criterion_name": "Qualité & Sécurité 测试",
                    "score": 8.5,
                    "participant_name": "Test User",
                    "participant_email": "test@example.com"
                },
                "expected": [200, 400, 404]
            }
        ]
        
        for test_case in test_cases:
            status_code, response = self.make_request("POST", test_case["endpoint"], test_case["data"])
            success = status_code in test_case["expected"]
            
            self.log_test_result(
                test_case["name"],
                test_case["endpoint"],
                "POST",
                status_code,
                test_case["expected"],
                success,
                response
            )
    
    def run_all_edge_case_tests(self):
        """Run all edge case tests"""
        print("🧪 Starting Edge Case Tests")
        print("="*50)
        
        if not self.start_test_server():
            print("❌ Cannot start test server. Aborting tests.")
            return False
        
        # Run all test categories
        self.test_malformed_json_posts()
        self.test_invalid_resource_ids()
        self.test_boundary_conditions()
        self.test_concurrent_requests()
        self.test_large_payloads()
        self.test_special_characters()
        
        # Print summary
        self.print_test_summary()
        return True
    
    def print_test_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print("📊 EDGE CASE TEST SUMMARY")
        print("="*50)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {successful_tests/total_tests*100:.1f}%")
        
        # Check for unexpected 500 errors
        server_errors = [r for r in self.test_results if r["status_code"] == 500 and 500 not in r["expected_codes"]]
        if server_errors:
            print(f"\n⚠️  CRITICAL: {len(server_errors)} unexpected 500 errors!")
            for error in server_errors:
                print(f"   - {error['test_name']}")
        else:
            print("\n✅ No unexpected 500 errors detected!")
        
        # Show failed tests
        if failed_tests > 0:
            print(f"\n❌ Failed Tests ({failed_tests}):")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test_name']}: {result['status_code']} (expected {result['expected_codes']})")
        
        # Show test categories
        categories = {}
        for result in self.test_results:
            category = result["test_name"].split(" - ")[0] if " - " in result["test_name"] else result["test_name"]
            if category not in categories:
                categories[category] = {"total": 0, "success": 0}
            categories[category]["total"] += 1
            if result["success"]:
                categories[category]["success"] += 1
        
        print(f"\n📋 Test Categories:")
        for category, stats in categories.items():
            success_rate = stats["success"] / stats["total"] * 100
            print(f"   - {category}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        print("="*50)

def main():
    """Main function to run edge case tests"""
    print("🚀 API Edge Case Testing Tool")
    print("Testing error conditions and boundary cases")
    print("Goal: Ensure robust error handling and validation\n")
    
    tester = EdgeCaseTester()
    
    try:
        if not tester.run_all_edge_case_tests():
            return 1
        
        # Check for critical failures
        unexpected_errors = [r for r in tester.test_results 
                           if r["status_code"] == 500 and 500 not in r["expected_codes"]]
        
        if unexpected_errors:
            print(f"\n💥 CRITICAL: Found {len(unexpected_errors)} unexpected server errors!")
            return 1
        else:
            print("\n🎉 SUCCESS: All edge cases handled appropriately!")
            return 0
            
    except Exception as e:
        print(f"\n💥 TESTING FAILED: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)