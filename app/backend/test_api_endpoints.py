#!/usr/bin/env python3
"""
Comprehensive API Endpoint Testing

This script tests the key API endpoints that were failing in the frontend error log
to ensure they work correctly with the fresh database and don't return 500 errors.

Tests focus on:
1. /api/promethee/threshold-recommendations (POST)
2. /api/supplier-evaluations/ (GET)
3. /api/profile-scoring-config/ (GET)
4. /api/promethee/calculate (POST)
5. /api/bwm/weights/ (GET)
6. /api/suppliers/ (GET)
7. /api/health (GET)

The goal is to verify endpoints return proper HTTP status codes (200, 400, 404)
instead of 500 errors and handle empty database state gracefully.
"""

import sys
import os
import json
import traceback
from typing import Dict, Any, List
import requests
import time
import subprocess
from contextlib import contextmanager
import threading
import uvicorn

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import FastAPI app
from unified_api import app

class APIEndpointTester:
    """
    Comprehensive API endpoint tester for the unified supply chain optimizer API
    """
    
    def __init__(self, base_url="http://localhost:8001"):
        """
        Initialize the tester
        
        Args:
            base_url: Base URL for HTTP testing
        """
        self.base_url = base_url
        self.test_results = []
        self.server_process = None
        
    def log_test_result(self, endpoint: str, method: str, status_code: int, 
                       success: bool, response_data: Any = None, error: str = None):
        """Log test result"""
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "success": success,
            "response_data": response_data,
            "error": error,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        # Print real-time results
        status_indicator = "✅" if success else "❌"
        print(f"{status_indicator} {method} {endpoint} -> {status_code}")
        if error:
            print(f"   Error: {error}")
            
    def start_test_server(self):
        """Start a test server in a separate thread"""
        def run_server():
            try:
                uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
            except Exception as e:
                print(f"Server error: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(3)
        
        # Test if server is running
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            print(f"✅ Test server started on {self.base_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to start test server: {e}")
            return False
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None):
        """Make HTTP request using requests"""
        try:
            url = f"{self.base_url}{endpoint}"
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, params=params, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, params=params, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            try:
                response_data = response.json() if response.content else None
            except:
                response_data = {"raw_content": response.text}
                
            return response.status_code, response_data
                
        except Exception as e:
            return 500, {"error": str(e), "traceback": traceback.format_exc()}
    
    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        print("\n=== Testing Health Endpoint ===")
        
        status_code, response_data = self.make_request("GET", "/api/health")
        
        success = status_code == 200 and response_data is not None
        error = None if success else f"Expected 200, got {status_code}"
        
        self.log_test_result("/api/health", "GET", status_code, success, response_data, error)
        
        if success:
            print(f"   Status: {response_data.get('status', 'unknown')}")
            print(f"   Database: {response_data.get('database', 'unknown')}")
            
    def test_suppliers_endpoint(self):
        """Test /api/suppliers/ GET endpoint"""
        print("\n=== Testing Suppliers Endpoint ===")
        
        status_code, response_data = self.make_request("GET", "/api/suppliers/")
        
        # Should return 200 even with empty database
        success = status_code == 200 and response_data is not None
        error = None if success else f"Expected 200, got {status_code}"
        
        self.log_test_result("/api/suppliers/", "GET", status_code, success, response_data, error)
        
        if success and "suppliers" in response_data:
            print(f"   Found {len(response_data['suppliers'])} suppliers")
            
    def test_bwm_weights_endpoint(self):
        """Test /api/bwm/weights/ GET endpoint"""
        print("\n=== Testing BWM Weights Endpoint ===")
        
        status_code, response_data = self.make_request("GET", "/api/bwm/weights/")
        
        # Should return 200, may have no data but shouldn't crash
        success = status_code == 200 and response_data is not None
        error = None if success else f"Expected 200, got {status_code}"
        
        self.log_test_result("/api/bwm/weights/", "GET", status_code, success, response_data, error)
        
        if success:
            has_data = response_data.get("data") is not None
            print(f"   BWM weights available: {has_data}")
            
    def test_supplier_evaluations_endpoint(self):
        """Test /api/supplier-evaluations/ GET endpoint"""
        print("\n=== Testing Supplier Evaluations Endpoint ===")
        
        status_code, response_data = self.make_request("GET", "/api/supplier-evaluations/")
        
        # Should return 200 even with no evaluations
        success = status_code == 200 and response_data is not None
        error = None if success else f"Expected 200, got {status_code}"
        
        self.log_test_result("/api/supplier-evaluations/", "GET", status_code, success, response_data, error)
        
        if success and "evaluations" in response_data:
            print(f"   Found {len(response_data['evaluations'])} evaluations")
            
    def test_profile_scoring_config_endpoint(self):
        """Test /api/profile-scoring-config/ GET endpoint"""
        print("\n=== Testing Profile Scoring Config Endpoint ===")
        
        status_code, response_data = self.make_request("GET", "/api/profile-scoring-config/")
        
        # Should return 200, may have empty config but shouldn't crash
        success = status_code == 200 and response_data is not None
        error = None if success else f"Expected 200, got {status_code}"
        
        self.log_test_result("/api/profile-scoring-config/", "GET", status_code, success, response_data, error)
        
        if success:
            has_config = bool(response_data.get("config"))
            print(f"   Profile scoring config available: {has_config}")
            
    def test_promethee_threshold_recommendations_endpoint(self):
        """Test /api/promethee/threshold-recommendations POST endpoint"""
        print("\n=== Testing PROMETHEE Threshold Recommendations Endpoint ===")
        
        # Test with minimal valid data
        test_data = {
            "criteria_names": ["Quality", "Price", "Delivery"],
            "criteria_weights": [0.4, 0.3, 0.3],
            "preference_functions": {
                "Quality": "linear",
                "Price": "linear", 
                "Delivery": "linear"
            },
            "preference_thresholds": {
                "Quality": 2.0,
                "Price": 2.0,
                "Delivery": 2.0
            },
            "indifference_thresholds": {
                "Quality": 0.5,
                "Price": 0.5,
                "Delivery": 0.5
            }
        }
        
        status_code, response_data = self.make_request("POST", "/api/promethee/threshold-recommendations", test_data)
        
        # Should handle gracefully - may return error for no data but shouldn't crash with 500
        success = status_code in [200, 400, 404] and response_data is not None
        error = None if success else f"Got unexpected {status_code} (expected 200/400/404)"
        
        self.log_test_result("/api/promethee/threshold-recommendations", "POST", status_code, success, response_data, error)
        
        if status_code == 200:
            print("   ✅ Successfully generated threshold recommendations")
        elif status_code in [400, 404]:
            print(f"   ⚠️  Expected error for empty database: {response_data.get('detail', 'No details')}")
        
    def test_promethee_calculate_endpoint(self):
        """Test /api/promethee/calculate POST endpoint"""
        print("\n=== Testing PROMETHEE Calculate Endpoint ===")
        
        # Test with minimal valid data
        test_data = {
            "criteria_names": ["Quality", "Price", "Delivery"],
            "criteria_weights": [0.4, 0.3, 0.3],
            "preference_functions": {
                "Quality": "linear",
                "Price": "linear", 
                "Delivery": "linear"
            },
            "preference_thresholds": {
                "Quality": 2.0,
                "Price": 2.0,
                "Delivery": 2.0
            },
            "indifference_thresholds": {
                "Quality": 0.5,
                "Price": 0.5,
                "Delivery": 0.5
            }
        }
        
        status_code, response_data = self.make_request("POST", "/api/promethee/calculate", test_data)
        
        # Should handle gracefully - may return error for no supplier data but shouldn't crash with 500
        success = status_code in [200, 400, 404] and response_data is not None
        error = None if success else f"Got unexpected {status_code} (expected 200/400/404)"
        
        self.log_test_result("/api/promethee/calculate", "POST", status_code, success, response_data, error)
        
        if status_code == 200:
            print("   ✅ Successfully calculated PROMETHEE ranking")
        elif status_code in [400, 404]:
            print(f"   ⚠️  Expected error for insufficient data: {response_data.get('detail', 'No details')}")
    
    def run_all_tests(self):
        """Run all endpoint tests"""
        print("🧪 Starting API Endpoint Tests")
        print("="*50)
        
        # Start test server
        if not self.start_test_server():
            print("❌ Cannot start test server. Aborting tests.")
            return False
        
        # Test all endpoints
        self.test_health_endpoint()
        self.test_suppliers_endpoint()
        self.test_bwm_weights_endpoint()
        self.test_supplier_evaluations_endpoint()
        self.test_profile_scoring_config_endpoint()
        self.test_promethee_threshold_recommendations_endpoint()
        self.test_promethee_calculate_endpoint()
        
        # Print summary
        self.print_test_summary()
        return True
        
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {successful_tests/total_tests*100:.1f}%")
        
        # Check for 500 errors (the main concern)
        server_errors = [r for r in self.test_results if r["status_code"] == 500]
        if server_errors:
            print(f"\n⚠️  CRITICAL: {len(server_errors)} endpoints returned 500 errors!")
            for error in server_errors:
                print(f"   - {error['method']} {error['endpoint']}")
        else:
            print("\n✅ No 500 (Internal Server) errors detected!")
            
        # Show failing tests
        if failed_tests > 0:
            print(f"\n❌ Failed Tests ({failed_tests}):")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['method']} {result['endpoint']} -> {result['status_code']}")
                    if result["error"]:
                        print(f"     Error: {result['error']}")
                        
        # Show successful tests
        print(f"\n✅ Successful Tests ({successful_tests}):")
        for result in self.test_results:
            if result["success"]:
                print(f"   - {result['method']} {result['endpoint']} -> {result['status_code']}")
                
        print("\n" + "="*50)
        
        # Key findings
        print("🔍 KEY FINDINGS:")
        db_error_found = any("name 'db' is not defined" in str(r.get("response_data", {})) for r in self.test_results)
        if db_error_found:
            print("   ❌ 'name 'db' is not defined' error still present")
        else:
            print("   ✅ 'name 'db' is not defined' error resolved")
            
        graceful_handling = all(r["status_code"] != 500 for r in self.test_results)
        if graceful_handling:
            print("   ✅ All endpoints handle empty database state gracefully")
        else:
            print("   ❌ Some endpoints still return 500 errors")
            
        print("="*50)


def main():
    """Main function to run tests"""
    print("🚀 API Endpoint Testing Tool")
    print("Testing key endpoints that were failing in frontend error log")
    print("Goal: Verify no 500 errors and graceful handling of empty database\n")
    
    # Create tester instance
    tester = APIEndpointTester()
    
    try:
        # Run all tests
        if not tester.run_all_tests():
            return 1
        
        # Return appropriate exit code
        server_errors = [r for r in tester.test_results if r["status_code"] == 500]
        if server_errors:
            print(f"\n💥 CRITICAL: Found {len(server_errors)} server errors!")
            return 1  # Exit with error code
        else:
            print("\n🎉 SUCCESS: All endpoints working without 500 errors!")
            return 0  # Exit successfully
            
    except Exception as e:
        print(f"\n💥 TESTING FAILED: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)