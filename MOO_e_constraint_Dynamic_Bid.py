from docplex.mp.model import Model
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import os
from collections import defaultdict

class SelectiveNAFlexibleEConstraintOptimizer:
    def __init__(self, file_path, sheet_names=None):
        """
        Initialize the e-constraint optimizer with selective NA handling
        """
        if sheet_names is None:
            sheet_names = {
                'obj1': 'Obj1_Coeff',
                'obj2': 'Obj2_Coeff', 
                'volumes': 'Annual Volumes'
            }
        
        self.file_path = file_path
        self.sheet_names = sheet_names
        self.load_data()
    
    def load_data(self):
        """Load and parse data from Excel file with selective NA handling"""
        try:
            # Load data sheets
            self.df_data = pd.read_excel(self.file_path, sheet_name=self.sheet_names['obj1'])
            self.df_scores = pd.read_excel(self.file_path, sheet_name=self.sheet_names['obj2'])
            self.df_volume = pd.read_excel(self.file_path, sheet_name=self.sheet_names['volumes'])
            
            print("Original data shape:", self.df_data.shape)
            print("Columns in df_data:", self.df_data.columns.tolist())
            
            # Parse depot-supplier pairs EXACTLY like the original
            self.df_data['Key'] = list(zip(self.df_data['Depot'], self.df_data['Supplier']))
            self.all_pairs = self.df_data['Key'].tolist()
            self.depots = sorted(set(i for i, _ in self.all_pairs))
            self.suppliers = sorted(set(j for _, j in self.all_pairs))
            
            self.n_depots = len(self.depots)
            self.n_suppliers = len(self.suppliers)
            
            # SELECTIVE NA HANDLING: Check which operations are valid for each pair
            self.valid_collection = {}  # (depot, supplier) -> bool
            self.valid_delivery = {}    # (depot, supplier) -> bool
            
            for idx, row in self.df_data.iterrows():
                key = (row['Depot'], row['Supplier'])
                
                # Check if Collection is valid (needs COC Rebate and Cost of Collection)
                coc_valid = not (pd.isna(row['COC Rebate(R/L)']) or row['COC Rebate(R/L)'] == 'NA')
                cost_valid = not (pd.isna(row['Cost of Collection (R/L)']) or row['Cost of Collection (R/L)'] == 'NA')
                self.valid_collection[key] = coc_valid and cost_valid
                
                # Check if Delivery is valid (needs DEL Rebate)
                del_valid = not (pd.isna(row['DEL Rebate(R/L)']) or row['DEL Rebate(R/L)'] == 'NA')
                self.valid_delivery[key] = del_valid
                
                # Report invalid operations
                if not self.valid_collection[key]:
                    print(f"Collection DISABLED for Depot {key[0]} - Supplier {key[1]} (COC or Cost NA)")
                if not self.valid_delivery[key]:
                    print(f"Delivery DISABLED for Depot {key[0]} - Supplier {key[1]} (DEL NA)")
            
            # Check if any depot has no valid operations at all
            depot_has_valid_operation = defaultdict(bool)
            for (depot, supplier) in self.all_pairs:
                if self.valid_collection.get((depot, supplier), False) or self.valid_delivery.get((depot, supplier), False):
                    depot_has_valid_operation[depot] = True
            
            empty_depots = [depot for depot in self.depots if not depot_has_valid_operation[depot]]
            if empty_depots:
                raise ValueError(f"Depots {empty_depots} have no feasible operations after filtering NA values!")
            
            print(f"Data loaded: Depots={self.depots}, Suppliers={self.suppliers}")
            print(f"Available depot-supplier pairs: {len(self.all_pairs)}")
            
            # Create coefficient dictionaries for ALL pairs (we'll handle NA during evaluation)
            self.COC = dict(zip(self.df_data['Key'], self.df_data['COC Rebate(R/L)']))
            self.DEL = dict(zip(self.df_data['Key'], self.df_data['DEL Rebate(R/L)']))
            self.COST = dict(zip(self.df_data['Key'], self.df_data['Cost of Collection (R/L)']))
            self.ZD = dict(zip(self.df_data['Key'], self.df_data['Zone Differentials']))
            
            # Convert to numeric where possible, keep NA as is for now
            for key in self.all_pairs:
                # Only convert if not NA
                if not (pd.isna(self.COC[key]) or self.COC[key] == 'NA'):
                    self.COC[key] = pd.to_numeric(self.COC[key], errors='coerce')
                if not (pd.isna(self.DEL[key]) or self.DEL[key] == 'NA'):
                    self.DEL[key] = pd.to_numeric(self.DEL[key], errors='coerce')
                if not (pd.isna(self.COST[key]) or self.COST[key] == 'NA'):
                    self.COST[key] = pd.to_numeric(self.COST[key], errors='coerce')
                # Zone differentials should always be numeric
                self.ZD[key] = pd.to_numeric(self.ZD[key], errors='coerce')
            
            # Check if Distance column exists (from original but not used in calculations)
            if 'Distance(Km)' in self.df_data.columns:
                self.DIST = dict(zip(self.df_data['Key'], self.df_data['Distance(Km)']))
            
            # Parse volume data - handle different possible formats
            if "Site Names" in self.df_volume.columns:
                # Extract depot number from 'Depot 1', 'Depot 2', etc.
                depot_numbers = self.df_volume["Site Names"].str.extract(r"Depot (\d+)").astype(int)[0]
                self.V = dict(zip(depot_numbers, self.df_volume["Annual Volume(Litres)"]))
            elif "Depot" in self.df_volume.columns:
                # Direct depot column
                self.V = dict(zip(self.df_volume["Depot"], self.df_volume["Annual Volume(Litres)"]))
            else:
                raise ValueError("Cannot find depot information in volume data")
            
            # Remove NaN keys from volume data
            self.V = {k: v for k, v in self.V.items() if pd.notna(k)}
            
            # Parse score data EXACTLY like original
            score_row = self.df_scores.iloc[6]  # Row 6 contains the total scores
            score_row.index = score_row.index.str.strip()
            score_row = score_row.drop(labels=["Scoring Element", "Criteria Weighting"], errors="ignore")
            self.S = score_row.to_dict()
            
            # Same diesel price as original
            self.DP = 23.0
            
            print(f"Volume data: {self.V}")
            print(f"Score data: {self.S}")
            
            # Identify which depots have suppliers available for valid operations
            self.depot_suppliers = defaultdict(set)
            for (i, j) in self.all_pairs:
                # Only include supplier for depot if at least one operation is valid
                if self.valid_collection.get((i, j), False) or self.valid_delivery.get((i, j), False):
                    self.depot_suppliers[i].add(j)
            
            print("Depot-supplier availability (with valid operations):")
            for depot in self.depots:
                available_suppliers = sorted(self.depot_suppliers[depot])
                print(f"  Depot {depot}: Suppliers {available_suppliers}")
            
            # Print operation availability summary
            print("\nOperation availability summary:")
            for depot in self.depots:
                print(f"Depot {depot}:")
                for supplier in sorted(self.depot_suppliers[depot]):
                    operations = []
                    if self.valid_collection.get((depot, supplier), False):
                        operations.append("Collection")
                    if self.valid_delivery.get((depot, supplier), False):
                        operations.append("Delivery")
                    print(f"  Supplier {supplier}: {', '.join(operations) if operations else 'No valid operations'}")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            raise
    
    def create_model(self, epsilon, constraint_type="cost"):
        """
        Create optimization model with e-constraint and selective operation constraints
        constraint_type: "cost" or "score" - which objective to constrain
        """
        model_name = f"E_Constraint_SelectiveNA_{constraint_type}≤{epsilon:.0f}"
        mdl = Model(name=model_name)
        
        # Decision variables for all available depot-supplier pairs
        C = mdl.binary_var_dict(self.all_pairs, name="C")  # Collection
        D = mdl.binary_var_dict(self.all_pairs, name="D")  # Delivery
        
        # Constraint: Exactly one valid allocation per depot
        for depot in self.depots:
            available_suppliers = list(self.depot_suppliers[depot])
            if available_suppliers:  # Only add constraint if depot has suppliers with valid operations
                valid_operations = []
                for supplier in available_suppliers:
                    if self.valid_collection.get((depot, supplier), False):
                        valid_operations.append(C[depot, supplier])
                    if self.valid_delivery.get((depot, supplier), False):
                        valid_operations.append(D[depot, supplier])
                
                if valid_operations:  # Only add constraint if there are valid operations
                    mdl.add_constraint(
                        mdl.sum(valid_operations) == 1,
                        ctname=f"one_valid_allocation_depot_{depot}"
                    )
        
        # Constraint: Disable invalid operations explicitly
        for (depot, supplier) in self.all_pairs:
            if not self.valid_collection.get((depot, supplier), False):
                mdl.add_constraint(C[depot, supplier] == 0, ctname=f"disable_collection_{depot}_{supplier}")
            if not self.valid_delivery.get((depot, supplier), False):
                mdl.add_constraint(D[depot, supplier] == 0, ctname=f"disable_delivery_{depot}_{supplier}")
        
        # Define objectives with selective coefficient usage
        # Cost objective (to minimize) - only apply coefficients for valid operations
        cost_terms = []
        for (i, j) in self.all_pairs:
            if i in self.V:  # Only include depots with volume data
                base_cost = self.DP + self.ZD.get((i, j), 0)
                
                # Collection cost reduction - only if valid and coefficients are numeric
                collection_benefit = 0
                if self.valid_collection.get((i, j), False):
                    coc_val = self.COC.get((i, j), 0)
                    cost_val = self.COST.get((i, j), 0)
                    if isinstance(coc_val, (int, float)) and isinstance(cost_val, (int, float)):
                        collection_benefit = C[i, j] * (coc_val - cost_val)
                
                # Delivery cost reduction - only if valid and coefficient is numeric
                delivery_benefit = 0
                if self.valid_delivery.get((i, j), False):
                    del_val = self.DEL.get((i, j), 0)
                    if isinstance(del_val, (int, float)):
                        delivery_benefit = D[i, j] * del_val
                
                cost_terms.append(self.V[i] * (base_cost - collection_benefit - delivery_benefit))
        
        cost_obj = mdl.sum(cost_terms) if cost_terms else 0
        
        # Score objective (to maximize) - only for valid operations
        score_terms = []
        for (i, j) in self.all_pairs:
            if f"Supplier {j}" in self.S:  # Only include suppliers with score data
                # Only count operations that are valid
                valid_ops = []
                if self.valid_collection.get((i, j), False):
                    valid_ops.append(C[i, j])
                if self.valid_delivery.get((i, j), False):
                    valid_ops.append(D[i, j])
                
                if valid_ops:
                    score_terms.append(self.S[f"Supplier {j}"] * mdl.sum(valid_ops))
        
        score_obj = mdl.sum(score_terms) if score_terms else 0
        
        # Apply e-constraint based on constraint type
        if constraint_type == "cost":
            # Constrain cost, maximize score
            mdl.add_constraint(cost_obj <= epsilon, ctname="epsilon_constraint")
            mdl.maximize(score_obj)
            primary_obj = score_obj
            constrained_obj = cost_obj
        else:  # constraint_type == "score"
            # Constrain score, minimize cost
            mdl.add_constraint(score_obj >= epsilon, ctname="epsilon_constraint")
            mdl.minimize(cost_obj)
            primary_obj = cost_obj
            constrained_obj = score_obj
        
        return mdl, C, D, cost_obj, score_obj, primary_obj, constrained_obj
    
    def solve_single_epsilon(self, epsilon, constraint_type="cost"):
        """Solve optimization for a single epsilon value"""
        mdl, C, D, cost_obj, score_obj, primary_obj, constrained_obj = self.create_model(epsilon, constraint_type)
        
        # Solve the model
        solution = mdl.solve()
        
        if solution:
            # Extract allocations - only show valid operations
            allocations = []
            for (i, j) in self.all_pairs:
                if C[i, j].solution_value == 1 and self.valid_collection.get((i, j), False):
                    allocations.append(f"C({i},{j})")
                elif D[i, j].solution_value == 1 and self.valid_delivery.get((i, j), False):
                    allocations.append(f"D({i},{j})")
            
            result = {
                "epsilon": epsilon,
                "cost": cost_obj.solution_value,
                "score": score_obj.solution_value,
                "allocations": " ".join(allocations),
                "status": "Optimal"
            }

        else:
            result = {
                "epsilon": epsilon,
                "cost": None,
                "score": None,
                "allocations": "No solution",
                "status": "Infeasible"
            }
        
        # Clean up model to free memory
        mdl.end()
        
        return result
    
    def optimize_epsilon_constraint(self, epsilon_range=None, n_points=21, constraint_type="cost"):
        """
        Run e-constraint optimization across epsilon range
        
        Args:
            epsilon_range: tuple (min, max) or None for auto-detection
            n_points: number of epsilon points to test
            constraint_type: "cost" or "score" - which objective to constrain
        """
        print(f"Starting e-constraint optimization with {constraint_type} constraint and selective NA handling...")
        
        # Auto-detect epsilon range if not provided
        if epsilon_range is None:
            epsilon_range = self.detect_epsilon_range(constraint_type)
        
        epsilons = np.linspace(epsilon_range[0], epsilon_range[1], n_points)
        print(f"Testing {n_points} epsilon values from {epsilon_range[0]:.2e} to {epsilon_range[1]:.2e}")
        
        results = []
        for i, eps in enumerate(epsilons):
            print(f"Solving epsilon {i+1}/{n_points}: {eps:.2e}")
            result = self.solve_single_epsilon(eps, constraint_type)
            results.append(result)
        
        return pd.DataFrame(results)
    
    def detect_epsilon_range(self, constraint_type="cost"):
        """
        Detect reasonable epsilon range by solving extreme cases with selective NA handling
        """
        print("Detecting epsilon range with selective NA handling...")
        
        # Solve for minimum cost (ignore score)
        mdl_min_cost, C, D, cost_obj, score_obj, _, _ = self.create_model(float('inf'), "cost")
        mdl_min_cost.minimize(cost_obj)
        sol_min_cost = mdl_min_cost.solve()
        
        # Solve for maximum score (ignore cost)  
        mdl_max_score, C2, D2, cost_obj2, score_obj2, _, _ = self.create_model(0, "score")
        mdl_max_score.maximize(score_obj2)
        sol_max_score = mdl_max_score.solve()
        
        if constraint_type == "cost":
            if sol_min_cost and sol_max_score:
                min_cost = cost_obj.solution_value
                max_cost = cost_obj2.solution_value
                epsilon_range = (min_cost, max_cost)
                print(f"Detected cost range: {min_cost:.2e} to {max_cost:.2e}")
            else:
                print("Warning: Could not detect range, using default")
                epsilon_range = (2.280e+08, 2.295e+08)  # Default from original
        else:  # score constraint
            if sol_min_cost and sol_max_score:
                min_score = score_obj.solution_value
                max_score = score_obj2.solution_value
                epsilon_range = (min_score, max_score)
                print(f"Detected score range: {min_score:.2e} to {max_score:.2e}")
            else:
                print("Warning: Could not detect range, using default")
                epsilon_range = (50, 200)  # Reasonable default for scores
        
        # Clean up models
        mdl_min_cost.end()
        mdl_max_score.end()
        
        return epsilon_range
    
    def run_full_optimization(self, epsilon_range=None, n_points=21, constraint_type="cost", **kwargs):


        """Run complete e-constraint optimization with results export"""
        print("="*60)
        print("SELECTIVE NA HANDLING E-CONSTRAINT OPTIMIZATION")
        print("="*60)
        print(f"Problem size: {self.n_depots} depots × {self.n_suppliers} suppliers")
        print(f"Total depot-supplier pairs: {len(self.all_pairs)}")
        print(f"Constraint type: {constraint_type.upper()}")
        
        # Show depot-specific information
        print("\nDepot-supplier availability (with valid operations):")
        for depot in self.depots:
            available_suppliers = sorted(self.depot_suppliers[depot])
            print(f"  Depot {depot}: Suppliers {available_suppliers}")
        
        # Show operation validity summary
        valid_collection_count = sum(1 for key in self.all_pairs if self.valid_collection.get(key, False))
        valid_delivery_count = sum(1 for key in self.all_pairs if self.valid_delivery.get(key, False))
        print(f"\nOperation validity:")
        print(f"  Valid collection operations: {valid_collection_count}/{len(self.all_pairs)}")
        print(f"  Valid delivery operations: {valid_delivery_count}/{len(self.all_pairs)}")
        
        print("="*60)
        
        # Run optimization
        df_pareto = self.optimize_epsilon_constraint(epsilon_range, n_points, constraint_type)
        
        # Filter out infeasible solutions
        df_feasible = df_pareto[df_pareto['status'] == 'Optimal'].copy()
        
        if len(df_feasible) == 0:
            print("No feasible solutions found!")
            return df_pareto
        
        # Save results
        output_path = "Output Data/"
        os.makedirs(output_path, exist_ok=True)
        df_pareto.to_csv(f"{output_path}MOO_e-const_{constraint_type}_selective_na_pareto.csv", index=False)
        
        # Print summary
        print(f"\nOptimization Results ({constraint_type} constraint with selective NA handling):")
        print(f"Total epsilon points tested: {len(df_pareto)}")
        print(f"Feasible solutions found: {len(df_feasible)}")
        if len(df_feasible) > 0:
            print(f"Cost range: {df_feasible['cost'].min():.2f} - {df_feasible['cost'].max():.2f}")
            print(f"Score range: {df_feasible['score'].min():.2f} - {df_feasible['score'].max():.2f}")
        
        # Show sample solutions
        print(f"\nSample Pareto optimal solutions:")
        print(df_feasible.head())
        
        # Create visualizations
        self.create_plots(df_feasible, output_path, constraint_type)
        
        return df_pareto
    
    def create_plots(self, df_pareto, save_path, constraint_type):
        """Create plots for e-constraint results"""
        if len(df_pareto) == 0:
            print("No data to plot")
            return
            
        # Matplotlib plot
        plt.figure(figsize=(8, 6))
        plt.plot(df_pareto["score"], df_pareto["cost"], marker='o', linestyle='-', alpha=0.7)
        plt.xlabel("Supplier Score (↑)")
        plt.ylabel("Total Cost (↓)")
        plt.title(f"Pareto Front: Cost vs Supplier Score (E-Constraint: {constraint_type}, Selective NA)")
        plt.grid(True)
        plt.gca().invert_yaxis()  # Lower cost is better
        plt.tight_layout()
        plt.savefig(f"{save_path}MOO_e-const_{constraint_type}_selective_na_pareto_plot.png")
        plt.show()
        
        # Interactive plotly plot
        fig = px.scatter(
            df_pareto,
            x="cost",
            y="score", 
            color="epsilon",
            hover_data=["epsilon", "allocations"],
            title=f"Interactive Pareto Front: E-Constraint Selective NA ({constraint_type} constraint)"
        )
        fig.update_layout(
            xaxis_title="Cost (Minimize)",
            yaxis_title="Supplier Score (Maximize)"
        )
        fig.show()
        
        # Print additional statistics
        unique_allocs = set(df_pareto["allocations"])
        print(f"\nUnique allocation patterns found: {len(unique_allocs)}")
        print(f"Total Pareto optimal solutions: {len(df_pareto)}")

    def _parse_allocation_string(self, allocation_str):
        """
        Parse allocation strings like "C(1,2) D(3,4)" into structured format
        
        Args:
            allocation_str: String containing allocations like "C(1,2) D(3,4)"
            
        Returns:
            dict: {depot: {'supplier': X, 'operation': 'collection/delivery'}}
        """
        if not allocation_str or allocation_str.lower() in ["no solution", "none", ""]:
            return {}
        
        allocations = {}
        for item in allocation_str.split():
            if '(' in item and ')' in item:
                operation = item[0]  # 'C' or 'D'
                params = item[2:-1]  # Remove parentheses
                if ',' in params:
                    depot, supplier = params.split(',')
                    depot = int(depot)
                    supplier = int(supplier)
                    
                    allocations[depot] = {
                        'supplier': supplier,
                        'operation': 'collection' if operation == 'C' else 'delivery'
                    }
        
        return allocations
    
    def _calculate_switch_impact(self, depot, new_supplier, new_operation, current_allocation, current_cost, current_score):
        """
        Calculate exact cost and score impact of switching one depot to different supplier/operation
        
        Args:
            depot: Depot number
            new_supplier: New supplier number
            new_operation: 'collection' or 'delivery'
            current_allocation: Current allocation dict from _parse_allocation_string
            current_cost: Current total cost
            current_score: Current total score
            
        Returns:
            dict: {'cost_impact': float, 'score_impact': float, 'new_cost': float, 'new_score': float}
        """
        if depot not in self.V:
            return {'cost_impact': 0, 'score_impact': 0, 'new_cost': current_cost, 'new_score': current_score}
        
        # Get current allocation for this depot
        current_depot_alloc = current_allocation.get(depot, {})
        current_supplier = current_depot_alloc.get('supplier')
        current_operation = current_depot_alloc.get('operation')
        
        if current_supplier is None:
            return {'cost_impact': 0, 'score_impact': 0, 'new_cost': current_cost, 'new_score': current_score}
        
        # Calculate current depot contribution
        current_depot_cost = 0
        current_depot_score = 0
        
        # Current depot cost calculation (same logic as in create_model)
        base_cost = self.DP + self.ZD.get((depot, current_supplier), 0)
        if current_operation == 'collection' and self.valid_collection.get((depot, current_supplier), False):
            coc_val = self.COC.get((depot, current_supplier), 0)
            cost_val = self.COST.get((depot, current_supplier), 0)
            if isinstance(coc_val, (int, float)) and isinstance(cost_val, (int, float)):
                collection_benefit = coc_val - cost_val
                current_depot_cost = self.V[depot] * (base_cost - collection_benefit)
        elif current_operation == 'delivery' and self.valid_delivery.get((depot, current_supplier), False):
            del_val = self.DEL.get((depot, current_supplier), 0)
            if isinstance(del_val, (int, float)):
                delivery_benefit = del_val
                current_depot_cost = self.V[depot] * (base_cost - delivery_benefit)
        else:
            current_depot_cost = self.V[depot] * base_cost
        
        # Current depot score
        if f"Supplier {current_supplier}" in self.S:
            current_depot_score = self.S[f"Supplier {current_supplier}"]
        
        # Calculate new depot contribution
        new_depot_cost = 0
        new_depot_score = 0
        
        # Check if new operation is valid
        if new_operation == 'collection' and not self.valid_collection.get((depot, new_supplier), False):
            return {'cost_impact': 0, 'score_impact': 0, 'new_cost': current_cost, 'new_score': current_score}
        elif new_operation == 'delivery' and not self.valid_delivery.get((depot, new_supplier), False):
            return {'cost_impact': 0, 'score_impact': 0, 'new_cost': current_cost, 'new_score': current_score}
        
        # New depot cost calculation
        base_cost_new = self.DP + self.ZD.get((depot, new_supplier), 0)
        if new_operation == 'collection':
            coc_val = self.COC.get((depot, new_supplier), 0)
            cost_val = self.COST.get((depot, new_supplier), 0)
            if isinstance(coc_val, (int, float)) and isinstance(cost_val, (int, float)):
                collection_benefit = coc_val - cost_val
                new_depot_cost = self.V[depot] * (base_cost_new - collection_benefit)
            else:
                new_depot_cost = self.V[depot] * base_cost_new
        elif new_operation == 'delivery':
            del_val = self.DEL.get((depot, new_supplier), 0)
            if isinstance(del_val, (int, float)):
                delivery_benefit = del_val
                new_depot_cost = self.V[depot] * (base_cost_new - delivery_benefit)
            else:
                new_depot_cost = self.V[depot] * base_cost_new
        
        # New depot score
        if f"Supplier {new_supplier}" in self.S:
            new_depot_score = self.S[f"Supplier {new_supplier}"]
        
        # Calculate impacts
        cost_impact = new_depot_cost - current_depot_cost
        score_impact = new_depot_score - current_depot_score
        
        new_cost = current_cost - current_depot_cost + new_depot_cost
        new_score = current_score - current_depot_score + new_depot_score
        
        return {
            'cost_impact': cost_impact,
            'score_impact': score_impact,
            'new_cost': new_cost,
            'new_score': new_score
        }
    
    def _calculate_ranking_score(self, cost_impact, score_impact, ranking_metric):
        """
        Convert cost/score impacts into single ranking score
        
        Args:
            cost_impact: Cost change (positive = cost increase)
            score_impact: Score change (positive = score increase)
            ranking_metric: "cost_effectiveness", "cost_impact", "score_impact", "combined"
            
        Returns:
            float: Ranking score (higher is better for ranking)
        """
        if ranking_metric == "cost_effectiveness":
            # Score improvement per cost increase (or cost reduction per score decrease)
            if abs(cost_impact) < 1e-10:  # Avoid division by zero
                return score_impact if score_impact > 0 else -1e6
            return score_impact / abs(cost_impact) if cost_impact != 0 else score_impact
        
        elif ranking_metric == "cost_impact":
            # Prefer alternatives that reduce cost most (negative cost_impact is better)
            return -cost_impact  # Negative because we want to minimize cost
        
        elif ranking_metric == "score_impact":
            # Prefer alternatives that increase score most
            return score_impact
        
        elif ranking_metric == "combined":
            # Balanced normalized combination
            # Normalize by typical ranges (these could be made configurable)
            cost_weight = 0.6
            score_weight = 0.4
            
            # Normalize cost impact (assume typical range of ±1e6)
            norm_cost = -cost_impact / 1e6  # Negative because lower cost is better
            
            # Normalize score impact (assume typical range of ±100)
            norm_score = score_impact / 100
            
            return cost_weight * norm_cost + score_weight * norm_score
        
        else:
            raise ValueError(f"Unknown ranking metric: {ranking_metric}")
    
    def _analyze_depot_alternatives(self, depot, current_allocation, current_cost, current_score, ranking_metric):
        """
        For one depot, test all valid alternative suppliers
        
        Args:
            depot: Depot number
            current_allocation: Current allocation dict
            current_cost: Current total cost
            current_score: Current total score
            ranking_metric: Ranking metric to use
            
        Returns:
            list: Ranked alternatives for this depot
        """
        alternatives = []
        
        # Get current allocation for this depot
        current_depot_alloc = current_allocation.get(depot, {})
        current_supplier = current_depot_alloc.get('supplier')
        current_operation = current_depot_alloc.get('operation')
        
        # Test all valid suppliers for this depot
        for supplier in self.suppliers:
            if (depot, supplier) not in self.all_pairs:
                continue
            
            # Test collection operation if valid
            if self.valid_collection.get((depot, supplier), False):
                impact = self._calculate_switch_impact(
                    depot, supplier, 'collection', 
                    current_allocation, current_cost, current_score
                )
                
                if impact['cost_impact'] != 0 or impact['score_impact'] != 0:  # Only include meaningful alternatives
                    ranking_score = self._calculate_ranking_score(
                        impact['cost_impact'], impact['score_impact'], ranking_metric
                    )
                    
                    alternatives.append({
                        'depot': depot,
                        'supplier': supplier,
                        'operation': 'collection',
                        'cost_impact': impact['cost_impact'],
                        'score_impact': impact['score_impact'],
                        'new_cost': impact['new_cost'],
                        'new_score': impact['new_score'],
                        'ranking_score': ranking_score,
                        'is_current': (supplier == current_supplier and current_operation == 'collection')
                    })
            
            # Test delivery operation if valid
            if self.valid_delivery.get((depot, supplier), False):
                impact = self._calculate_switch_impact(
                    depot, supplier, 'delivery', 
                    current_allocation, current_cost, current_score
                )
                
                if impact['cost_impact'] != 0 or impact['score_impact'] != 0:  # Only include meaningful alternatives
                    ranking_score = self._calculate_ranking_score(
                        impact['cost_impact'], impact['score_impact'], ranking_metric
                    )
                    
                    alternatives.append({
                        'depot': depot,
                        'supplier': supplier,
                        'operation': 'delivery',
                        'cost_impact': impact['cost_impact'],
                        'score_impact': impact['score_impact'],
                        'new_cost': impact['new_cost'],
                        'new_score': impact['new_score'],
                        'ranking_score': ranking_score,
                        'is_current': (supplier == current_supplier and current_operation == 'delivery')
                    })
        
        # Sort by ranking score (descending - higher is better)
        alternatives.sort(key=lambda x: x['ranking_score'], reverse=True)
        
        return alternatives
    
    def analyze_supplier_alternatives(self, pareto_solutions_df, ranking_metric="cost_effectiveness"):
        """
        Analyze supplier alternatives for each Pareto solution
        
        Args:
            pareto_solutions_df: DataFrame from optimize_epsilon_constraint()
            ranking_metric: "cost_effectiveness", "cost_impact", "score_impact", "combined"
            
        Returns:
            dict: Detailed ranking analysis for each solution
        """
        print(f"Starting supplier alternatives analysis with ranking metric: {ranking_metric}")
        
        analysis_results = {}
        
        # Filter to only optimal solutions
        df_feasible = pareto_solutions_df[pareto_solutions_df['status'] == 'Optimal'].copy()
        
        if len(df_feasible) == 0:
            print("No feasible solutions found for analysis!")
            return analysis_results
        
        for idx, row in df_feasible.iterrows():
            print(f"Analyzing solution {idx+1}/{len(df_feasible)} (epsilon: {row['epsilon']:.2e})")
            
            allocation_str = row['allocations']
            current_cost = row['cost']
            current_score = row['score']
            
            # Parse current allocation
            current_allocation = self._parse_allocation_string(allocation_str)
            
            if not current_allocation:
                print(f"  Warning: No valid allocation found for solution {idx}")
                continue
            
            # Analyze alternatives for each depot
            solution_analysis = {
                'solution_id': idx,
                'epsilon': row['epsilon'],
                'current_cost': current_cost,
                'current_score': current_score,
                'current_allocation': current_allocation,
                'depot_alternatives': {}
            }
            
            for depot in self.depots:
                if depot in current_allocation:
                    alternatives = self._analyze_depot_alternatives(
                        depot, current_allocation, current_cost, current_score, ranking_metric
                    )
                    solution_analysis['depot_alternatives'][depot] = alternatives
            
            analysis_results[idx] = solution_analysis
        
        print(f"Analysis completed for {len(analysis_results)} solutions")
        return analysis_results
    
    def create_ranking_report(self, analysis_results, save_path="Output Data/"):
        """
        Generate comprehensive text report and CSV files
        
        Args:
            analysis_results: Results from analyze_supplier_alternatives()
            save_path: Directory to save reports
        """
        if not analysis_results:
            print("No analysis results to report!")
            return
        
        os.makedirs(save_path, exist_ok=True)
        
        # Create detailed CSV report
        csv_data = []
        for solution_id, analysis in analysis_results.items():
            for depot, alternatives in analysis['depot_alternatives'].items():
                for i, alt in enumerate(alternatives[:10]):  # Top 10 alternatives per depot
                    csv_data.append({
                        'solution_id': solution_id,
                        'epsilon': analysis['epsilon'],
                        'depot': depot,
                        'rank': i + 1,
                        'supplier': alt['supplier'],
                        'operation': alt['operation'],
                        'cost_impact': alt['cost_impact'],
                        'score_impact': alt['score_impact'],
                        'new_cost': alt['new_cost'],
                        'new_score': alt['new_score'],
                        'ranking_score': alt['ranking_score'],
                        'is_current': alt['is_current']
                    })
        
        # Save CSV
        df_report = pd.DataFrame(csv_data)
        csv_filename = f"{save_path}supplier_ranking_analysis.csv"
        df_report.to_csv(csv_filename, index=False)
        print(f"Detailed CSV report saved to: {csv_filename}")
        
        # Create text report
        report_filename = f"{save_path}supplier_ranking_report.txt"
        with open(report_filename, 'w') as f:
            f.write("="*80 + "\n")
            f.write("SUPPLIER RANKING ANALYSIS REPORT\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Analysis Summary:\n")
            f.write(f"- Total solutions analyzed: {len(analysis_results)}\n")
            f.write(f"- Total depot-supplier alternatives evaluated: {len(csv_data)}\n\n")
            
            for solution_id, analysis in analysis_results.items():
                f.write(f"SOLUTION {solution_id} (Epsilon: {analysis['epsilon']:.2e})\n")
                f.write("-" * 50 + "\n")
                f.write(f"Current Cost: {analysis['current_cost']:,.2f}\n")
                f.write(f"Current Score: {analysis['current_score']:.2f}\n")
                f.write(f"Current Allocation: {analysis['current_allocation']}\n\n")
                
                for depot, alternatives in analysis['depot_alternatives'].items():
                    f.write(f"  DEPOT {depot} - Top 3 Alternatives:\n")
                    for i, alt in enumerate(alternatives[:3]):
                        status = " (CURRENT)" if alt['is_current'] else ""
                        f.write(f"    {i+1}. Supplier {alt['supplier']} ({alt['operation']}){status}\n")
                        f.write(f"       Cost Impact: {alt['cost_impact']:+,.2f}, Score Impact: {alt['score_impact']:+.2f}\n")
                        f.write(f"       New Cost: {alt['new_cost']:,.2f}, New Score: {alt['new_score']:.2f}\n")
                        f.write(f"       Ranking Score: {alt['ranking_score']:.4f}\n")
                    f.write("\n")
                
                f.write("\n" + "="*80 + "\n\n")
        
        print(f"Text report saved to: {report_filename}")
        
        # Create summary statistics
        summary_data = []
        for solution_id, analysis in analysis_results.items():
            for depot, alternatives in analysis['depot_alternatives'].items():
                if alternatives:
                    best_alternative = alternatives[0]
                    summary_data.append({
                        'solution_id': solution_id,
                        'depot': depot,
                        'best_supplier': best_alternative['supplier'],
                        'best_operation': best_alternative['operation'],
                        'best_cost_impact': best_alternative['cost_impact'],
                        'best_score_impact': best_alternative['score_impact'],
                        'best_ranking_score': best_alternative['ranking_score'],
                        'num_alternatives': len(alternatives)
                    })
        
        df_summary = pd.DataFrame(summary_data)
        summary_filename = f"{save_path}supplier_ranking_summary.csv"
        df_summary.to_csv(summary_filename, index=False)
        print(f"Summary report saved to: {summary_filename}")
        
        return {
            'detailed_csv': csv_filename,
            'text_report': report_filename,
            'summary_csv': summary_filename,
            'analysis_results': analysis_results
        }
    
    def run_full_optimization_with_ranking(self, epsilon_range=None, n_points=21, constraint_type="cost", 
                                         ranking_metric="cost_effectiveness", **kwargs):
        """
        Enhanced version of run_full_optimization with ranking analysis
        
        Args:
            epsilon_range: tuple (min, max) or None for auto-detection
            n_points: number of epsilon points to test
            constraint_type: "cost" or "score" - which objective to constrain
            ranking_metric: "cost_effectiveness", "cost_impact", "score_impact", "combined"
            **kwargs: Additional arguments for run_full_optimization
        """
        print("="*80)
        print("ENHANCED E-CONSTRAINT OPTIMIZATION WITH SUPPLIER RANKING ANALYSIS")
        print("="*80)
        
        # Run standard optimization
        df_pareto = self.run_full_optimization(epsilon_range, n_points, constraint_type, **kwargs)
        
        # Perform ranking analysis
        print("\n" + "="*60)
        print("PERFORMING SUPPLIER RANKING ANALYSIS")
        print("="*60)
        
        analysis_results = self.analyze_supplier_alternatives(df_pareto, ranking_metric)
        
        if analysis_results:
            # Create ranking reports
            report_files = self.create_ranking_report(analysis_results)
            
            print("\n" + "="*60)
            print("RANKING ANALYSIS COMPLETED")
            print("="*60)
            print(f"Reports generated:")
            print(f"- Detailed CSV: {report_files['detailed_csv']}")
            print(f"- Text Report: {report_files['text_report']}")
            print(f"- Summary CSV: {report_files['summary_csv']}")
            
            # Store analysis results for potential UI access
            self.last_ranking_analysis = analysis_results
            self.last_ranking_reports = report_files
        
        return df_pareto

    def get_feasible_allocations(self, n_points=10, constraint_type="cost"):
        """
        Run MOO and extract decoded allocation dicts (C, D) for each feasible solution.
        """
        df = self.optimize_epsilon_constraint(n_points=n_points, constraint_type=constraint_type)
        df_feasible = df[df['status'] == 'Optimal'].copy()

        allocations_list = []
        for row in df_feasible.itertuples():
            allocation_str = getattr(row, "allocations")
            C = {}
            D = {}
            for item in allocation_str.split():
                if item.startswith("C("):
                    i, j = map(int, item[2:-1].split(','))
                    C[(i, j)] = 1
                elif item.startswith("D("):
                    i, j = map(int, item[2:-1].split(','))
                    D[(i, j)] = 1
            allocations_list.append({"C": C, "D": D})
        
        return allocations_list


# # Usage example
# if __name__ == "__main__":
#     # Example file path - update this to match your file
#     file_path = r"C:\Users\blake\OneDrive - Stellenbosch University\SUN 2\2025\Skripsie\Demo Data\Demo3.xlsx"
    
#     try:
#         # Initialize optimizer with selective NA handling
#         optimizer = SelectiveNAFlexibleEConstraintOptimizer(file_path)
        
#         # Run optimization with cost constraint (like original)
#         print("Running with COST constraint (maximize score, limit cost) with selective NA handling:")
#         results_cost = optimizer.run_full_optimization(
#             n_points=21,
#             constraint_type="cost"
#         )
        
#         print("\n" + "="*60 + "\n")
        
#         # Run optimization with score constraint (alternative approach)
#         print("Running with SCORE constraint (minimize cost, require minimum score) with selective NA handling:")
#         results_score = optimizer.run_full_optimization(
#             n_points=21,
#             constraint_type="score"
#         )
        
#         print("\nSelective NA handling e-constraint optimization completed successfully!")
        
#     except Exception as e:
#         print(f"Error during optimization: {e}")
#         import traceback
#         traceback.print_exc()