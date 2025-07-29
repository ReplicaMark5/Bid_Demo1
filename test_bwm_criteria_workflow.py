#!/usr/bin/env python3
"""
Test script for BWM weights clearing when criteria configuration is updated.
This comprehensive test validates the complete workflow for ensuring BWM weights 
consistency with current criteria configuration.
"""

import requests
import sqlite3
import json
import sys
import time
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
DB_PATH = "/tmp/supplier_data_fresh.db"

def test_database_connection():
    """Test basic database connectivity"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM suppliers")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"✓ Database connection successful. Found {count} suppliers.")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def get_bwm_weights_count() -> int:
    """Get current count of BWM weights in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bwm_weights")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_supplier_evaluations_count() -> int:
    """Get current count of supplier evaluations in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM supplier_evaluations")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_test_bwm_weights():
    """Add test BWM weights to database"""
    test_bwm_data = {
        "criteria_names": ["Quality", "Price", "Delivery", "Service", "Reliability"],
        "weights": {
            "Quality": 0.35,
            "Price": 0.25,
            "Delivery": 0.20,
            "Service": 0.12,
            "Reliability": 0.08
        },
        "best_criterion": "Quality",
        "worst_criterion": "Reliability",
        "best_to_others": {
            "Quality": 1.0,
            "Price": 2.0,
            "Delivery": 3.0,
            "Service": 4.0,
            "Reliability": 5.0
        },
        "others_to_worst": {
            "Quality": 5.0,
            "Price": 4.0,
            "Delivery": 3.0,
            "Service": 2.0,
            "Reliability": 1.0
        },
        "consistency_ratio": 0.15,
        "consistency_interpretation": "Good consistency",
        "created_by": "test_workflow"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/bwm/save/",
            json=test_bwm_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Test BWM weights added successfully (ID: {result.get('id')})")
            return True
        else:
            print(f"✗ Failed to add test BWM weights: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error adding test BWM weights: {e}")
        return False

def add_test_supplier_evaluations():
    """Add test supplier evaluations to database"""
    # First, let's get some suppliers to evaluate
    try:
        response = requests.get(f"{API_BASE_URL}/api/suppliers/")
        if response.status_code != 200:
            print(f"✗ Failed to get suppliers: {response.status_code}")
            return False
        
        suppliers = response.json().get("suppliers", [])
        if not suppliers:
            print("✗ No suppliers found for testing")
            return False
        
        # Add some test evaluations
        test_evaluations = []
        criteria = ["Quality", "Price", "Delivery", "Service", "Reliability"]
        
        for i, supplier in enumerate(suppliers[:3]):  # Test with first 3 suppliers
            for j, criterion in enumerate(criteria):
                test_evaluations.append({
                    "supplier_id": supplier["id"],
                    "criterion_name": criterion,
                    "score": 5.0 + (i + j) % 4  # Vary scores between 5-8
                })
        
        # Submit batch evaluation
        batch_request = {
            "participant_name": "Test Manager",
            "participant_email": "test@example.com",
            "evaluations": test_evaluations
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/supplier-evaluations/submit-batch",
            json=batch_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Test supplier evaluations added successfully (Count: {result.get('count')})")
            return True
        else:
            print(f"✗ Failed to add test supplier evaluations: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error adding test supplier evaluations: {e}")
        return False

def test_api_health():
    """Test API health and connectivity"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health-simple", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✓ API is healthy: {health_data.get('message')}")
            return True
        else:
            print(f"✗ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API health check failed: {e}")
        return False

def test_bwm_weights_endpoint():
    """Test BWM weights endpoint response"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/bwm/weights/")
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"✗ BWM weights endpoint failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ BWM weights endpoint error: {e}")
        return None

def test_criteria_update_endpoint():
    """Test the criteria update endpoint"""
    test_payload = {
        "old_criteria_names": ["Quality", "Price", "Delivery", "Service", "Reliability"],
        "new_criteria_names": ["New Quality", "New Price", "New Speed", "New Support", "New Trust"],
        "default_score": 5.0
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/criteria/update",
            json=test_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Criteria update successful")
            print(f"  - Message: {result.get('message')}")
            print(f"  - Cleared evaluations: {result.get('cleared_evaluations')}")
            print(f"  - Cleared BWM weights: {result.get('cleared_bwm_weights')}")
            return result
        else:
            print(f"✗ Criteria update failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"✗ Criteria update error: {e}")
        return None

def main():
    """Run complete BWM weights clearing workflow test"""
    print("🧪 BWM Weights Clearing Workflow Test")
    print("=" * 50)
    
    # Step 1: Test prerequisites
    print("\n📋 Step 1: Testing Prerequisites")
    if not test_database_connection():
        sys.exit(1)
    
    if not test_api_health():
        sys.exit(1)
    
    # Step 2: Setup test data
    print("\n🔧 Step 2: Setting up Test Data")
    
    # Get initial counts
    initial_bwm_count = get_bwm_weights_count()
    initial_eval_count = get_supplier_evaluations_count()
    print(f"Initial BWM weights count: {initial_bwm_count}")
    print(f"Initial supplier evaluations count: {initial_eval_count}")
    
    # Add test BWM weights if none exist
    if initial_bwm_count == 0:
        if not add_test_bwm_weights():
            sys.exit(1)
    
    # Add test evaluations if none exist
    if initial_eval_count == 0:
        if not add_test_supplier_evaluations():
            print("⚠️  Warning: Could not add test evaluations (this is okay for the main test)")
    
    # Get setup counts
    setup_bwm_count = get_bwm_weights_count()
    setup_eval_count = get_supplier_evaluations_count()
    print(f"Setup BWM weights count: {setup_bwm_count}")
    print(f"Setup supplier evaluations count: {setup_eval_count}")
    
    # Step 3: Test BWM weights endpoint before update
    print("\n🔍 Step 3: Testing BWM Weights Endpoint (Before Update)")
    bwm_before = test_bwm_weights_endpoint()
    if bwm_before and bwm_before.get('data'):
        print(f"✓ BWM weights found before update:")
        print(f"  - Criteria: {bwm_before['data'].get('criteria_names')}")
        print(f"  - Best criterion: {bwm_before['data'].get('best_criterion')}")
        print(f"  - Worst criterion: {bwm_before['data'].get('worst_criterion')}")
    else:
        print("⚠️  No BWM weights found before update")
    
    # Step 4: Test criteria update endpoint
    print("\n🔄 Step 4: Testing Criteria Update Endpoint")
    update_result = test_criteria_update_endpoint()
    if not update_result:
        sys.exit(1)
    
    # Step 5: Verify database state after update
    print("\n✅ Step 5: Verifying Database State After Update")
    post_bwm_count = get_bwm_weights_count()
    post_eval_count = get_supplier_evaluations_count()
    
    print(f"Post-update BWM weights count: {post_bwm_count}")
    print(f"Post-update supplier evaluations count: {post_eval_count}")
    
    # Verify BWM weights were cleared
    if post_bwm_count == 0:
        print("✓ BWM weights successfully cleared")
    else:
        print(f"✗ BWM weights not cleared! Still {post_bwm_count} records")
    
    # Step 6: Test BWM weights endpoint after update
    print("\n🔍 Step 6: Testing BWM Weights Endpoint (After Update)")
    bwm_after = test_bwm_weights_endpoint()
    if bwm_after:
        if bwm_after.get('data') is None:
            print("✓ BWM weights endpoint returns null data - PROMETHEE II protection working")
            print(f"  - Message: {bwm_after.get('message')}")
        else:
            print("✗ BWM weights endpoint still returns data after clearing!")
    else:
        print("✗ BWM weights endpoint failed after update")
    
    # Step 7: Test PROMETHEE II protection scenario
    print("\n🛡️  Step 7: Testing PROMETHEE II Protection Scenario")
    print("When no BWM weights exist:")
    print("  - BWM weights endpoint returns: null data")
    print("  - PROMETHEE II components should show: 'BWM weights required'")
    print("  - User workflow: Must recalculate BWM before running PROMETHEE II")
    
    # Step 8: Summary
    print("\n📊 Step 8: Workflow Test Summary")
    print("=" * 30)
    
    success_criteria = [
        ("Database connectivity", True),
        ("API health check", True),
        ("BWM weights cleared", post_bwm_count == 0),
        ("API response includes both counts", 
         update_result and 'cleared_evaluations' in update_result and 'cleared_bwm_weights' in update_result),
        ("BWM endpoint returns null after clear", bwm_after and bwm_after.get('data') is None),
        ("PROMETHEE II protection active", bwm_after and 'No BWM weights found' in bwm_after.get('message', ''))
    ]
    
    all_passed = True
    for criterion, passed in success_criteria:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {criterion}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED - BWM weights clearing workflow is working correctly!")
        print("\nWorkflow Summary:")
        print("1. ✅ Initial BWM weights detected in database")
        print("2. ✅ Criteria update API clears BWM weights table")
        print("3. ✅ BWM weights count reduced to 0")
        print("4. ✅ BWM endpoint returns null data")
        print("5. ✅ PROMETHEE II protection active - requires BWM recalculation")
    else:
        print("❌ SOME TESTS FAILED - Please review the issues above")
        sys.exit(1)

if __name__ == "__main__":
    main()