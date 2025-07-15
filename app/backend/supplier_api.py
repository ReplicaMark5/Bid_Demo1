from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from database import SupplierDatabase

app = FastAPI(title="Supplier Data Submission API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = SupplierDatabase()

# Pydantic models
class SupplierCreate(BaseModel):
    name: str
    email: Optional[str] = None

class DepotCreate(BaseModel):
    name: str
    annual_volume: Optional[float] = None

class SupplierDataSubmission(BaseModel):
    supplier_id: int
    depot_id: int
    coc_rebate: Optional[float] = None
    cost_of_collection: Optional[float] = None
    del_rebate: Optional[float] = None
    zone_differential: float
    distance_km: Optional[float] = None
    
    @field_validator('zone_differential')
    def validate_zone_differential(cls, v):
        if v is None:
            raise ValueError('Zone differential is required')
        return v

class SupplierScores(BaseModel):
    supplier_id: int
    total_score: float
    criteria_scores: Dict[str, float]

class ApprovalRequest(BaseModel):
    submission_id: int
    approved_by: str

class BulkApprovalRequest(BaseModel):
    supplier_id: int
    approved_by: str

class BulkDataSubmission(BaseModel):
    supplier_id: int
    submissions: List[Dict[str, Any]]

# Dependency to get database instance
def get_db():
    return db

# API Routes

@app.get("/")
async def root():
    return {"message": "Supplier Data Submission API", "version": "1.0.0"}

@app.post("/api/suppliers/")
async def create_supplier(supplier: SupplierCreate, db: SupplierDatabase = Depends(get_db)):
    """Create a new supplier"""
    try:
        supplier_id = db.add_supplier(supplier.name, supplier.email)
        return {"id": supplier_id, "message": "Supplier created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating supplier: {str(e)}")

@app.get("/api/suppliers/")
async def get_suppliers(db: SupplierDatabase = Depends(get_db)):
    """Get all suppliers"""
    try:
        suppliers = db.get_suppliers()
        return {"suppliers": suppliers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching suppliers: {str(e)}")

@app.post("/api/depots/")
async def create_depot(depot: DepotCreate, db: SupplierDatabase = Depends(get_db)):
    """Create a new depot (admin only)"""
    try:
        depot_id = db.add_depot(depot.name, depot.annual_volume)
        return {"id": depot_id, "message": "Depot created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating depot: {str(e)}")

@app.get("/api/depots/")
async def get_depots(db: SupplierDatabase = Depends(get_db)):
    """Get all depots"""
    try:
        depots = db.get_depots()
        return {"depots": depots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching depots: {str(e)}")

@app.post("/api/suppliers/submit-data/")
async def submit_supplier_data(submission: SupplierDataSubmission, db: SupplierDatabase = Depends(get_db)):
    """Submit supplier data for a specific depot"""
    try:
        # Convert to dict for database storage
        data = {
            'coc_rebate': submission.coc_rebate,
            'cost_of_collection': submission.cost_of_collection,
            'del_rebate': submission.del_rebate,
            'zone_differential': submission.zone_differential,
            'distance_km': submission.distance_km
        }
        
        submission_id = db.submit_supplier_data(
            submission.supplier_id,
            submission.depot_id,
            data
        )
        
        return {
            "id": submission_id,
            "message": "Data submitted successfully and pending approval"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error submitting data: {str(e)}")

@app.post("/api/suppliers/submit-bulk-data/")
async def submit_bulk_supplier_data(bulk_submission: BulkDataSubmission, db: SupplierDatabase = Depends(get_db)):
    """Submit supplier data for multiple depots"""
    try:
        submission_ids = []
        for depot_data in bulk_submission.submissions:
            submission_id = db.submit_supplier_data(
                bulk_submission.supplier_id,
                depot_data['depot_id'],
                depot_data
            )
            submission_ids.append(submission_id)
        
        return {
            "ids": submission_ids,
            "message": f"Bulk data submitted successfully for {len(submission_ids)} depots"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error submitting bulk data: {str(e)}")

@app.get("/api/suppliers/{supplier_id}/submissions/")
async def get_supplier_submissions(supplier_id: int, db: SupplierDatabase = Depends(get_db)):
    """Get submissions for a specific supplier"""
    try:
        submissions = db.get_supplier_submissions(supplier_id=supplier_id)
        return {"submissions": submissions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching submissions: {str(e)}")

@app.get("/api/admin/submissions/")
async def get_all_submissions(status: Optional[str] = None, db: SupplierDatabase = Depends(get_db)):
    """Get all submissions (admin only) with optional status filtering"""
    try:
        submissions = db.get_supplier_submissions(status=status)
        return {"submissions": submissions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching submissions: {str(e)}")

@app.post("/api/admin/submissions/approve/")
async def approve_submission(approval: ApprovalRequest, db: SupplierDatabase = Depends(get_db)):
    """Approve a supplier submission (admin only)"""
    try:
        success = db.approve_submission(approval.submission_id, approval.approved_by)
        if success:
            return {"message": "Submission approved successfully"}
        else:
            raise HTTPException(status_code=404, detail="Submission not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error approving submission: {str(e)}")

@app.post("/api/admin/submissions/reject/")
async def reject_submission(rejection: ApprovalRequest, db: SupplierDatabase = Depends(get_db)):
    """Reject a supplier submission (admin only)"""
    try:
        success = db.reject_submission(rejection.submission_id, rejection.approved_by)
        if success:
            return {"message": "Submission rejected successfully"}
        else:
            raise HTTPException(status_code=404, detail="Submission not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error rejecting submission: {str(e)}")

@app.get("/api/admin/submissions/pending/")
async def get_pending_submissions(db: SupplierDatabase = Depends(get_db)):
    """Get all pending submissions (admin only)"""
    try:
        submissions = db.get_submissions_by_status('pending')
        return submissions
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching pending submissions: {str(e)}")

@app.post("/api/admin/submissions/bulk-approve/")
async def bulk_approve_supplier_submissions(approval: BulkApprovalRequest, db: SupplierDatabase = Depends(get_db)):
    """Approve all pending submissions for a supplier (admin only)"""
    try:
        success = db.bulk_approve_supplier_submissions(approval.supplier_id, approval.approved_by)
        if success:
            return {"message": "All supplier submissions approved successfully"}
        else:
            raise HTTPException(status_code=404, detail="No pending submissions found for this supplier")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error approving bulk submissions: {str(e)}")

@app.post("/api/admin/submissions/bulk-reject/")
async def bulk_reject_supplier_submissions(rejection: BulkApprovalRequest, db: SupplierDatabase = Depends(get_db)):
    """Reject all pending submissions for a supplier (admin only)"""
    try:
        success = db.bulk_reject_supplier_submissions(rejection.supplier_id, rejection.approved_by)
        if success:
            return {"message": "All supplier submissions rejected successfully"}
        else:
            raise HTTPException(status_code=404, detail="No pending submissions found for this supplier")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error rejecting bulk submissions: {str(e)}")

@app.get("/api/admin/approved-data/")
async def get_approved_optimization_data(db: SupplierDatabase = Depends(get_db)):
    """Get all approved data ready for optimization"""
    try:
        # Get approved submissions with supplier and depot details
        approved_data = db.get_approved_optimization_data()
        return {"approved_data": approved_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching approved data: {str(e)}")

@app.post("/api/suppliers/scores/")
async def save_supplier_scores(scores: SupplierScores, db: SupplierDatabase = Depends(get_db)):
    """Save supplier AHP scores"""
    try:
        criteria_scores_json = json.dumps(scores.criteria_scores)
        score_id = db.save_supplier_scores(
            scores.supplier_id,
            scores.total_score,
            criteria_scores_json
        )
        return {"id": score_id, "message": "Scores saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error saving scores: {str(e)}")

@app.get("/api/suppliers/scores/")
async def get_supplier_scores(db: SupplierDatabase = Depends(get_db)):
    """Get all supplier scores"""
    try:
        scores = db.get_supplier_scores()
        # Parse JSON criteria scores
        for score in scores:
            if score['criteria_scores']:
                score['criteria_scores'] = json.loads(score['criteria_scores'])
        return {"scores": scores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching scores: {str(e)}")

@app.get("/api/admin/export/optimizer-data/")
async def export_optimizer_data(db: SupplierDatabase = Depends(get_db)):
    """Export data in optimizer format (admin only)"""
    try:
        data = db.export_to_optimizer_format()
        return {
            "message": "Data exported successfully",
            "data": {
                "obj1_coeff": data['Obj1_Coeff'].to_dict('records'),
                "obj2_coeff": data['Obj2_Coeff'].to_dict('records'),
                "annual_volumes": data['Annual Volumes'].to_dict('records')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting data: {str(e)}")

@app.post("/api/admin/create-temp-excel/")
async def create_temp_excel(db: SupplierDatabase = Depends(get_db)):
    """Create temporary Excel file for optimizer (admin only)"""
    try:
        temp_file = db.create_temporary_excel_file()
        return {
            "message": "Temporary Excel file created successfully",
            "file_path": temp_file
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating Excel file: {str(e)}")

@app.get("/api/admin/validation/check-data/")
async def validate_data_completeness(db: SupplierDatabase = Depends(get_db)):
    """Check if all required data is complete for optimization"""
    try:
        suppliers = db.get_suppliers()
        depots = db.get_depots()
        submissions = db.get_supplier_submissions(status='approved')
        scores = db.get_supplier_scores()
        
        # Check completeness
        missing_data = []
        
        # Check if all depots have annual volumes
        for depot in depots:
            if not depot['annual_volume']:
                missing_data.append(f"Depot '{depot['name']}' missing annual volume")
        
        # Check if all suppliers have scores
        supplier_ids_with_scores = {score['supplier_id'] for score in scores}
        for supplier in suppliers:
            if supplier['id'] not in supplier_ids_with_scores:
                missing_data.append(f"Supplier '{supplier['name']}' missing scores")
        
        # Check depot-supplier coverage
        supplier_depot_pairs = {(s['supplier_id'], s['depot_id']) for s in submissions}
        total_possible_pairs = len(suppliers) * len(depots)
        
        return {
            "is_complete": len(missing_data) == 0,
            "missing_data": missing_data,
            "statistics": {
                "total_suppliers": len(suppliers),
                "total_depots": len(depots),
                "approved_submissions": len(submissions),
                "suppliers_with_scores": len(supplier_ids_with_scores),
                "depot_supplier_pairs": len(supplier_depot_pairs),
                "total_possible_pairs": total_possible_pairs,
                "coverage_percentage": (len(supplier_depot_pairs) / total_possible_pairs * 100) if total_possible_pairs > 0 else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating data: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)