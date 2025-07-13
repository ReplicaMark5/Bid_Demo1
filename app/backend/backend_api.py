from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys
import json
import requests
import numpy as np
import pandas as pd
from datetime import datetime
import traceback

# Add the current directory to sys.path to import the optimizer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from MOO_e_constraint_Dynamic_Bid import SelectiveNAFlexibleEConstraintOptimizer

app = FastAPI(title="Supply Chain Optimizer API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store optimizer instances and results
optimizer_instances = {}
optimization_results = {}

# Pydantic models for request/response
class AHPScoreRequest(BaseModel):
    description: str
    criterion: str

class AHPCalculationRequest(BaseModel):
    criteria_names: List[str]
    criteria_weights: List[float]
    supplier_names: List[str]
    scores_matrix: List[List[float]]

class OptimizerInitRequest(BaseModel):
    file_path: str
    sheet_names: Dict[str, str]
    random_seed: int = 42

class OptimizationRequest(BaseModel):
    n_points: int = 21
    constraint_type: str = "cost"
    enable_ranking: bool = False
    ranking_metric: str = "cost_effectiveness"
    show_ranking_in_ui: bool = True

class AHPScoreResponse(BaseModel):
    score: int
    description: str
    criterion: str

class AHPCalculationResponse(BaseModel):
    weighted_scores: List[float]
    criteria_weights: List[float]
    normalized_weights: List[float]

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

# GitHub AI integration (same as Streamlit app)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
endpoint = "https://models.github.ai/inference"
model_name = "openai/gpt-4o"

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

# API Routes

@app.get("/")
async def root():
    return {"message": "Supply Chain Optimizer API", "version": "1.0.0"}

@app.post("/api/ahp/ai-score", response_model=AHPScoreResponse)
async def get_ai_supplier_score(request: AHPScoreRequest):
    """Get AI-generated score for supplier description"""
    try:
        score = await get_ai_score(request.description, request.criterion)
        return AHPScoreResponse(
            score=score,
            description=request.description,
            criterion=request.criterion
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting AI score: {str(e)}")

@app.post("/api/ahp/calculate", response_model=AHPCalculationResponse)
async def calculate_ahp_scores(request: AHPCalculationRequest):
    """Calculate AHP weighted scores"""
    try:
        # Convert to numpy arrays for calculation
        scores_matrix = np.array(request.scores_matrix)
        weights = np.array(request.criteria_weights)
        
        # Calculate weighted scores
        weighted_scores = np.dot(scores_matrix, weights)
        
        # Normalize weights
        weight_sum = sum(request.criteria_weights)
        normalized_weights = [w / weight_sum for w in request.criteria_weights]
        
        return AHPCalculationResponse(
            weighted_scores=weighted_scores.tolist(),
            criteria_weights=request.criteria_weights,
            normalized_weights=normalized_weights
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating AHP scores: {str(e)}")

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

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_optimizers": len(optimizer_instances),
        "stored_results": len(optimization_results)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)