#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'backend'))

from MOO_e_constraint_Dynamic_Bid import SelectiveNAFlexibleEConstraintOptimizer

def test_optimizer():
    try:
        # Excel file path
        excel_file = "/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Demo3.xlsx"
        
        print("🔄 Initializing optimizer...")
        optimizer = SelectiveNAFlexibleEConstraintOptimizer(excel_file)
        
        print("✅ Optimizer initialized successfully")
        print("🎯 Starting optimization...")
        
        # Test the optimization
        df_pareto = optimizer.optimize_epsilon_constraint(
            n_points=5,  # Small number for testing
            constraint_type='cost'
        )
        
        print("✅ Optimization completed!")
        print(f"Generated {len(df_pareto)} Pareto points")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_optimizer()