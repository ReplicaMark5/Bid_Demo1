#!/usr/bin/env python3
"""
Minimal backend with step-by-step optimization testing
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
import sys
import os

# Add backend directory to path
sys.path.append('./backend')

app = FastAPI(title="Minimal Optimizer API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store optimizer
optimizer_instance = None

class OptimizerInitRequest(BaseModel):
    file_path: str
    sheet_names: Dict[str, str]
    random_seed: int = 42

class OptimizationRequest(BaseModel):
    n_points: int = 5
    constraint_type: str = "cost"

@app.get("/")
async def root():
    return {"message": "Minimal Optimizer API", "status": "running"}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "optimizer_loaded": optimizer_instance is not None}

@app.post("/api/optimization/initialize")
async def initialize_optimizer(request: OptimizerInitRequest):
    """Initialize optimizer with minimal error handling"""
    global optimizer_instance
    
    try:
        print(f"🚀 Attempting to initialize optimizer...")
        print(f"📁 File path: {request.file_path}")
        print(f"📊 Sheet names: {request.sheet_names}")
        
        # Check if file exists
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=400, detail=f"File not found: {request.file_path}")
        
        # Import and initialize optimizer
        from MOO_e_constraint_Dynamic_Bid import SelectiveNAFlexibleEConstraintOptimizer
        print("✅ Optimizer class imported successfully")
        
        optimizer_instance = SelectiveNAFlexibleEConstraintOptimizer(
            request.file_path, 
            request.sheet_names
        )
        print("✅ Optimizer initialized successfully")
        
        return {
            "success": True,
            "message": "Optimizer initialized successfully",
            "n_depots": optimizer_instance.n_depots,
            "n_suppliers": optimizer_instance.n_suppliers,
            "total_pairs": len(optimizer_instance.all_pairs)
        }
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

@app.post("/api/optimization/run")
async def run_optimization(request: OptimizationRequest):
    """Run optimization with detailed error reporting"""
    global optimizer_instance
    
    try:
        if optimizer_instance is None:
            raise HTTPException(status_code=400, detail="Optimizer not initialized. Call /initialize first.")
        
        print(f"🎯 Starting optimization...")
        print(f"   - n_points: {request.n_points}")
        print(f"   - constraint_type: {request.constraint_type}")
        
        # Run optimization with very small parameters first
        df_pareto = optimizer_instance.optimize_epsilon_constraint(
            n_points=request.n_points,
            constraint_type=request.constraint_type
        )
        print("✅ Optimization completed successfully")
        
        # Convert to simple format
        solutions = []
        for _, row in df_pareto.iterrows():
            solutions.append({
                "epsilon": float(row.get("epsilon", 0)),
                "cost": float(row.get("cost", 0)),
                "score": float(row.get("score", 0)),
                "status": str(row.get("status", "Unknown")),
                "allocations": str(row.get("allocations", ""))
            })
        
        print(f"📊 Returning {len(solutions)} solutions")
        
        return {
            "success": True,
            "message": "Optimization completed successfully",
            "solutions": solutions
        }
        
    except Exception as e:
        print(f"❌ Optimization error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting minimal backend server...")
    print("📍 Server will be available at:")
    print("   - http://localhost:8000/ (Root)")
    print("   - http://localhost:8000/api/health (Health check)")
    print("   - http://localhost:8000/docs (API docs)")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)