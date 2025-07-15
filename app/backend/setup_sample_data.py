#!/usr/bin/env python3
"""
Setup sample data for testing the supplier data submission system.
"""

from database import SupplierDatabase
import json

def setup_sample_data():
    """Setup sample suppliers, depots, and initial submissions for testing"""
    
    db = SupplierDatabase()
    
    print("Setting up sample data...")
    
    # Create sample suppliers
    suppliers = [
        {"name": "ABC Transport Ltd", "email": "abc@transport.com"},
        {"name": "XYZ Logistics", "email": "xyz@logistics.com"},
        {"name": "FastTrack Solutions", "email": "info@fasttrack.com"},
        {"name": "GreenFleet Services", "email": "green@fleet.com"},
        {"name": "ProLogistics Inc", "email": "pro@logistics.com"}
    ]
    
    supplier_ids = []
    for supplier in suppliers:
        try:
            supplier_id = db.add_supplier(supplier["name"], supplier["email"])
            supplier_ids.append(supplier_id)
            print(f"✓ Created supplier: {supplier['name']} (ID: {supplier_id})")
        except Exception as e:
            print(f"✗ Failed to create supplier {supplier['name']}: {e}")
    
    # Create sample depots
    depots = [
        {"name": "Cape Town Depot", "annual_volume": 850000},
        {"name": "Johannesburg Depot", "annual_volume": 1200000},
        {"name": "Durban Depot", "annual_volume": 750000},
        {"name": "Port Elizabeth Depot", "annual_volume": 450000},
        {"name": "Bloemfontein Depot", "annual_volume": 300000}
    ]
    
    depot_ids = []
    for depot in depots:
        try:
            depot_id = db.add_depot(depot["name"], depot["annual_volume"])
            depot_ids.append(depot_id)
            print(f"✓ Created depot: {depot['name']} (ID: {depot_id})")
        except Exception as e:
            print(f"✗ Failed to create depot {depot['name']}: {e}")
    
    # Create sample submissions (some approved, some pending)
    sample_submissions = [
        # ABC Transport Ltd submissions
        {
            "supplier_id": supplier_ids[0] if supplier_ids else 1,
            "depot_id": depot_ids[0] if depot_ids else 1,
            "data": {
                "coc_rebate": 2.5,
                "cost_of_collection": 1.2,
                "del_rebate": 3.0,
                "zone_differential": 0.5,
                "distance_km": 25.3
            },
            "status": "approved"
        },
        {
            "supplier_id": supplier_ids[0] if supplier_ids else 1,
            "depot_id": depot_ids[1] if depot_ids else 2,
            "data": {
                "coc_rebate": None,  # N/A
                "cost_of_collection": None,  # N/A
                "del_rebate": 2.8,
                "zone_differential": 0.3,
                "distance_km": 18.7
            },
            "status": "approved"
        },
        # XYZ Logistics submissions
        {
            "supplier_id": supplier_ids[1] if len(supplier_ids) > 1 else 2,
            "depot_id": depot_ids[0] if depot_ids else 1,
            "data": {
                "coc_rebate": 2.2,
                "cost_of_collection": 1.1,
                "del_rebate": None,  # N/A
                "zone_differential": 0.4,
                "distance_km": 30.1
            },
            "status": "pending"
        },
        {
            "supplier_id": supplier_ids[1] if len(supplier_ids) > 1 else 2,
            "depot_id": depot_ids[2] if len(depot_ids) > 2 else 3,
            "data": {
                "coc_rebate": 2.6,
                "cost_of_collection": 1.3,
                "del_rebate": 3.2,
                "zone_differential": 0.6,
                "distance_km": 22.5
            },
            "status": "approved"
        },
        # FastTrack Solutions submissions
        {
            "supplier_id": supplier_ids[2] if len(supplier_ids) > 2 else 3,
            "depot_id": depot_ids[1] if len(depot_ids) > 1 else 2,
            "data": {
                "coc_rebate": 2.3,
                "cost_of_collection": 1.0,
                "del_rebate": 2.9,
                "zone_differential": 0.35,
                "distance_km": 28.9
            },
            "status": "pending"
        },
        # GreenFleet Services submissions
        {
            "supplier_id": supplier_ids[3] if len(supplier_ids) > 3 else 4,
            "depot_id": depot_ids[0] if depot_ids else 1,
            "data": {
                "coc_rebate": 2.7,
                "cost_of_collection": 1.4,
                "del_rebate": 3.1,
                "zone_differential": 0.45,
                "distance_km": 19.2
            },
            "status": "approved"
        }
    ]
    
    for submission in sample_submissions:
        try:
            submission_id = db.submit_supplier_data(
                submission["supplier_id"],
                submission["depot_id"],
                submission["data"]
            )
            
            # Approve if needed
            if submission["status"] == "approved":
                db.approve_submission(submission_id, "System Admin")
            
            print(f"✓ Created submission ID: {submission_id} (Status: {submission['status']})")
        except Exception as e:
            print(f"✗ Failed to create submission: {e}")
    
    # Create sample supplier scores
    sample_scores = [
        {"supplier_id": supplier_ids[0] if supplier_ids else 1, "total_score": 85.2, "criteria": {"Quality": 8.5, "Reliability": 8.0, "Cost": 9.0, "Service": 8.7}},
        {"supplier_id": supplier_ids[1] if len(supplier_ids) > 1 else 2, "total_score": 72.4, "criteria": {"Quality": 7.2, "Reliability": 7.5, "Cost": 7.8, "Service": 6.9}},
        {"supplier_id": supplier_ids[2] if len(supplier_ids) > 2 else 3, "total_score": 91.1, "criteria": {"Quality": 9.1, "Reliability": 9.2, "Cost": 8.8, "Service": 9.3}},
        {"supplier_id": supplier_ids[3] if len(supplier_ids) > 3 else 4, "total_score": 78.8, "criteria": {"Quality": 7.8, "Reliability": 8.2, "Cost": 7.5, "Service": 7.7}},
        {"supplier_id": supplier_ids[4] if len(supplier_ids) > 4 else 5, "total_score": 82.6, "criteria": {"Quality": 8.2, "Reliability": 8.5, "Cost": 8.0, "Service": 8.4}}
    ]
    
    for score in sample_scores:
        try:
            score_id = db.save_supplier_scores(
                score["supplier_id"],
                score["total_score"],
                json.dumps(score["criteria"])
            )
            print(f"✓ Created score for supplier {score['supplier_id']}: {score['total_score']}")
        except Exception as e:
            print(f"✗ Failed to create score: {e}")
    
    print("\n🎉 Sample data setup complete!")
    print(f"✓ Created {len(suppliers)} suppliers")
    print(f"✓ Created {len(depots)} depots")
    print(f"✓ Created {len(sample_submissions)} submissions")
    print(f"✓ Created {len(sample_scores)} supplier scores")
    
    # Show summary
    print("\n📊 Data Summary:")
    submissions = db.get_supplier_submissions()
    approved_count = len([s for s in submissions if s['status'] == 'approved'])
    pending_count = len([s for s in submissions if s['status'] == 'pending'])
    
    print(f"  • Approved submissions: {approved_count}")
    print(f"  • Pending submissions: {pending_count}")
    print(f"  • Total submissions: {len(submissions)}")
    
    # Test data export
    print("\n🔄 Testing data export...")
    try:
        export_data = db.export_to_optimizer_format()
        print(f"✓ Obj1_Coeff data: {len(export_data['Obj1_Coeff'])} rows")
        print(f"✓ Obj2_Coeff data: {len(export_data['Obj2_Coeff'])} rows")
        print(f"✓ Annual Volumes data: {len(export_data['Annual Volumes'])} rows")
        
        # Test Excel file creation
        temp_file = db.create_temporary_excel_file()
        print(f"✓ Created temporary Excel file: {temp_file}")
        
        # Clean up
        import os
        try:
            os.remove(temp_file)
            print("✓ Cleaned up temporary file")
        except:
            pass
            
    except Exception as e:
        print(f"✗ Data export test failed: {e}")
    
    print("\n🚀 System is ready for testing!")
    print("  • Start the backend APIs: python run_full_backend.py")
    print("  • Start the frontend: npm start (in the react directory)")
    print("  • Open browser to: http://localhost:3000")

if __name__ == "__main__":
    setup_sample_data()