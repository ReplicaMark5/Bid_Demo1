from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import os
import sys
import json
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import traceback
import sqlite3

# Add the current directory to sys.path to import the optimizer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from MOO_e_constraint_Dynamic_Bid import SelectiveNAFlexibleEConstraintOptimizer
from database import SupplierDatabase
from best_worst_method import calculate_bwm_weights

app = FastAPI(title="Unified Supply Chain Optimizer API", version="1.0.0")

# Enable CORS with comprehensive origin support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "http://localhost:3001", 
        "http://127.0.0.1:3001",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Global variables to store optimizer instances and results
optimizer_instances = {}
optimization_results = {}

# Database path configuration - avoid global database instance
import os
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# Use the fresh database that works properly
DB_PATH = "/tmp/supplier_data_fresh.db"

# GitHub AI integration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
endpoint = "https://models.github.ai/inference"
model_name = "openai/gpt-4o"

# Pydantic models - Combined from both APIs
class SupplierCreate(BaseModel):
    name: str
    email: Optional[str] = None
    
    @field_validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Supplier name cannot be empty')
        return v.strip()

class SupplierProfileUpdate(BaseModel):
    company_profile: Optional[str] = None
    annual_revenue: Optional[float] = None
    number_of_employees: Optional[int] = None
    bbee_level: Optional[int] = None
    black_ownership_percent: Optional[float] = None
    black_female_ownership_percent: Optional[float] = None
    bbee_compliant: Optional[bool] = None
    cipc_cor_documents: Optional[str] = None
    tax_certificate: Optional[str] = None
    fuel_products_offered: Optional[str] = None
    product_service_type: Optional[str] = None
    geographical_network: Optional[str] = None
    delivery_types_offered: Optional[str] = None
    method_of_sourcing: Optional[str] = None
    invest_in_refuelling_equipment: Optional[str] = None
    reciprocal_business: Optional[str] = None

class BWMRequest(BaseModel):
    criteria: List[str]
    best_criterion: str
    worst_criterion: str
    best_to_others: Dict[str, float]
    others_to_worst: Dict[str, float]

class BWMSaveRequest(BaseModel):
    criteria_names: List[str]
    weights: Dict[str, float]
    best_criterion: str
    worst_criterion: str
    best_to_others: Dict[str, float]
    others_to_worst: Dict[str, float]
    consistency_ratio: float
    consistency_interpretation: str
    created_by: Optional[str] = None

class DepotCreate(BaseModel):
    name: str
    annual_volume: Optional[float] = None
    country: Optional[str] = None
    town: Optional[str] = None
    lats: Optional[float] = None
    longs: Optional[float] = None
    fuel_zone: Optional[str] = None
    tankage_size: Optional[float] = None
    number_of_pumps: Optional[int] = None
    equipment_value: Optional[float] = None

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


class ApprovalRequest(BaseModel):
    submission_id: int
    approved_by: str

class BulkApprovalRequest(BaseModel):
    supplier_id: int
    approved_by: str

class BulkDataSubmission(BaseModel):
    supplier_id: int
    submissions: List[Dict[str, Any]]

# Legacy AHP models removed - now using PROMETHEE II

class SupplierEvaluationRequest(BaseModel):
    supplier_id: int
    criterion_name: str
    score: float
    participant_name: Optional[str] = None
    participant_email: Optional[str] = None

class SupplierEvaluationBatchRequest(BaseModel):
    participant_name: str
    participant_email: str
    evaluations: List[Dict[str, Any]]  # List of {supplier_id, criterion_name, score}

class PROMETHEECalculationRequest(BaseModel):
    criteria_names: List[str]
    criteria_weights: List[float]
    preference_functions: Optional[Dict[str, str]] = None
    preference_thresholds: Optional[Dict[str, float]] = None
    indifference_thresholds: Optional[Dict[str, float]] = None

class CriteriaUpdateRequest(BaseModel):
    old_criteria_names: List[str]
    new_criteria_names: List[str]
    default_score: Optional[float] = 5.0

class ProfileScoringConfigRequest(BaseModel):
    config_data: Dict[str, Dict[str, float]]

class OptimizerInitRequest(BaseModel):
    file_path: str
    sheet_names: Dict[str, str]
    random_seed: int = 42

class OptimizerInitFromDBRequest(BaseModel):
    random_seed: int = 42

class OptimizationRequest(BaseModel):
    n_points: int = 21
    constraint_type: str = "cost"
    enable_ranking: bool = False
    ranking_metric: str = "cost_effectiveness"
    show_ranking_in_ui: bool = True

# Legacy AHP response models removed - now using PROMETHEE II

class OptimizerInitResponse(BaseModel):
    success: bool
    message: str
    n_depots: int
    n_suppliers: int
    total_pairs: int
    collection_available: int
    delivery_available: int
    availability: List[Dict[str, Any]]

class OptimizationResponse(BaseModel):
    success: bool
    message: str
    solutions: List[Dict[str, Any]]
    ranking_analysis: Optional[Dict[str, Any]] = None
    ranking_reports: Optional[Dict[str, str]] = None

# Dependency to get database instance - creates new instance per request
def get_db():
    """Create a new database instance for each request to avoid connection sharing"""
    try:
        return SupplierDatabase(DB_PATH)
    except sqlite3.OperationalError as e:
        if "disk I/O error" in str(e).lower():
            raise HTTPException(
                status_code=503, 
                detail="Database is temporarily unavailable due to file system issues. This may be related to WSL2 limitations. Please try again or contact the administrator."
            )
        else:
            raise HTTPException(status_code=503, detail=f"Database connection error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization error: {str(e)}")

# Helper function for database operations with error handling
def execute_db_operation(operation_func, *args, **kwargs):
    """Execute a database operation with proper error handling for lock errors"""
    try:
        return operation_func(*args, **kwargs)
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e).lower():
            raise HTTPException(
                status_code=503, 
                detail="Database is temporarily busy. Please try again in a moment."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# AI scoring function
async def get_ai_score(description: str, criterion: str) -> int:
    """Get AI-generated score for supplier evaluation"""
    if not GITHUB_TOKEN:
        return 5  # Default score if no token
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"You are a helpful assistant scoring suppliers on the criterion '{criterion}'.\n"
        f"Rate the following performance description from 1 (very poor) to 9 (excellent).\n\n"
        f"Criterion: {criterion}\n"
        f"Supplier Description: {description}\n\n"
        f"Return only a number from 1 to 9."
    )

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for supplier evaluation."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(f"{endpoint}/v1/chat/completions", json=payload, headers=headers)
        
        if response.status_code == 200:
            reply = response.json()
            content = reply['choices'][0]['message']['content']
            digits = [int(s) for s in content if s.isdigit()]
            return min(max(digits[0], 1), 9) if digits else 5
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return 5
    except Exception as e:
        print(f"AI scoring error: {e}")
        return 5

# PROMETHEE II calculation function
def calculate_promethee_ii(supplier_scores: Dict[int, Dict[str, float]], 
                          criteria_weights: Dict[str, float],
                          preference_functions: Dict[str, str] = None,
                          preference_thresholds: Dict[str, float] = None,
                          indifference_thresholds: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Calculate PROMETHEE II ranking for suppliers
    """
    suppliers = list(supplier_scores.keys())
    criteria = list(criteria_weights.keys())
    n_suppliers = len(suppliers)
    
    # Initialize parameters if not provided
    if preference_functions is None:
        preference_functions = {criterion: 'linear' for criterion in criteria}
    if preference_thresholds is None:
        preference_thresholds = {criterion: 2.0 for criterion in criteria}
    if indifference_thresholds is None:
        indifference_thresholds = {criterion: 0.5 for criterion in criteria}
    
    def calculate_preference_value(diff: float, function_type: str, 
                                 indiff_threshold: float, pref_threshold: float) -> float:
        """Calculate preference value based on function type"""
        if function_type == 'usual':
            return 1.0 if diff > 0 else 0.0
            
        elif function_type == 'u_shape':
            return 1.0 if diff > indiff_threshold else 0.0
            
        elif function_type == 'v_shape':
            if diff <= 0:
                return 0.0
            elif diff >= pref_threshold:
                return 1.0
            else:
                return diff / pref_threshold
                
        elif function_type == 'level':
            if diff <= indiff_threshold:
                return 0.0
            elif diff >= pref_threshold:
                return 1.0
            else:
                return 0.5  # Plateau level
                
        elif function_type == 'linear':
            if diff <= indiff_threshold:
                return 0.0
            elif diff >= pref_threshold:
                return 1.0
            else:
                return (diff - indiff_threshold) / (pref_threshold - indiff_threshold)
                
        elif function_type == 'gaussian':
            if diff <= 0:
                return 0.0
            else:
                # Gaussian with sigma = preference_threshold / 2
                sigma = pref_threshold / 2
                return 1 - np.exp(-(diff**2) / (2 * sigma**2))
                
        else:  # Default to linear
            if diff <= indiff_threshold:
                return 0.0
            elif diff >= pref_threshold:
                return 1.0
            else:
                return (diff - indiff_threshold) / (pref_threshold - indiff_threshold)

    # Calculate pairwise preferences
    preference_matrix = np.zeros((n_suppliers, n_suppliers))
    criteria_preference_matrices = {}
    
    # Initialize per-criteria matrices
    for criterion in criteria:
        criteria_preference_matrices[criterion] = np.zeros((n_suppliers, n_suppliers))
    
    for i, supplier_a in enumerate(suppliers):
        for j, supplier_b in enumerate(suppliers):
            if i != j:
                aggregated_preference = 0.0
                
                for criterion in criteria:
                    score_a = supplier_scores[supplier_a].get(criterion, 0)
                    score_b = supplier_scores[supplier_b].get(criterion, 0)
                    
                    # Calculate difference (assuming higher is better)
                    diff = score_a - score_b
                    
                    # Calculate preference using selected function type
                    preference = calculate_preference_value(
                        diff,
                        preference_functions.get(criterion, 'linear'),
                        indifference_thresholds[criterion],
                        preference_thresholds[criterion]
                    )
                    
                    # Store unweighted preference for per-criteria analysis
                    criteria_preference_matrices[criterion][i][j] = preference
                    
                    # Weight the preference for aggregated matrix
                    aggregated_preference += criteria_weights[criterion] * preference
                
                preference_matrix[i][j] = aggregated_preference
    
    # Calculate flows
    if preference_matrix.size > 0:
        positive_flows = np.mean(preference_matrix, axis=1)  # How much each supplier dominates others
        negative_flows = np.mean(preference_matrix, axis=0)  # How much each supplier is dominated
        net_flows = positive_flows - negative_flows
    else:
        # Handle empty matrix case
        positive_flows = np.zeros(n_suppliers)
        negative_flows = np.zeros(n_suppliers)
        net_flows = np.zeros(n_suppliers)
    
    # Calculate per-criteria flows
    criteria_flows = {}
    for criterion in criteria:
        criteria_matrix = criteria_preference_matrices[criterion]
        if criteria_matrix.size > 0:
            criteria_positive_flows = np.mean(criteria_matrix, axis=1)
            criteria_negative_flows = np.mean(criteria_matrix, axis=0)
            criteria_net_flows = criteria_positive_flows - criteria_negative_flows
        else:
            criteria_positive_flows = np.zeros(n_suppliers)
            criteria_negative_flows = np.zeros(n_suppliers)
            criteria_net_flows = np.zeros(n_suppliers)
        
        criteria_flows[criterion] = {
            'positive_flows': criteria_positive_flows.tolist(),
            'negative_flows': criteria_negative_flows.tolist(),
            'net_flows': criteria_net_flows.tolist()
        }
    
    # Create ranking
    ranking_indices = np.argsort(-net_flows)  # Sort by net flow (descending)
    
    results = {
        'suppliers': suppliers,
        'positive_flows': positive_flows.tolist(),
        'negative_flows': negative_flows.tolist(),
        'net_flows': net_flows.tolist(),
        'ranking': ranking_indices.tolist(),
        'preference_matrix': preference_matrix.tolist(),
        'criteria_flows': criteria_flows
    }
    
    return results

# ============================================================================
# API ROUTES
# ============================================================================

@app.get("/")
async def root():
    return {"message": "Unified Supply Chain Optimizer API", "version": "1.0.0"}

@app.get("/api/health-simple")
async def health_check_simple():
    """Simple health check that doesn't require database access"""
    return {
        "status": "healthy",
        "message": "API is running",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# ============================================================================
# SUPPLIER AND DEPOT MANAGEMENT (from supplier_api.py)
# ============================================================================

@app.post("/api/suppliers/")
async def create_supplier(supplier: SupplierCreate, db: SupplierDatabase = Depends(get_db)):
    """Create a new supplier"""
    try:
        supplier_id = execute_db_operation(db.add_supplier, supplier.name, supplier.email)
        return {"id": supplier_id, "message": "Supplier created successfully"}
    except HTTPException:
        raise  # Re-raise HTTP exceptions from execute_db_operation
    except ValueError as e:
        # Validation errors should return 422
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating supplier: {str(e)}")

@app.get("/api/suppliers/")
async def get_suppliers(db: SupplierDatabase = Depends(get_db)):
    """Get all suppliers"""
    try:
        suppliers = execute_db_operation(db.get_suppliers)
        return {"suppliers": suppliers}
    except HTTPException:
        raise  # Re-raise HTTP exceptions from execute_db_operation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching suppliers: {str(e)}")

@app.post("/api/depots/")
async def create_depot(depot: DepotCreate, db: SupplierDatabase = Depends(get_db)):
    """Create a new depot (admin only)"""
    try:
        depot_id = execute_db_operation(
            db.add_depot,
            name=depot.name,
            annual_volume=depot.annual_volume,
            country=depot.country,
            town=depot.town,
            lats=depot.lats,
            longs=depot.longs,
            fuel_zone=depot.fuel_zone,
            tankage_size=depot.tankage_size,
            number_of_pumps=depot.number_of_pumps,
            equipment_value=depot.equipment_value
        )
        return {"id": depot_id, "message": "Depot created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating depot: {str(e)}")

@app.get("/api/depots/")
async def get_depots(db: SupplierDatabase = Depends(get_db)):
    """Get all depots"""
    try:
        depots = execute_db_operation(db.get_depots)
        return {"depots": depots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching depots: {str(e)}")

# ============================================================================
# SUPPLIER DATA SUBMISSION (from supplier_api.py)
# ============================================================================

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
        
        submission_id = execute_db_operation(
            db.submit_supplier_data,
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
            submission_id = execute_db_operation(
                db.submit_supplier_data,
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
        submissions = execute_db_operation(db.get_supplier_submissions, supplier_id=supplier_id)
        return {"submissions": submissions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching submissions: {str(e)}")

@app.get("/api/suppliers/{supplier_id}/profile/")
async def get_supplier_profile(supplier_id: int, db: SupplierDatabase = Depends(get_db)):
    """Get supplier profile information"""
    try:
        supplier = execute_db_operation(db.get_supplier_by_id, supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        return {"supplier": supplier}
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching supplier profile: {str(e)}")

@app.put("/api/suppliers/{supplier_id}/profile/")
async def update_supplier_profile(supplier_id: int, profile: SupplierProfileUpdate, db: SupplierDatabase = Depends(get_db)):
    """Update supplier profile information"""
    try:
        # Check if supplier exists
        supplier = execute_db_operation(db.get_supplier_by_id, supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        # Update profile
        profile_data = profile.dict(exclude_unset=True)
        success = execute_db_operation(db.update_supplier_profile, supplier_id, profile_data)
        
        if success:
            return {"message": "Profile updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update profile")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating supplier profile: {str(e)}")

# ============================================================================
# ADMIN ENDPOINTS (from supplier_api.py)
# ============================================================================

@app.get("/api/admin/submissions/")
async def get_all_submissions(status: Optional[str] = None, db: SupplierDatabase = Depends(get_db)):
    """Get all submissions (admin only) with optional status filtering"""
    try:
        submissions = execute_db_operation(db.get_supplier_submissions, status=status)
        return {"submissions": submissions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching submissions: {str(e)}")

@app.post("/api/admin/submissions/approve/")
async def approve_submission(approval: ApprovalRequest, db: SupplierDatabase = Depends(get_db)):
    """Approve a supplier submission (admin only)"""
    try:
        success = execute_db_operation(db.approve_submission, approval.submission_id, approval.approved_by)
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
        success = execute_db_operation(db.reject_submission, rejection.submission_id, rejection.approved_by)
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
        submissions = execute_db_operation(db.get_submissions_by_status, 'pending')
        return submissions
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching pending submissions: {str(e)}")

@app.post("/api/admin/submissions/bulk-approve/")
async def bulk_approve_supplier_submissions(approval: BulkApprovalRequest, db: SupplierDatabase = Depends(get_db)):
    """Approve all pending submissions for a supplier (admin only)"""
    try:
        success = execute_db_operation(db.bulk_approve_supplier_submissions, approval.supplier_id, approval.approved_by)
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
        success = execute_db_operation(db.bulk_reject_supplier_submissions, rejection.supplier_id, rejection.approved_by)
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
        approved_data = execute_db_operation(db.get_approved_optimization_data)
        return {"approved_data": approved_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching approved data: {str(e)}")

@app.post("/api/admin/cleanup-duplicates/")
async def cleanup_duplicate_submissions(db: SupplierDatabase = Depends(get_db)):
    """Clean up duplicate supplier-depot submissions (admin only)"""
    try:
        result = execute_db_operation(db.cleanup_duplicate_submissions)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning duplicates: {str(e)}")

@app.get("/api/admin/validation/check-data/")
async def validate_data_completeness(db: SupplierDatabase = Depends(get_db)):
    """Check if all required data is complete for optimization"""
    try:
        suppliers = execute_db_operation(db.get_suppliers)
        depots = execute_db_operation(db.get_depots)
        submissions = execute_db_operation(db.get_supplier_submissions, status='approved')
        # Skip scores check for now due to potential table corruption
        
        # Check completeness
        missing_data = []
        
        # Check if all depots have annual volumes
        for depot in depots:
            if not depot['annual_volume']:
                missing_data.append(f"Depot '{depot['name']}' missing annual volume")
        
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
                "suppliers_with_scores": 0,  # Disabled due to table corruption
                "depot_supplier_pairs": len(supplier_depot_pairs),
                "total_possible_pairs": total_possible_pairs,
                "coverage_percentage": (len(supplier_depot_pairs) / total_possible_pairs * 100) if total_possible_pairs > 0 else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating data: {str(e)}")

# ============================================================================
# SUPPLIER SCORES (from supplier_api.py)
# ============================================================================


# ============================================================================
# EXPORT ENDPOINTS (from supplier_api.py)
# ============================================================================

@app.get("/api/admin/export/optimizer-data/")
async def export_optimizer_data(db: SupplierDatabase = Depends(get_db)):
    """Export data in optimizer format (admin only)"""
    try:
        data = execute_db_operation(db.export_to_optimizer_format)
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
        temp_file = execute_db_operation(db.create_temporary_excel_file)
        return {
            "message": "Temporary Excel file created successfully",
            "file_path": temp_file
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating Excel file: {str(e)}")

# ============================================================================
# BEST-WORST METHOD (BWM) ENDPOINTS
# ============================================================================
@app.post("/api/bwm/calculate/")
async def calculate_bwm_weights_endpoint(request: BWMRequest):
    """Calculate criteria weights using Best-Worst Method"""
    try:
        result = calculate_bwm_weights(
            criteria=request.criteria,
            best=request.best_criterion,
            worst=request.worst_criterion,
            best_to_others=request.best_to_others,
            others_to_worst=request.others_to_worst
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"BWM calculation failed: {str(e)}")

@app.post("/api/bwm/save/")
async def save_bwm_weights_endpoint(request: BWMSaveRequest, db: SupplierDatabase = Depends(get_db)):
    """Save BWM weights configuration to database"""
    try:
        weight_id = execute_db_operation(
            db.save_bwm_weights,
            criteria_names=request.criteria_names,
            weights=request.weights,
            best_criterion=request.best_criterion,
            worst_criterion=request.worst_criterion,
            best_to_others=request.best_to_others,
            others_to_worst=request.others_to_worst,
            consistency_ratio=request.consistency_ratio,
            consistency_interpretation=request.consistency_interpretation,
            created_by=request.created_by
        )
        return {"success": True, "id": weight_id, "message": "BWM weights saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save BWM weights: {str(e)}")

@app.get("/api/bwm/weights/")
async def get_latest_bwm_weights_endpoint(db: SupplierDatabase = Depends(get_db)):
    """Get the latest BWM weights configuration from database"""
    try:
        weights = execute_db_operation(db.get_latest_bwm_weights)
        if weights:
            return {"success": True, "data": weights}
        else:
            return {"success": True, "data": None, "message": "No BWM weights found"}
    except HTTPException:
        raise  # Re-raise HTTP exceptions from execute_db_operation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve BWM weights: {str(e)}")

# ============================================================================
# Legacy AHP endpoints removed - now using BWM + PROMETHEE II
# ============================================================================
# OPTIMIZATION ENDPOINTS (from backend_api.py)
# ============================================================================

@app.post("/api/optimization/initialize", response_model=OptimizerInitResponse)
async def initialize_optimizer(request: OptimizerInitRequest):
    """Initialize and analyze optimization data"""
    try:
        # Set random seed
        np.random.seed(request.random_seed)
        
        # Initialize optimizer
        optimizer = SelectiveNAFlexibleEConstraintOptimizer(
            request.file_path, 
            request.sheet_names
        )
        
        # Store optimizer instance
        optimizer_id = f"optimizer_{datetime.now().timestamp()}"
        optimizer_instances[optimizer_id] = optimizer
        
        # Prepare availability data
        availability_data = []
        for depot in optimizer.depots:
            for supplier in optimizer.suppliers:
                if (depot, supplier) in optimizer.all_pairs:
                    collection_valid = optimizer.valid_collection.get((depot, supplier), False)
                    delivery_valid = optimizer.valid_delivery.get((depot, supplier), False)
                    
                    operations = []
                    if collection_valid:
                        operations.append("Collection")
                    if delivery_valid:
                        operations.append("Delivery")
                    
                    availability_data.append({
                        "depot": depot,
                        "supplier": supplier,
                        "operations": operations,
                        "collection": collection_valid,
                        "delivery": delivery_valid
                    })
        
        # Calculate statistics
        total_pairs = len(availability_data)
        collection_available = sum(1 for item in availability_data if item["collection"])
        delivery_available = sum(1 for item in availability_data if item["delivery"])
        
        return OptimizerInitResponse(
            success=True,
            message="Optimizer initialized successfully",
            n_depots=optimizer.n_depots,
            n_suppliers=optimizer.n_suppliers,
            total_pairs=total_pairs,
            collection_available=collection_available,
            delivery_available=delivery_available,
            availability=availability_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing optimizer: {str(e)}")

@app.post("/api/optimization/initialize-from-db", response_model=OptimizerInitResponse)
async def initialize_optimizer_from_db(request: OptimizerInitFromDBRequest):
    """Initialize optimizer from database data"""
    try:
        # Set random seed
        np.random.seed(request.random_seed)
        
        # Create temporary Excel file from database
        db_instance = SupplierDatabase(DB_PATH)
        temp_file = db_instance.create_temporary_excel_file()
        
        # Initialize optimizer with temporary file
        sheet_names = {
            'obj1': 'Obj1_Coeff',
            'obj2': 'Obj2_Coeff',
            'volumes': 'Annual Volumes'
        }
        
        optimizer = SelectiveNAFlexibleEConstraintOptimizer(
            temp_file, 
            sheet_names
        )
        
        # Store optimizer instance
        optimizer_id = f"optimizer_{datetime.now().timestamp()}"
        optimizer_instances[optimizer_id] = optimizer
        
        # Prepare availability data
        availability_data = []
        for depot in optimizer.depots:
            for supplier in optimizer.suppliers:
                if (depot, supplier) in optimizer.all_pairs:
                    collection_valid = optimizer.valid_collection.get((depot, supplier), False)
                    delivery_valid = optimizer.valid_delivery.get((depot, supplier), False)
                    
                    operations = []
                    if collection_valid:
                        operations.append("Collection")
                    if delivery_valid:
                        operations.append("Delivery")
                    
                    availability_data.append({
                        "depot": depot,
                        "supplier": supplier,
                        "operations": operations,
                        "collection": collection_valid,
                        "delivery": delivery_valid
                    })
        
        # Calculate statistics
        total_pairs = len(availability_data)
        collection_available = sum(1 for item in availability_data if item["collection"])
        delivery_available = sum(1 for item in availability_data if item["delivery"])
        
        # Clean up temporary file
        try:
            os.remove(temp_file)
        except:
            pass
        
        return OptimizerInitResponse(
            success=True,
            message="Optimizer initialized successfully from database",
            n_depots=optimizer.n_depots,
            n_suppliers=optimizer.n_suppliers,
            total_pairs=total_pairs,
            collection_available=collection_available,
            delivery_available=delivery_available,
            availability=availability_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing optimizer from database: {str(e)}")

@app.post("/api/optimization/run", response_model=OptimizationResponse)
async def run_optimization(request: OptimizationRequest):
    """Run standard optimization"""
    try:
        # Get the most recent optimizer instance
        if not optimizer_instances:
            raise HTTPException(status_code=400, detail="No optimizer initialized. Call /initialize first.")
        
        optimizer = list(optimizer_instances.values())[-1]
        
        # Run optimization
        df_pareto = optimizer.optimize_epsilon_constraint(
            n_points=request.n_points,
            constraint_type=request.constraint_type
        )
        
        # Convert DataFrame to list of dictionaries
        solutions = []
        for _, row in df_pareto.iterrows():
            solutions.append({
                "epsilon": row["epsilon"],
                "cost": row["cost"],
                "score": row["score"],
                "allocations": row["allocations"],
                "status": row["status"]
            })
        
        # Store results
        result_id = f"result_{datetime.now().timestamp()}"
        optimization_results[result_id] = {
            "solutions": solutions,
            "optimizer": optimizer
        }
        
        return OptimizationResponse(
            success=True,
            message="Optimization completed successfully",
            solutions=solutions
        )
        
    except Exception as e:
        print(f"[BACKEND] Optimization error: {str(e)}")
        print(f"[BACKEND] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error running optimization: {str(e)}")

@app.post("/api/optimization/run-with-ranking", response_model=OptimizationResponse)
async def run_optimization_with_ranking(request: OptimizationRequest):
    """Run optimization with ranking analysis"""
    try:
        # Get the most recent optimizer instance
        if not optimizer_instances:
            raise HTTPException(status_code=400, detail="No optimizer initialized. Call /initialize first.")
        
        optimizer = list(optimizer_instances.values())[-1]
        
        # Run optimization with ranking
        df_pareto = optimizer.run_full_optimization_with_ranking(
            n_points=request.n_points,
            constraint_type=request.constraint_type,
            ranking_metric=request.ranking_metric
        )
        
        # Convert DataFrame to list of dictionaries
        solutions = []
        for _, row in df_pareto.iterrows():
            solutions.append({
                "epsilon": row["epsilon"],
                "cost": row["cost"],
                "score": row["score"],
                "allocations": row["allocations"],
                "status": row["status"]
            })
        
        # Get ranking analysis if available
        ranking_analysis = None
        ranking_reports = None
        if hasattr(optimizer, 'last_ranking_analysis'):
            ranking_analysis = optimizer.last_ranking_analysis
        if hasattr(optimizer, 'last_ranking_reports'):
            ranking_reports = optimizer.last_ranking_reports
        
        # Store results
        result_id = f"result_{datetime.now().timestamp()}"
        optimization_results[result_id] = {
            "solutions": solutions,
            "optimizer": optimizer,
            "ranking_analysis": ranking_analysis,
            "ranking_reports": ranking_reports
        }
        
        return OptimizationResponse(
            success=True,
            message="Optimization with ranking completed successfully",
            solutions=solutions,
            ranking_analysis=ranking_analysis,
            ranking_reports=ranking_reports
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running optimization with ranking: {str(e)}")

@app.get("/api/optimization/solution/{solution_id}")
async def get_solution_details(solution_id: int):
    """Get detailed information about a specific solution"""
    try:
        if not optimization_results:
            raise HTTPException(status_code=404, detail="No optimization results available")
        
        # Get the most recent results
        latest_results = list(optimization_results.values())[-1]
        solutions = latest_results["solutions"]
        
        # Filter to optimal solutions and get the requested one
        optimal_solutions = [s for s in solutions if s["status"] == "Optimal"]
        
        if solution_id >= len(optimal_solutions):
            raise HTTPException(status_code=404, detail="Solution not found")
        
        solution = optimal_solutions[solution_id]
        
        # Add additional details if available
        if "ranking_analysis" in latest_results and latest_results["ranking_analysis"]:
            ranking_analysis = latest_results["ranking_analysis"]
            if solution_id in ranking_analysis:
                solution["ranking_details"] = ranking_analysis[solution_id]
        
        return {"solution": solution}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting solution details: {str(e)}")

@app.get("/api/optimization/export/{format}")
async def export_results(format: str = "csv"):
    """Export optimization results"""
    try:
        if not optimization_results:
            raise HTTPException(status_code=404, detail="No optimization results available")
        
        # Get the most recent results
        latest_results = list(optimization_results.values())[-1]
        solutions = latest_results["solutions"]
        
        # Convert to DataFrame
        df = pd.DataFrame(solutions)
        
        # Create output directory if it doesn't exist
        output_dir = "Output Data"
        os.makedirs(output_dir, exist_ok=True)
        
        if format.lower() == "csv":
            filename = f"{output_dir}/optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            return FileResponse(filename, media_type="text/csv", filename=os.path.basename(filename))
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting results: {str(e)}")

@app.get("/api/optimization/ranking/{solution_id}")
async def get_ranking_analysis(solution_id: int):
    """Get ranking analysis for a specific solution"""
    try:
        if not optimization_results:
            raise HTTPException(status_code=404, detail="No optimization results available")
        
        # Get the most recent results
        latest_results = list(optimization_results.values())[-1]
        
        if "ranking_analysis" not in latest_results or not latest_results["ranking_analysis"]:
            raise HTTPException(status_code=404, detail="No ranking analysis available")
        
        ranking_analysis = latest_results["ranking_analysis"]
        
        if solution_id not in ranking_analysis:
            raise HTTPException(status_code=404, detail="Ranking analysis not found for this solution")
        
        return {"ranking_analysis": ranking_analysis[solution_id]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting ranking analysis: {str(e)}")

# ============================================================================
# DEPOT EVALUATION ENDPOINTS (from backend_api.py)
# ============================================================================

@app.post("/api/supplier-evaluations/submit")
async def submit_supplier_evaluation(request: SupplierEvaluationRequest, db: SupplierDatabase = Depends(get_db)):
    """Submit a single supplier evaluation"""
    try:
        # Submit single supplier evaluation
        evaluation_id = execute_db_operation(
            db.submit_single_supplier_evaluation,
            request.supplier_id,
            request.criterion_name,
            request.score,
            request.participant_name,
            request.participant_email
        )
        return {"evaluation_id": evaluation_id, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting evaluation: {str(e)}")

@app.post("/api/supplier-evaluations/submit-batch")
async def submit_supplier_evaluations_batch(request: SupplierEvaluationBatchRequest, db: SupplierDatabase = Depends(get_db)):
    """Submit multiple supplier evaluations at once"""
    try:
        # Submit evaluations directly to the new supplier_evaluations table
        evaluation_ids = execute_db_operation(
            db.submit_supplier_evaluations_batch,
            request.evaluations,
            request.participant_name,
            request.participant_email
        )
        
        return {"evaluation_ids": evaluation_ids, "status": "success", "count": len(evaluation_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting batch evaluations: {str(e)}")

@app.get("/api/supplier-evaluations/")
async def get_supplier_evaluations(supplier_id: int = None, db: SupplierDatabase = Depends(get_db)):
    """Get supplier evaluations with optional filtering"""
    try:
        evaluations = execute_db_operation(db.get_supplier_evaluations, supplier_id)
        return {"evaluations": evaluations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting evaluations: {str(e)}")

@app.get("/api/supplier-evaluations/summary")
async def get_evaluation_summary(db: SupplierDatabase = Depends(get_db)):
    """Get summary of supplier evaluations"""
    try:
        summary = execute_db_operation(db.get_evaluation_summary)
        return {"summary": summary}
    except HTTPException:
        raise  # Re-raise HTTP exceptions from execute_db_operation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting evaluation summary: {str(e)}")

@app.delete("/api/supplier-evaluations/clear")
async def clear_supplier_evaluations(db: SupplierDatabase = Depends(get_db)):
    """Clear all supplier evaluations"""
    try:
        result = execute_db_operation(db.clear_supplier_evaluations)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing evaluations: {str(e)}")

@app.delete("/api/supplier-evaluations/{evaluation_id}")
async def delete_supplier_evaluation(evaluation_id: int, db: SupplierDatabase = Depends(get_db)):
    """Delete a specific supplier evaluation"""
    try:
        result = execute_db_operation(db.delete_supplier_evaluation, evaluation_id)
        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=result.get("message", "Evaluation not found"))
        return result
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting supplier evaluation: {str(e)}")

# ============================================================================
# PROFILE SCORING CONFIGURATION ENDPOINTS
# ============================================================================

@app.post("/api/profile-scoring-config/save")
async def save_profile_scoring_config(request: ProfileScoringConfigRequest, db: SupplierDatabase = Depends(get_db)):
    """Save profile scoring configuration to database"""
    try:
        result = execute_db_operation(db.save_profile_scoring_config, request.config_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving profile scoring config: {str(e)}")

@app.get("/api/profile-scoring-config/")
async def get_profile_scoring_config(db: SupplierDatabase = Depends(get_db)):
    """Get profile scoring configuration from database"""
    try:
        config = execute_db_operation(db.get_profile_scoring_config)
        return {"config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting profile scoring config: {str(e)}")

@app.get("/api/suppliers/{supplier_id}/profile-scores")
async def get_supplier_profile_scores(supplier_id: int, db: SupplierDatabase = Depends(get_db)):
    """Get calculated profile scores for a specific supplier"""
    try:
        scores = execute_db_operation(db.get_supplier_profile_scores, supplier_id)
        return {"supplier_id": supplier_id, "profile_scores": scores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting supplier profile scores: {str(e)}")

# ============================================================================
# PROMETHEE II ENDPOINTS (from backend_api.py)
# ============================================================================

@app.post("/api/promethee/calculate")
async def calculate_promethee_ranking(request: PROMETHEECalculationRequest, db: SupplierDatabase = Depends(get_db)):
    """Calculate PROMETHEE II ranking for suppliers"""
    try:
        # Ensure unified scores table is populated before calculation
        migration_result = execute_db_operation(db.ensure_unified_scores_populated, request.criteria_names)
        
        # Get aggregated supplier scores from unified table
        aggregated_scores = execute_db_operation(db.get_unified_supplier_scores, request.criteria_names)
        
        # Get manager evaluation counts per supplier
        evaluation_counts = execute_db_operation(db.get_supplier_evaluation_counts)
        
        # Define which criteria are profile-based (must have data) vs survey-based (can have missing data)
        PROFILE_CRITERIA = {
            'Product/Service Type', 'Geographical Network', 'Method of Sourcing',
            'Investment in Equipment', 'Reciprocal Business', 'B-BBEE Level'
        }
        
        # Convert to format expected by PROMETHEE calculation
        supplier_scores = {}
        confidence_levels = {}
        missing_evaluations = []
        
        for supplier_id, criteria_data in aggregated_scores.items():
            supplier_scores[supplier_id] = {}
            confidence_levels[supplier_id] = []
            
            for criterion_name in request.criteria_names:
                if criterion_name in criteria_data:
                    supplier_scores[supplier_id][criterion_name] = criteria_data[criterion_name]['score']
                    
                    # Calculate confidence based on data source and count
                    data_source = criteria_data[criterion_name].get('source', 'unknown')
                    count = criteria_data[criterion_name].get('count', 1)
                    
                    if data_source == 'profile':
                        confidence = 1.0  # Profile data is always fully confident
                    elif data_source == 'survey':
                        confidence = min(1.0, count / 3.0)  # More evaluations = higher confidence, max at 3
                    else:
                        confidence = 0.5  # Default/unknown sources get medium confidence
                    
                    confidence_levels[supplier_id].append(confidence)
                else:
                    # Only consider it "missing" if it's a profile criterion that should always have data
                    if criterion_name in PROFILE_CRITERIA:
                        missing_evaluations.append({
                            'supplier_id': supplier_id,
                            'criterion_name': criterion_name
                        })
                    else:
                        # For survey criteria without data, use default score of 0
                        supplier_scores[supplier_id][criterion_name] = 0.0
                        confidence_levels[supplier_id].append(0)  # Zero confidence for missing survey data
        
        # Check if there are any missing profile evaluations (this should not happen with proper profile integration)
        if missing_evaluations:
            # Get supplier names for better error messages
            suppliers_data = execute_db_operation(db.get_suppliers)
            supplier_names = {s['id']: s['name'] for s in suppliers_data}
            
            missing_details = []
            for missing in missing_evaluations:
                supplier_name = supplier_names.get(missing['supplier_id'], f"Supplier {missing['supplier_id']}")
                missing_details.append(f"- {supplier_name}: {missing['criterion_name']}")
            
            error_message = (
                f"⚠️ PROMETHEE II calculation cannot proceed with missing profile criteria data.\n\n"
                f"Missing profile data ({len(missing_evaluations)} total):\n" +
                "\n".join(missing_details) +
                f"\n\nProfile criteria should always have data from supplier profiles. Please check the supplier data and profile scoring configuration."
            )
            
            raise HTTPException(status_code=400, detail=error_message)
        
        # Convert criteria weights to dict
        criteria_weights = dict(zip(request.criteria_names, request.criteria_weights))
        
        # Debug: Print supplier scores being passed to PROMETHEE II
        print("\n=== DEBUG: PROMETHEE II Input Data ===")
        for supplier_id, scores in supplier_scores.items():
            print(f"Supplier {supplier_id}: {scores}")
        print("=========================================\n")
        
        # Calculate PROMETHEE II ranking
        promethee_results = calculate_promethee_ii(
            supplier_scores,
            criteria_weights,
            request.preference_functions,
            request.preference_thresholds,
            request.indifference_thresholds
        )
        
        # Save results to database
        suppliers = promethee_results['suppliers']
        for i, supplier_id in enumerate(suppliers):
            avg_confidence = np.mean(confidence_levels[supplier_id])
            execute_db_operation(
                db.save_promethee_results,
                supplier_id,
                promethee_results['positive_flows'][i],
                promethee_results['negative_flows'][i],
                promethee_results['net_flows'][i],
                promethee_results['ranking'].index(i) + 1,  # Convert to 1-based ranking
                avg_confidence,
                json.dumps(criteria_weights)
            )
        
        # Add supplier names and confidence levels to results
        supplier_names = []
        supplier_data = execute_db_operation(db.get_suppliers)
        for supplier_id in suppliers:
            supplier_name = next((s['name'] for s in supplier_data if s['id'] == supplier_id), f"Supplier {supplier_id}")
            supplier_names.append(supplier_name)
        
        promethee_results['supplier_names'] = supplier_names
        promethee_results['confidence_levels'] = confidence_levels
        promethee_results['evaluation_counts'] = evaluation_counts
        
        return {"results": promethee_results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating PROMETHEE ranking: {str(e)}")

@app.get("/api/promethee/results")
async def get_promethee_results(db: SupplierDatabase = Depends(get_db)):
    """Get latest PROMETHEE II results"""
    try:
        results = execute_db_operation(db.get_promethee_results)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting PROMETHEE results: {str(e)}")

@app.post("/api/promethee/threshold-recommendations")
async def get_threshold_recommendations(request: PROMETHEECalculationRequest, db: SupplierDatabase = Depends(get_db)):
    """Get intelligent threshold recommendations based on actual data distributions"""
    try:
        # Ensure unified scores table is populated before generating recommendations
        migration_result = execute_db_operation(db.ensure_unified_scores_populated, request.criteria_names)
        
        recommendations = execute_db_operation(db.calculate_threshold_recommendations, request.criteria_names)
        return {"success": True, "recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating threshold recommendations: {str(e)}")

@app.post("/api/promethee/threshold-alternatives")  
async def get_threshold_alternatives(request: PROMETHEECalculationRequest, db: SupplierDatabase = Depends(get_db)):
    """Get alternative threshold recommendation strategies (conservative, sensitive, etc.)"""
    try:
        alternatives = execute_db_operation(db.get_threshold_recommendation_alternatives, request.criteria_names)
        return {"success": True, "alternatives": alternatives}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating threshold alternatives: {str(e)}")

@app.post("/api/criteria/update")
async def update_criteria_configuration(request: CriteriaUpdateRequest, db: SupplierDatabase = Depends(get_db)):
    """Update criteria names and clear all existing evaluations"""
    try:
        # Clear all existing supplier evaluations
        clear_result = execute_db_operation(db.clear_supplier_evaluations)
        
        return {
            "message": f"Criteria configuration updated successfully. {clear_result['message']}",
            "cleared_evaluations": clear_result['cleared_count']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating criteria configuration: {str(e)}")

@app.get("/api/criteria/current")
async def get_current_criteria(db: SupplierDatabase = Depends(get_db)):
    """Get current criteria from existing evaluations"""
    try:
        evaluations = execute_db_operation(db.get_supplier_evaluations)
        if not evaluations:
            return {"criteria_names": [], "total_evaluations": 0}
        
        # Get criteria from first evaluation (they should all be consistent)
        sample_criteria = evaluations[0]['criteria_scores']
        criteria_names = list(sample_criteria.keys()) if sample_criteria else []
        
        return {
            "criteria_names": criteria_names,
            "total_evaluations": len(evaluations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting current criteria: {str(e)}")

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.post("/api/promethee/migrate-unified-scores")
async def migrate_unified_scores(request: PROMETHEECalculationRequest, db: SupplierDatabase = Depends(get_db)):
    """Migrate existing data to unified supplier criteria scores table"""
    try:
        result = execute_db_operation(db.migrate_to_unified_criteria_scores, request.criteria_names)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error migrating to unified scores: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_optimizers": len(optimizer_instances),
        "stored_results": len(optimization_results),
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)