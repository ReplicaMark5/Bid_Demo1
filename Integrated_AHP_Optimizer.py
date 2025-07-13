import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import requests
import importlib
MOO_e_constraint = importlib.import_module("MOO_e_constraint_Dynamic_Bid")
SelectiveNAFlexibleEConstraintOptimizer = MOO_e_constraint.SelectiveNAFlexibleEConstraintOptimizer
import random
from scipy.spatial.distance import cdist

def generate_supplier_ranking(allocations_str, optimizer_instance):
    """
    Generate supplier ranking for each depot based on the selected solution.
    
    Args:
        allocations_str: String containing allocations like "C(1,2) D(3,1)"
        optimizer_instance: The optimizer instance with cost and score data
    
    Returns:
        dict: Depot -> list of suppliers ranked by cost (lowest to highest)
    """
    if not allocations_str or allocations_str.lower() in ["no solution", "none", ""]:
        return {}
    
    # Parse allocations
    allocations = allocations_str.split()
    depot_allocations = {}
    
    for alloc in allocations:
        if '(' in alloc and ')' in alloc:
            operation = alloc[0]
            params = alloc[2:-1]
            if ',' in params:
                depot, supplier = params.split(',')
                depot = int(depot)
                supplier = int(supplier)
                
                if depot not in depot_allocations:
                    depot_allocations[depot] = []
                depot_allocations[depot].append({
                    'supplier': supplier,
                    'operation': operation,
                    'score': optimizer_instance.S.get(f"Supplier {supplier}", 0)
                })
    
    # Generate ranking for each depot
    depot_rankings = {}
    for depot in optimizer_instance.depots:
        if depot in depot_allocations:
            # Get the selected supplier for this depot
            selected_suppliers = depot_allocations[depot]
            
            # Get all available suppliers for this depot with their costs
            available_suppliers = []
            for supplier in optimizer_instance.suppliers:
                # Check if this supplier is available for this depot
                if (depot, supplier) in optimizer_instance.all_pairs:
                    score = optimizer_instance.S.get(f"Supplier {supplier}", 0)
                    is_selected = any(s['supplier'] == supplier for s in selected_suppliers)
                    
                    # Calculate cost for this depot-supplier pair
                    base_cost = optimizer_instance.DP + optimizer_instance.ZD.get((depot, supplier), 0)
                    
                    # Calculate cost reductions for valid operations
                    collection_reduction = 0
                    delivery_reduction = 0
                    
                    # Collection cost reduction (if valid)
                    if optimizer_instance.valid_collection.get((depot, supplier), False):
                        coc_val = optimizer_instance.COC.get((depot, supplier), 0)
                        cost_val = optimizer_instance.COST.get((depot, supplier), 0)
                        if isinstance(coc_val, (int, float)) and isinstance(cost_val, (int, float)):
                            collection_reduction = coc_val - cost_val
                    
                    # Delivery cost reduction (if valid)
                    if optimizer_instance.valid_delivery.get((depot, supplier), False):
                        del_val = optimizer_instance.DEL.get((depot, supplier), 0)
                        if isinstance(del_val, (int, float)):
                            delivery_reduction = del_val
                    
                    # Calculate total cost (base cost minus best possible reduction)
                    total_cost = base_cost - max(collection_reduction, delivery_reduction)
                    
                    available_suppliers.append({
                        'supplier': supplier,
                        'score': score,
                        'cost': total_cost,
                        'is_selected': is_selected,
                        'operation': next((s['operation'] for s in selected_suppliers if s['supplier'] == supplier), None)
                    })
            
            # Sort by cost (ascending - lowest cost first) and add ranking
            available_suppliers.sort(key=lambda x: x['cost'])
            for i, supplier_info in enumerate(available_suppliers):
                supplier_info['rank'] = i + 1
            
            depot_rankings[depot] = available_suppliers
    
    return depot_rankings

# Configure page
st.set_page_config(
    page_title="Integrated AHP & Supply Chain Optimizer",
    page_icon="🏭",
    layout="wide"
)

# Initialize session state
if 'current_phase' not in st.session_state:
    st.session_state.current_phase = "ahp_scoring"
if 'ahp_results' not in st.session_state:
    st.session_state.ahp_results = None
if 'file_path' not in st.session_state:
    st.session_state.file_path = r"C:\Users\blake\OneDrive - Stellenbosch University\SUN 2\2025\Skripsie\Demo Data\Demo3.xlsx"

# GitHub AI integration for AHP scoring
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
endpoint = "https://models.github.ai/inference"
model_name = "openai/gpt-4o"

def get_ai_score(description, criterion):
    """Get AI-generated score for supplier evaluation"""
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

    response = requests.post(f"{endpoint}/v1/chat/completions", json=payload, headers=headers)

    if response.status_code == 200:
        reply = response.json()
        content = reply['choices'][0]['message']['content']
        digits = [int(s) for s in content if s.isdigit()]
        return min(max(digits[0], 1), 9) if digits else 5
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return 5

def main():
    """Main application with unified interface"""
    
    # Main title and navigation
    st.title("🏭 Integrated AHP & Supply Chain Optimizer")
    st.markdown("*Seamlessly evaluate suppliers and optimize supply chains*")
    
    # Phase indicator
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.current_phase == "ahp_scoring":
            st.success("📊 Phase 1: AHP Supplier Scoring")
        else:
            st.success("🚀 Phase 2: Supply Chain Optimization")
    
    # Navigation tabs
    tab1, tab2 = st.tabs(["🧮 AHP Supplier Scoring", "🏭 Supply Chain Optimization"])
    
    with tab1:
        ahp_scoring_interface()
    
    with tab2:
        optimization_interface()

def ahp_scoring_interface():
    """AHP Supplier Scoring Interface"""
    
    st.header("🧮 AHP Supplier Scoring")
    st.markdown("*Evaluate suppliers using AHP methodology with AI-assisted scoring*")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🔧 AHP Configuration")
        num_criteria = st.number_input("Number of Criteria", min_value=1, max_value=10, value=3)
        num_suppliers = st.number_input("Number of Suppliers", min_value=1, max_value=10, value=3)
        
        st.divider()
        
        # Show AHP results if available
        if st.session_state.ahp_results:
            st.success("✅ AHP Scores Calculated")
            st.markdown("**Supplier Rankings:**")
            for i, (supplier, score) in enumerate(zip(st.session_state.ahp_results['suppliers'], 
                                                    st.session_state.ahp_results['scores'])):
                st.markdown(f"{i+1}. {supplier}: {score:.2f}")
    
    # Step 1: Input Criteria Names
    st.subheader("Step 1: Define Supplier Selection Criteria")
    criteria_names = []
    col1, col2 = st.columns(2)
    for i in range(num_criteria):
        with col1 if i % 2 == 0 else col2:
            name = st.text_input(f"Criteria {i+1} name", key=f"crit_{i}")
            criteria_names.append(name if name else f"Criteria {i+1}")

    # Step 2: Input Criteria Weights
    st.subheader("Step 2: Assign Criteria Weights (Relative Importance)")
    criteria_weights = []
    col1, col2 = st.columns(2)
    for i, crit in enumerate(criteria_names):
        with col1 if i % 2 == 0 else col2:
            weight = st.number_input(f"Weight for '{crit}'", min_value=0.0, value=1.0, step=0.1, key=f"w_{i}")
            criteria_weights.append(weight)

    # Normalize weights
    weight_sum = sum(criteria_weights)
    normalized_weights = [w / weight_sum for w in criteria_weights]

    # Step 3: Input Supplier Names and Scores
    st.subheader("Step 3: Enter Supplier Scores per Criterion")
    supplier_names = []
    scores_matrix = []

    for s in range(num_suppliers):
        st.markdown(f"**Supplier {s+1}**")
        supplier_name = st.text_input(f"Name of Supplier {s+1}", key=f"supp_{s}")
        supplier_names.append(supplier_name if supplier_name else f"Supplier {s+1}")
        scores = []
        cols = st.columns(len(criteria_names))
        for i, crit in enumerate(criteria_names):
            with cols[i]:
                desc = st.text_input(f"Describe {crit} for {supplier_name}", key=f"desc_{s}_{i}")
                if desc:
                    score = get_ai_score(desc, crit)
                    st.write(f"AI Score: {score}")
                else:
                    score = 5  # default neutral score
                scores.append(score)
        scores_matrix.append(scores)

    # Step 4: Calculate Final Scores
    if st.button("🔍 Calculate AHP Supplier Scores", key="calculate_ahp", type="primary"):
        st.subheader("📊 Results: AHP Weighted Supplier Scores")
        weighted_scores = np.dot(scores_matrix, normalized_weights)
        
        results_df = pd.DataFrame({
            "Supplier": supplier_names,
            "AHP Score": weighted_scores
        }).sort_values(by="AHP Score", ascending=False).reset_index(drop=True)

        st.dataframe(results_df, use_container_width=True)
        
        # Store results in session state
        st.session_state.ahp_results = {
            'suppliers': supplier_names,
            'scores': weighted_scores.tolist(),
            'criteria': criteria_names,
            'weights': normalized_weights,
            'scores_matrix': scores_matrix
        }
        
        # Show criteria weights summary
        st.subheader("📋 Criteria Weights Summary")
        weights_df = pd.DataFrame({
            "Criteria": criteria_names,
            "Weight": normalized_weights
        })
        st.dataframe(weights_df, use_container_width=True)
        
        # Visualization
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Supplier Scores Comparison")
            fig_scores = px.bar(results_df, x='Supplier', y='AHP Score', 
                               title="AHP Supplier Scores",
                               color='AHP Score', color_continuous_scale='viridis')
            st.plotly_chart(fig_scores, use_container_width=True)
        
        with col2:
            st.subheader("🎯 Criteria Weights Distribution")
            fig_weights = px.pie(weights_df, values='Weight', names='Criteria',
                                title="Criteria Weight Distribution")
            st.plotly_chart(fig_weights, use_container_width=True)
        
        st.success("✅ AHP scoring completed! You can now proceed to the Supply Chain Optimization tab.")

def optimization_interface():
    """Supply Chain Optimization Interface"""
    
    st.header("🏭 Supply Chain Optimizer")
    st.markdown("*Multi-objective optimization using ε-Constraint method with selective NA handling*")
    
    # Show AHP results summary if available
    if st.session_state.ahp_results:
        st.subheader("📊 AHP Results Summary")
        ahp_df = pd.DataFrame({
            "Supplier": st.session_state.ahp_results['suppliers'],
            "AHP Score": st.session_state.ahp_results['scores']
        }).sort_values(by="AHP Score", ascending=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(ahp_df, use_container_width=True)
        with col2:
            fig_ahp = px.bar(ahp_df, x='Supplier', y='AHP Score', 
                            title="AHP Supplier Rankings")
            st.plotly_chart(fig_ahp, use_container_width=True)
    else:
        st.info("💡 Complete the AHP scoring first to see supplier rankings here.")
    
    # Sidebar controls
    with st.sidebar:
        st.header("📁 Data Configuration")
        
        # File path input
        file_path = st.text_input(
            "Excel File Path", 
            value=st.session_state.file_path,
            help="Path to your Excel file containing optimization data"
        )
        st.session_state.file_path = file_path
        
        # Sheet name configuration
        st.subheader("📋 Sheet Names")
        obj1_sheet = st.text_input("Objective 1 Coefficients", value="Obj1_Coeff")
        obj2_sheet = st.text_input("Objective 2 Coefficients", value="Obj2_Coeff") 
        volumes_sheet = st.text_input("Annual Volumes", value="Annual Volumes")
        
        sheet_names = {
            'obj1': obj1_sheet,
            'obj2': obj2_sheet,
            'volumes': volumes_sheet
        }
        
        st.divider()
        
        st.header("⚙️ ε-Constraint Parameters")
        n_points = st.slider("Number of Epsilon Points", 5, 400, 21, help="Number of points to test in the Pareto front")
        constraint_type = st.selectbox("Constraint Type", ["cost", "score"], help="Which objective to constrain")

        # Add ranking analysis options
        st.divider()
        st.header("🔍 Supplier Ranking Analysis")
        
        enable_ranking = st.checkbox("Enable Supplier Ranking Analysis", value=True, 
                                   help="Analyze alternative suppliers for each Pareto solution")
        
        if enable_ranking:
            ranking_metric = st.selectbox(
                "Ranking Metric",
                ["cost_effectiveness", "cost_impact", "score_impact", "combined"],
                help="How to rank alternative suppliers"
            )
            
            st.markdown("**Ranking Metrics:**")
            st.markdown("- **cost_effectiveness**: Score improvement per cost increase")
            st.markdown("- **cost_impact**: Prefer alternatives that reduce cost most")
            st.markdown("- **score_impact**: Prefer alternatives that increase score most")
            st.markdown("- **combined**: Balanced normalized combination")
            
            show_ranking_in_ui = st.checkbox("Show Ranking Analysis in UI", value=True,
                                           help="Display ranking analysis in the solution details")

        random_seed = st.number_input("Random Seed", value=42, help="For reproducible results")
        
        st.divider()
        
        st.header("📋 Instructions")
        st.markdown("""
        1. Configure data file path and sheet names
        2. Adjust ε-constraint parameters
        3. Configure ranking analysis options (optional)
        4. Click **Initialize & Analyze Data**
        5. Click **Run Optimization**
        6. **Click any point** on the Pareto front to view details
        """)
        
        # Initialize optimizer button
        if st.button("🔍 Initialize & Analyze Data", type="secondary"):
            if os.path.exists(file_path):
                try:
                    with st.spinner("Loading and analyzing data..."):
                        # Set random seeds
                        random.seed(random_seed)
                        np.random.seed(random_seed)
                        
                        econst_optimizer = SelectiveNAFlexibleEConstraintOptimizer(file_path, sheet_names)
                        st.session_state.econst_optimizer = econst_optimizer
                        st.session_state.optimizer_instance = econst_optimizer
                        st.session_state.data_loaded = True
                        
                    st.success("✅ Data loaded and analyzed successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error loading data: {str(e)}")
            else:
                st.error("❌ File path does not exist!")

    # Main optimization content
    if st.session_state.get('data_loaded', False):
        optimizer = st.session_state.optimizer_instance
        
        # Display data analysis
        st.subheader("📊 Data Analysis")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏭 Depots", len(optimizer.depots))
        with col2:
            st.metric("🚛 Suppliers", len(optimizer.suppliers))
        with col3:
            st.metric("🔗 Total Pairs", len(optimizer.all_pairs))

        # Show depot-supplier availability
        with st.expander("🔍 Depot-Supplier Availability Analysis", expanded=False):
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
                            "🏭 Depot": depot,
                            "🏢 Supplier": supplier,
                            "Available Operations": ", ".join(operations) if operations else "None",
                            "Collection": "✅" if collection_valid else "❌",
                            "Delivery": "✅" if delivery_valid else "❌"
                        })
            
            availability_df = pd.DataFrame(availability_data)
            st.dataframe(availability_df, use_container_width=True)
            
            # Summary statistics
            total_pairs = len(availability_data)
            collection_available = sum(1 for row in availability_data if "Collection" in row["Available Operations"])
            delivery_available = sum(1 for row in availability_data if "Delivery" in row["Available Operations"])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pairs", total_pairs)
            with col2:
                st.metric("Collection Available", f"{collection_available} ({collection_available/total_pairs*100:.1f}%)")
            with col3:
                st.metric("Delivery Available", f"{delivery_available} ({delivery_available/total_pairs*100:.1f}%)")

        # Run optimization only if optimizer is initialized
        if st.button("🚀 Run Optimization", type="primary"):
            try:
                with st.spinner("Running ε-constraint optimization..."):
                    if 'econst_optimizer' in st.session_state:
                        econst_optimizer = st.session_state.econst_optimizer
                        
                        # Check if ranking analysis is enabled
                        if enable_ranking:
                            # Use enhanced optimization with ranking
                            df_econst = econst_optimizer.run_full_optimization_with_ranking(
                                n_points=n_points,
                                constraint_type=constraint_type,
                                ranking_metric=ranking_metric
                            )
                            # Store ranking analysis results
                            st.session_state.ranking_analysis = getattr(econst_optimizer, 'last_ranking_analysis', {})
                            st.session_state.ranking_reports = getattr(econst_optimizer, 'last_ranking_reports', {})
                        else:
                            # Use standard optimization
                            df_econst = econst_optimizer.optimize_epsilon_constraint(
                                n_points=n_points,
                                constraint_type=constraint_type
                            )
                        
                        df_econst = df_econst[df_econst['status'] == 'Optimal']
                        df_econst['method'] = 'ε-Constraint'
                        st.session_state.df_econst = df_econst
                        st.session_state.ranking_enabled = enable_ranking
                        st.session_state.show_ranking_in_ui = show_ranking_in_ui if enable_ranking else False
                    else:
                        st.error("❌ ε-Constraint optimizer not initialized. Please click 'Initialize & Analyze Data' first.")
                    
                    st.success("✅ Optimization completed!")
                    st.rerun()
                
            except Exception as e:
                st.error(f"❌ Optimization failed: {str(e)}")
                st.exception(e)

    # Results section
    if 'df_econst' in st.session_state:
        df_econst = st.session_state.get('df_econst', pd.DataFrame())
        
        if not df_econst.empty:
            st.divider()
            
            # Show ranking analysis status
            if st.session_state.get('ranking_enabled', False):
                st.success("🔍 Supplier Ranking Analysis: ENABLED")
                if 'ranking_reports' in st.session_state and st.session_state.ranking_reports:
                    reports = st.session_state.ranking_reports
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.download_button(
                            label="📥 Download Detailed Analysis",
                            data=open(reports['detailed_csv'], 'r').read(),
                            file_name="supplier_ranking_analysis.csv",
                            mime="text/csv"
                        )
                    with col2:
                        st.download_button(
                            label="📥 Download Summary",
                            data=open(reports['summary_csv'], 'r').read(),
                            file_name="supplier_ranking_summary.csv",
                            mime="text/csv"
                        )
                    with col3:
                        st.download_button(
                            label="📥 Download Text Report",
                            data=open(reports['text_report'], 'r').read(),
                            file_name="supplier_ranking_report.txt",
                            mime="text/plain"
                        )
            
            # Create two columns for the main display
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("📈 Interactive Pareto Front")
                
                # Create the interactive plot
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_econst["cost"],
                    y=df_econst["score"],
                    mode='markers',
                    name='ε-Constraint',
                    marker=dict(color='red', size=10),
                    text=df_econst.index,
                    customdata=df_econst.index,
                    hovertemplate=
                    '<b>ε-Constraint Solution %{text}</b><br>' +
                    'Cost: R%{x:,.0f}<br>' +
                    'Score: %{y:.2f}<br>' +
                    '<b>👆 Click to see details</b><br>' +
                    '<extra></extra>'
                ))
                
                fig.update_layout(
                    title="Pareto Front: ε-Constraint Optimization",
                    xaxis_title="Total Cost (R)",
                    yaxis_title="Supplier Score",
                    legend_title="Method",
                    hovermode='closest',
                    height=500
                )
                
                # Display the plot and capture click events
                clicked_data = st.plotly_chart(fig, use_container_width=True, key="pareto_plot", on_select="rerun")
                
                # Handle click events
                if clicked_data and 'selection' in clicked_data and clicked_data['selection']['points']:
                    clicked_point = clicked_data['selection']['points'][0]
                    selected_idx = clicked_point['customdata']
                    st.session_state.selected_solution = selected_idx
                    st.session_state.selected_method = 'ε-Constraint'
            
            with col2:
                st.subheader("📊 Solution Overview")
                
                st.metric("ε-Constraint Solutions", len(df_econst))
                
                # Distribution chart
                st.markdown("**📈 Cost Distribution:**")
                fig_dist = go.Figure()
                fig_dist.add_trace(go.Histogram(
                    x=df_econst['cost'],
                    name='ε-Constraint',
                    opacity=0.7,
                    marker_color='red'
                ))
                fig_dist.update_layout(
                    title="Cost Distribution",
                    xaxis_title="Cost",
                    yaxis_title="Frequency",
                    height=200
                )
                st.plotly_chart(fig_dist, use_container_width=True)
            
            # Display selected solution details
            if 'selected_solution' in st.session_state and st.session_state.selected_solution is not None:
                selected_idx = st.session_state.selected_solution
                selected_method = st.session_state.selected_method
                solution = df_econst.iloc[selected_idx]
                
                with st.expander(f"🔍 **{selected_method} Solution {selected_idx} Details**", expanded=True):
                    col_header1, col_header2 = st.columns(2)
                    with col_header1:
                        st.metric("💰 Total Cost", f"{solution['cost']:,.0f}")
                    with col_header2:
                        st.metric("⭐ Score", f"{solution['score']:.2f}")
                    
                    st.divider()
                    
                    # Safely get and validate allocations
                    allocations_str = solution.get("allocations", "").strip()
                    if allocations_str.lower() in ["no solution", "none", ""]:
                        st.warning("⚠️ No allocation data available for this solution.")
                        st.stop()
                    
                    allocations = allocations_str.split()

                    # Generate supplier rankings using the new analysis system if available
                    optimizer = st.session_state.optimizer_instance
                    
                    # Check if we have ranking analysis for this solution
                    ranking_analysis = st.session_state.get('ranking_analysis', {})
                    current_solution_analysis = ranking_analysis.get(selected_idx, {})
                    
                    # Create tabs for different views
                    tab_names = ["🏭 Allocations", "🏆 Supplier Rankings", "📊 Summary"]
                    if current_solution_analysis and st.session_state.get('show_ranking_in_ui', False):
                        tab_names.append("🔍 Advanced Ranking Analysis")
                    
                    tabs = st.tabs(tab_names)
                    
                    with tabs[0]:  # Allocations tab
                        col_detail1, col_detail2 = st.columns([1, 1])
                        
                        with col_detail1:
                            st.markdown("**🏭 Detailed Allocations:**")
                            
                            if allocations and allocations_str:
                                allocations_data = []
                                for alloc in allocations:
                                    if '(' in alloc and ')' in alloc:
                                        operation = alloc[0]
                                        params = alloc[2:-1]
                                        if ',' in params:
                                            depot, supplier = params.split(',')
                                            allocations_data.append({
                                                "🏭 Depot": f"Depot {depot}",
                                                "🏢 Supplier": f"Supplier {supplier}",
                                                "📋 Operation": "Collection" if operation == 'C' else "Delivery",
                                                "🔧 Code": alloc
                                            })
                                
                                if allocations_data:
                                    allocation_df = pd.DataFrame(allocations_data)
                                    st.dataframe(allocation_df, use_container_width=True, hide_index=True)
                                else:
                                    st.info("No valid allocations parsed")
                            else:
                                st.info("No allocations found for this solution")
                        
                        with col_detail2:
                            st.markdown("**📈 Allocation Summary:**")
                            
                            if allocations and allocations_str:
                                supplier_operations = {}
                                operation_counts = {"Collection": 0, "Delivery": 0}
                                
                                for alloc in allocations:
                                    if '(' in alloc and ')' in alloc:
                                        operation = alloc[0]
                                        params = alloc[2:-1]
                                        if ',' in params:
                                            depot, supplier = params.split(',')
                                            supplier_key = f"Supplier {supplier}"
                                            
                                            if supplier_key not in supplier_operations:
                                                supplier_operations[supplier_key] = {"Collection": 0, "Delivery": 0}
                                            
                                            if operation == 'C':
                                                supplier_operations[supplier_key]["Collection"] += 1
                                                operation_counts["Collection"] += 1
                                            elif operation == 'D':
                                                supplier_operations[supplier_key]["Delivery"] += 1
                                                operation_counts["Delivery"] += 1
                                
                                for supplier_id, operations in supplier_operations.items():
                                    total_ops = operations['Collection'] + operations['Delivery']
                                    if total_ops > 0:
                                        st.markdown(f"**{supplier_id}:** {total_ops} operations")
                                        if operations['Collection'] > 0:
                                            st.markdown(f"  - Collection: {operations['Collection']}")
                                        if operations['Delivery'] > 0:
                                            st.markdown(f"  - Delivery: {operations['Delivery']}")
                                
                                st.markdown("---")
                                st.markdown(f"**Total Operations:** {sum(operation_counts.values())}")
                            else:
                                st.info("No allocation summary available")
                    
                    with tabs[1]:  # Supplier Rankings tab
                        st.markdown("**🏆 Supplier Rankings by Depot**")
                        st.markdown("*Suppliers ranked by cost (lowest to highest). Selected suppliers are highlighted.*")
                        
                        # Use the new ranking analysis if available, otherwise fall back to the old method
                        if current_solution_analysis and st.session_state.get('show_ranking_in_ui', False):
                            # Use the new ranking analysis
                            for depot in sorted(current_solution_analysis.get('depot_alternatives', {}).keys()):
                                with st.expander(f"🏭 Depot {depot} Rankings", expanded=True):
                                    alternatives = current_solution_analysis['depot_alternatives'][depot]
                                    
                                    # Create ranking table
                                    ranking_data = []
                                    for i, alt in enumerate(alternatives[:10]):  # Show top 10
                                        rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
                                        status = "✅ SELECTED" if alt['is_current'] else ""
                                        operation = f"({alt['operation']})"
                                        
                                        ranking_data.append({
                                            "🏆 Rank": rank_emoji,
                                            "🏢 Supplier": f"Supplier {alt['supplier']}",
                                            "💰 Cost Impact": f"R{alt['cost_impact']:+,.0f}",
                                            "⭐ Score Impact": f"{alt['score_impact']:+.2f}",
                                            "📊 New Cost": f"R{alt['new_cost']:,.0f}",
                                            "📈 New Score": f"{alt['new_score']:.2f}",
                                            "📋 Status": f"{status} {operation}".strip()
                                        })
                                    
                                    ranking_df = pd.DataFrame(ranking_data)
                                    st.dataframe(ranking_df, use_container_width=True, hide_index=True)
                                    
                                    # Show why this supplier was selected
                                    current_alt = next((alt for alt in alternatives if alt['is_current']), None)
                                    if current_alt:
                                        st.markdown(f"**Why Supplier {current_alt['supplier']} was selected:**")
                                        if current_alt['ranking_score'] == alternatives[0]['ranking_score']:
                                            st.success(f"✅ **Best Ranked**: Supplier {current_alt['supplier']} has the best ranking score ({current_alt['ranking_score']:.4f}) for Depot {depot}")
                                        else:
                                            best_alt = alternatives[0]
                                            st.info(f"📊 **Trade-off Decision**: Supplier {current_alt['supplier']} (rank {alternatives.index(current_alt)+1}) was chosen over Supplier {best_alt['supplier']} (rank 1) to optimize overall cost-score balance")
                        else:
                            # Fall back to the old method
                            depot_rankings = generate_supplier_ranking(allocations_str, optimizer)
                            
                            if depot_rankings:
                                for depot in sorted(depot_rankings.keys()):
                                    with st.expander(f"🏭 Depot {depot} Rankings", expanded=True):
                                        suppliers = depot_rankings[depot]
                                        
                                        # Create ranking table
                                        ranking_data = []
                                        for supplier_info in suppliers:
                                            rank_emoji = "🥇" if supplier_info['rank'] == 1 else "🥈" if supplier_info['rank'] == 2 else "🥉" if supplier_info['rank'] == 3 else f"#{supplier_info['rank']}"
                                            status = "✅ SELECTED" if supplier_info['is_selected'] else ""
                                            operation = f"({supplier_info['operation']})" if supplier_info['operation'] else ""
                                            
                                            ranking_data.append({
                                                "🏆 Rank": rank_emoji,
                                                "🏢 Supplier": f"Supplier {supplier_info['supplier']}",
                                                "💰 Cost": f"R{supplier_info['cost']:.2f}",
                                                "⭐ Score": f"{supplier_info['score']:.2f}",
                                                "📋 Status": f"{status} {operation}".strip()
                                            })
                                        
                                        ranking_df = pd.DataFrame(ranking_data)
                                        st.dataframe(ranking_df, use_container_width=True, hide_index=True)
                                        
                                        # Show why this supplier was selected
                                        selected_supplier = next((s for s in suppliers if s['is_selected']), None)
                                        if selected_supplier:
                                            st.markdown(f"**Why Supplier {selected_supplier['supplier']} was selected:**")
                                            if selected_supplier['rank'] == 1:
                                                st.success(f"✅ **Lowest Cost**: Supplier {selected_supplier['supplier']} has the lowest cost (R{selected_supplier['cost']:.2f}) for Depot {depot}")
                                            else:
                                                # Find the best supplier
                                                best_supplier = suppliers[0]
                                                st.info(f"📊 **Trade-off Decision**: Supplier {selected_supplier['supplier']} (cost: R{selected_supplier['cost']:.2f}) was chosen over Supplier {best_supplier['supplier']} (lowest cost: R{best_supplier['cost']:.2f}) to optimize overall cost-score balance")
                            else:
                                st.info("No supplier rankings available for this solution")
                    
                    with tabs[2]:  # Summary tab
                        st.markdown("**📊 Solution Analysis**")
                        
                        # Summary statistics
                        col_sum1, col_sum2, col_sum3 = st.columns(3)
                        
                        with col_sum1:
                            if current_solution_analysis and st.session_state.get('show_ranking_in_ui', False):
                                total_depots = len(current_solution_analysis.get('depot_alternatives', {}))
                                current_rank_1 = sum(1 for depot, alts in current_solution_analysis.get('depot_alternatives', {}).items() 
                                                   if alts and alts[0]['is_current'])
                                st.metric("🏭 Total Depots", total_depots)
                                st.metric("🥇 Best Ranked Selected", f"{current_rank_1}/{total_depots}")
                            else:
                                depot_rankings = generate_supplier_ranking(allocations_str, optimizer)
                                if depot_rankings:
                                    total_depots = len(depot_rankings)
                                    selected_best_ranked = sum(1 for depot, suppliers in depot_rankings.items() 
                                                             if any(s['is_selected'] and s['rank'] == 1 for s in suppliers))
                                    st.metric("🏭 Total Depots", total_depots)
                                    st.metric("🥇 Lowest Cost Selected", f"{selected_best_ranked}/{total_depots}")
                        
                        with col_sum2:
                            if allocations and allocations_str:
                                collection_count = sum(1 for alloc in allocations if alloc.startswith('C'))
                                delivery_count = sum(1 for alloc in allocations if alloc.startswith('D'))
                                st.metric("📦 Collection Operations", collection_count)
                                st.metric("🚚 Delivery Operations", delivery_count)
                        
                        with col_sum3:
                            if current_solution_analysis and st.session_state.get('show_ranking_in_ui', False):
                                depot_alternatives = current_solution_analysis.get('depot_alternatives', {})
                                if depot_alternatives:
                                    current_ranks = []
                                    for depot, alts in depot_alternatives.items():
                                        current_alt = next((alt for alt in alts if alt['is_current']), None)
                                        if current_alt:
                                            current_ranks.append(alts.index(current_alt) + 1)
                                    if current_ranks:
                                        avg_rank = np.mean(current_ranks)
                                        st.metric("📊 Average Rank", f"{avg_rank:.1f}")
                            else:
                                depot_rankings = generate_supplier_ranking(allocations_str, optimizer)
                                if depot_rankings:
                                    avg_rank = np.mean([next(s['rank'] for s in suppliers if s['is_selected']) 
                                                      for suppliers in depot_rankings.values()])
                                    st.metric("📊 Average Cost Rank", f"{avg_rank:.1f}")
                        
                        # Visual summary
                        st.markdown("**📈 Cost Efficiency Analysis:**")
                        
                        if current_solution_analysis and st.session_state.get('show_ranking_in_ui', False):
                            # Create bar chart of selected supplier ranks using new analysis
                            depot_names = []
                            selected_ranks = []
                            
                            for depot in sorted(current_solution_analysis.get('depot_alternatives', {}).keys()):
                                alternatives = current_solution_analysis['depot_alternatives'][depot]
                                current_alt = next((alt for alt in alternatives if alt['is_current']), None)
                                if current_alt:
                                    depot_names.append(f"Depot {depot}")
                                    selected_ranks.append(alternatives.index(current_alt) + 1)
                            
                            if depot_names and selected_ranks:
                                fig_ranks = go.Figure(data=[
                                    go.Bar(
                                        x=depot_names,
                                        y=selected_ranks,
                                        marker_color=['green' if rank == 1 else 'orange' if rank == 2 else 'red' for rank in selected_ranks],
                                        text=[f"Rank {rank}" for rank in selected_ranks],
                                        textposition='auto'
                                    )
                                ])
                                fig_ranks.update_layout(
                                    title="Selected Supplier Ranks by Depot",
                                    xaxis_title="Depot",
                                    yaxis_title="Rank (1 = Best Ranked)",
                                    yaxis=dict(autorange='reversed'),  # Lower rank is better
                                    height=400
                                )
                                st.plotly_chart(fig_ranks, use_container_width=True)
                        else:
                            # Use old method for visualization
                            depot_rankings = generate_supplier_ranking(allocations_str, optimizer)
                            if depot_rankings:
                                # Create bar chart of selected supplier ranks
                                depot_names = [f"Depot {depot}" for depot in sorted(depot_rankings.keys())]
                                selected_ranks = [next(s['rank'] for s in suppliers if s['is_selected']) 
                                                for suppliers in depot_rankings.values()]
                                
                                fig_ranks = go.Figure(data=[
                                    go.Bar(
                                        x=depot_names,
                                        y=selected_ranks,
                                        marker_color=['green' if rank == 1 else 'orange' if rank == 2 else 'red' for rank in selected_ranks],
                                        text=[f"Rank {rank}" for rank in selected_ranks],
                                        textposition='auto'
                                    )
                                ])
                                fig_ranks.update_layout(
                                    title="Selected Supplier Cost Ranks by Depot",
                                    xaxis_title="Depot",
                                    yaxis_title="Cost Rank (1 = Lowest Cost)",
                                    yaxis=dict(autorange='reversed'),  # Lower rank is better
                                    height=400
                                )
                                st.plotly_chart(fig_ranks, use_container_width=True)
                    
                    # Add Advanced Ranking Analysis tab if available
                    if len(tabs) > 3 and current_solution_analysis and st.session_state.get('show_ranking_in_ui', False):
                        with tabs[3]:  # Advanced Ranking Analysis tab
                            st.markdown("**🔍 Advanced Supplier Ranking Analysis**")
                            st.markdown("*Detailed analysis of alternative suppliers with impact calculations*")
                            
                            # Show ranking metric used
                            st.info(f"**Ranking Metric Used**: {ranking_metric}")
                            
                            # Create comprehensive analysis table
                            all_alternatives = []
                            for depot, alternatives in current_solution_analysis.get('depot_alternatives', {}).items():
                                for alt in alternatives[:5]:  # Top 5 per depot
                                    all_alternatives.append({
                                        'Depot': depot,
                                        'Supplier': alt['supplier'],
                                        'Operation': alt['operation'],
                                        'Cost Impact': alt['cost_impact'],
                                        'Score Impact': alt['score_impact'],
                                        'New Cost': alt['new_cost'],
                                        'New Score': alt['new_score'],
                                        'Ranking Score': alt['ranking_score'],
                                        'Is Current': alt['is_current']
                                    })
                            
                            if all_alternatives:
                                df_analysis = pd.DataFrame(all_alternatives)
                                st.dataframe(df_analysis, use_container_width=True)
                                
                                # Show summary statistics
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    total_alternatives = len(all_alternatives)
                                    st.metric("Total Alternatives", total_alternatives)
                                with col2:
                                    cost_reductions = sum(1 for alt in all_alternatives if alt['Cost Impact'] < 0)
                                    st.metric("Cost Reduction Options", cost_reductions)
                                with col3:
                                    score_improvements = sum(1 for alt in all_alternatives if alt['Score Impact'] > 0)
                                    st.metric("Score Improvement Options", score_improvements)
                            else:
                                st.info("No alternative analysis available for this solution")
                    
                    st.divider()
                    st.markdown("**🔤 Raw Allocation String:**")
                    st.code(allocations_str if allocations_str else "No allocation data", language="text")
                    
                    if st.button("❌ Close Details", key="close_details"):
                        st.session_state.selected_solution = None
                        st.session_state.selected_method = None
                        st.rerun()
            
            # Export results section
            st.divider()
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                if st.button("💾 Export Results to CSV"):
                    try:
                        output_dir = "Output Data"
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = os.path.join(output_dir, "integrated_optimizer_results.csv")
                        df_econst.to_csv(output_path, index=False)
                        st.success(f"✅ Results exported to {output_path}")
                    except Exception as e:
                        st.error(f"❌ Export failed: {str(e)}")
            
            with col_export2:
                csv_data = df_econst.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results CSV",
                    data=csv_data,
                    file_name="integrated_optimizer_results.csv",
                    mime="text/csv"
                )
            
            # Full results table
            st.subheader("📋 All Solutions")
            with st.expander("View All Pareto Solutions", expanded=False):
                display_df = df_econst[['cost', 'score', 'method', 'allocations']].copy()
                display_df.columns = ['Total Cost', 'Score', 'Method', 'Allocation']
                st.dataframe(display_df, use_container_width=True)

    else:
        # Welcome screen for optimizer
        st.info("👆 Use the sidebar to configure your data file and click **Initialize & Analyze Data** to get started!")
        
        st.markdown("""
        ### 🎯 About This ε-Constraint Optimizer
        
        This application uses **ε-Constraint** method for supply chain optimization with **selective NA handling**.
        
        **Key Features:**
        - 🔍 **ε-Constraint Optimization**: Systematic exploration of Pareto front
        - 📊 **Pareto Front Visualization**: Interactive visualization of optimal solutions
        - 🎯 **Multi-objective Optimization**: Minimizes cost while maximizing supplier scores
        - 🏭 **Complex Constraints**: Handles depot-specific supplier availability
        - 📈 **Interactive Analysis**: Click points to explore solutions
        
        **Objectives:**
        - 📉 **Minimize Cost**: Total operational cost
        - 📈 **Maximize Score**: Supplier performance score
        """)
        
        # Parameter guidance section
        with st.expander("⚙️ ε-Constraint Parameter Guide", expanded=False):
            st.markdown("### 🎛️ Parameter Effects Overview")
            
            # Parameter effects table
            param_effects_data = {
                "Parameter": [
                    "Number of Epsilon Points (n_points)",
                    "Constraint Type",
                    "Random Seed"
                ],
                "What It Controls": [
                    "Resolution of Pareto front - How many solutions to generate",
                    "Which objective to constrain - Cost or Score",
                    "Reproducibility of results"
                ],
                "Too Low →": [
                    "Coarse Pareto front, missed trade-offs",
                    "Limited exploration of solution space",
                    "Non-reproducible results"
                ],
                "Too High →": [
                    "Longer computation time, diminishing returns",
                    "N/A (binary choice)",
                    "N/A (any fixed number works)"
                ]
            }
            
            param_effects_df = pd.DataFrame(param_effects_data)
            st.dataframe(param_effects_df, use_container_width=True, hide_index=True)
            
            st.markdown("### 🎯 Recommended Values")
            
            # Recommended values table
            recommended_data = {
                "Parameter": [
                    "Number of Epsilon Points (n_points)",
                    "Constraint Type",
                    "Random Seed"
                ],
                "Recommended Value": [
                    "21 – 50 (start at 21)",
                    "cost (constrain cost, maximize score)",
                    "Any fixed number (e.g., 42)"
                ],
                "Why This Range": [
                    "Good balance of resolution and computation time",
                    "Most intuitive approach for cost optimization",
                    "Ensures reproducible results"
                ]
            }
            
            recommended_df = pd.DataFrame(recommended_data)
            st.dataframe(recommended_df, use_container_width=True, hide_index=True)
            
            st.markdown("""
            ### 💡 Optimization Tips
            
            **For Better Results:**
            - Start with 21 epsilon points, increase if you need finer resolution
            - Use "cost" constraint type for most supply chain scenarios
            - **Small problems**: 10-20 epsilon points
            - **Complex problems**: 30-50 epsilon points
            - **Exploration**: Try both constraint types to see different perspectives
            
            **Performance vs Quality Trade-offs:**
            - 🚀 **Faster**: Fewer epsilon points (10-15)
            - 🎯 **Better quality**: More epsilon points (30-50)
            - ⚖️ **Balanced**: 21 epsilon points (recommended starting point)
            """)
        
        # System requirements
        with st.expander("📋 System Requirements & Data Format"):
            st.markdown("""
            **Required Excel Sheets:**
            - **Obj1_Coeff**: Cost coefficients (COC Rebate, DEL Rebate, Cost of Collection, Zone Differentials)
            - **Obj2_Coeff**: Supplier scoring data
            - **Annual Volumes**: Volume data for each depot
            
            **Data Handling:**
            - Automatically detects 'NA' or missing values
            - Only includes valid depot-supplier-operation combinations
            - Uses CPLEX solver for optimal solutions
            """)

# Run the main application
if __name__ == "__main__":
    main()

# Footer
st.markdown("---")
st.markdown("*Integrated AHP & Supply Chain Optimization Tool*") 