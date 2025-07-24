import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import json

class SupplierDatabase:
    def __init__(self, db_path: str = "supplier_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create suppliers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    email TEXT,
                    company_profile TEXT,
                    annual_revenue REAL,
                    number_of_employees INTEGER,
                    bbee_level INTEGER,
                    black_ownership_percent REAL,
                    black_female_ownership_percent REAL,
                    bbee_compliant BOOLEAN,
                    cipc_cor_documents TEXT,
                    tax_certificate TEXT,
                    fuel_products_offered TEXT,
                    product_service_type TEXT,
                    geographical_network TEXT,
                    delivery_types_offered TEXT,
                    method_of_sourcing TEXT,
                    invest_in_refuelling_equipment TEXT,
                    reciprocal_business TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create depots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS depots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    annual_volume REAL,
                    country TEXT,
                    town TEXT,
                    lats REAL,
                    longs REAL,
                    fuel_zone TEXT,
                    tankage_size REAL,
                    number_of_pumps INTEGER,
                    equipment_value REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create supplier_submissions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supplier_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER NOT NULL,
                    depot_id INTEGER NOT NULL,
                    coc_rebate REAL,
                    cost_of_collection REAL,
                    del_rebate REAL,
                    zone_differential REAL NOT NULL,
                    distance_km REAL,
                    status TEXT DEFAULT 'pending',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by TEXT,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
                    FOREIGN KEY (depot_id) REFERENCES depots (id),
                    UNIQUE(supplier_id, depot_id)
                )
            """)
            
            
            
            # Create supplier_evaluations table for PROMETHEE II data (JSON format like depot_evaluations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supplier_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER NOT NULL,
                    manager_name TEXT,
                    manager_email TEXT,
                    criteria_scores TEXT NOT NULL,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
                    UNIQUE(supplier_id, manager_name)
                )
            """)
            
            # Create promethee_results table for storing PROMETHEE II results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promethee_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER NOT NULL,
                    positive_flow REAL NOT NULL,
                    negative_flow REAL NOT NULL,
                    net_flow REAL NOT NULL,
                    ranking INTEGER NOT NULL,
                    confidence_level REAL,
                    criteria_weights TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
                )
            """)
            
            # Create bwm_weights table for storing BWM weight configurations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bwm_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    criteria_names TEXT NOT NULL,
                    weights TEXT NOT NULL,
                    best_criterion TEXT NOT NULL,
                    worst_criterion TEXT NOT NULL,
                    best_to_others TEXT NOT NULL,
                    others_to_worst TEXT NOT NULL,
                    consistency_ratio REAL,
                    consistency_interpretation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT
                )
            """)
            
            conn.commit()
    
    def add_supplier(self, name: str, email: str = None) -> int:
        """Add a new supplier and return the ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO suppliers (name, email) VALUES (?, ?)",
                (name, email)
            )
            return cursor.lastrowid
    
    def update_supplier_profile(self, supplier_id: int, profile_data: Dict) -> bool:
        """Update supplier profile information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE suppliers SET
                    company_profile = ?,
                    annual_revenue = ?,
                    number_of_employees = ?,
                    bbee_level = ?,
                    black_ownership_percent = ?,
                    black_female_ownership_percent = ?,
                    bbee_compliant = ?,
                    cipc_cor_documents = ?,
                    tax_certificate = ?,
                    fuel_products_offered = ?,
                    product_service_type = ?,
                    geographical_network = ?,
                    delivery_types_offered = ?,
                    method_of_sourcing = ?,
                    invest_in_refuelling_equipment = ?,
                    reciprocal_business = ?
                WHERE id = ?
            """, (
                profile_data.get('company_profile'),
                profile_data.get('annual_revenue'),
                profile_data.get('number_of_employees'),
                profile_data.get('bbee_level'),
                profile_data.get('black_ownership_percent'),
                profile_data.get('black_female_ownership_percent'),
                profile_data.get('bbee_compliant'),
                profile_data.get('cipc_cor_documents'),
                profile_data.get('tax_certificate'),
                profile_data.get('fuel_products_offered'),
                profile_data.get('product_service_type'),
                profile_data.get('geographical_network'),
                profile_data.get('delivery_types_offered'),
                profile_data.get('method_of_sourcing'),
                profile_data.get('invest_in_refuelling_equipment'),
                profile_data.get('reciprocal_business'),
                supplier_id
            ))
            return cursor.rowcount > 0
    
    def add_depot(self, name: str, annual_volume: float = None, country: str = None, 
                  town: str = None, lats: float = None, longs: float = None, 
                  fuel_zone: str = None, tankage_size: float = None, 
                  number_of_pumps: int = None, equipment_value: float = None) -> int:
        """Add a new depot and return the ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO depots 
                   (name, annual_volume, country, town, lats, longs, fuel_zone, 
                    tankage_size, number_of_pumps, equipment_value) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, annual_volume, country, town, lats, longs, fuel_zone, 
                 tankage_size, number_of_pumps, equipment_value)
            )
            return cursor.lastrowid
    
    def get_suppliers(self) -> List[Dict]:
        """Get all suppliers"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, email, company_profile, annual_revenue, number_of_employees,
                       bbee_level, black_ownership_percent, black_female_ownership_percent,
                       bbee_compliant, cipc_cor_documents, tax_certificate, fuel_products_offered,
                       product_service_type, geographical_network, delivery_types_offered,
                       method_of_sourcing, invest_in_refuelling_equipment, reciprocal_business
                FROM suppliers ORDER BY name
            """)
            columns = ["id", "name", "email", "company_profile", "annual_revenue", "number_of_employees",
                      "bbee_level", "black_ownership_percent", "black_female_ownership_percent",
                      "bbee_compliant", "cipc_cor_documents", "tax_certificate", "fuel_products_offered",
                      "product_service_type", "geographical_network", "delivery_types_offered",
                      "method_of_sourcing", "invest_in_refuelling_equipment", "reciprocal_business"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_supplier_by_id(self, supplier_id: int) -> Optional[Dict]:
        """Get a specific supplier by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, email, company_profile, annual_revenue, number_of_employees,
                       bbee_level, black_ownership_percent, black_female_ownership_percent,
                       bbee_compliant, cipc_cor_documents, tax_certificate, fuel_products_offered,
                       product_service_type, geographical_network, delivery_types_offered,
                       method_of_sourcing, invest_in_refuelling_equipment, reciprocal_business
                FROM suppliers WHERE id = ?
            """, (supplier_id,))
            row = cursor.fetchone()
            if row:
                columns = ["id", "name", "email", "company_profile", "annual_revenue", "number_of_employees",
                          "bbee_level", "black_ownership_percent", "black_female_ownership_percent",
                          "bbee_compliant", "cipc_cor_documents", "tax_certificate", "fuel_products_offered",
                          "product_service_type", "geographical_network", "delivery_types_offered",
                          "method_of_sourcing", "invest_in_refuelling_equipment", "reciprocal_business"]
                return dict(zip(columns, row))
            return None
    
    def get_depots(self) -> List[Dict]:
        """Get all depots"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, annual_volume, country, town, lats, longs, 
                       fuel_zone, tankage_size, number_of_pumps, equipment_value
                FROM depots ORDER BY name
            """)
            columns = ["id", "name", "annual_volume", "country", "town", "lats", "longs", 
                      "fuel_zone", "tankage_size", "number_of_pumps", "equipment_value"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def submit_supplier_data(self, supplier_id: int, depot_id: int, data: Dict) -> int:
        """Submit supplier data for a specific depot"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO supplier_submissions 
                (supplier_id, depot_id, coc_rebate, cost_of_collection, del_rebate, 
                 zone_differential, distance_km, status, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            """, (
                supplier_id, depot_id,
                data.get('coc_rebate'), data.get('cost_of_collection'),
                data.get('del_rebate'), data.get('zone_differential'),
                data.get('distance_km')
            ))
            return cursor.lastrowid
    
    def get_supplier_submissions(self, supplier_id: int = None, status: str = None) -> List[Dict]:
        """Get supplier submissions with optional filtering"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT s.id, s.supplier_id, sup.name as supplier_name, 
                       s.depot_id, d.name as depot_name,
                       s.coc_rebate, s.cost_of_collection, s.del_rebate,
                       s.zone_differential, s.distance_km, s.status,
                       s.submitted_at, s.approved_at, s.approved_by
                FROM supplier_submissions s
                JOIN suppliers sup ON s.supplier_id = sup.id
                JOIN depots d ON s.depot_id = d.id
            """
            
            conditions = []
            params = []
            
            if supplier_id:
                conditions.append("s.supplier_id = ?")
                params.append(supplier_id)
            
            if status:
                conditions.append("s.status = ?")
                params.append(status)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY s.submitted_at DESC"
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def approve_submission(self, submission_id: int, approved_by: str) -> bool:
        """Approve a supplier submission"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if this would create a duplicate approved submission
            cursor.execute("""
                SELECT s.supplier_id, s.depot_id
                FROM supplier_submissions s
                WHERE s.id = ?
            """, (submission_id,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            supplier_id, depot_id = result
            
            # Check if there's already an approved submission for this supplier-depot pair
            cursor.execute("""
                SELECT COUNT(*) FROM supplier_submissions
                WHERE supplier_id = ? AND depot_id = ? AND status = 'approved'
            """, (supplier_id, depot_id))
            
            if cursor.fetchone()[0] > 0:
                raise ValueError(f"Supplier {supplier_id} already has an approved submission for depot {depot_id}")
            
            cursor.execute("""
                UPDATE supplier_submissions 
                SET status = 'approved', approved_at = CURRENT_TIMESTAMP, approved_by = ?
                WHERE id = ?
            """, (approved_by, submission_id))
            return cursor.rowcount > 0
    
    def reject_submission(self, submission_id: int, rejected_by: str) -> bool:
        """Reject a supplier submission"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE supplier_submissions 
                SET status = 'rejected', approved_at = CURRENT_TIMESTAMP, approved_by = ?
                WHERE id = ?
            """, (rejected_by, submission_id))
            return cursor.rowcount > 0
    
    def bulk_approve_supplier_submissions(self, supplier_id: int, approved_by: str) -> bool:
        """Approve all pending submissions for a supplier"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE supplier_submissions 
                SET status = 'approved', approved_at = CURRENT_TIMESTAMP, approved_by = ?
                WHERE supplier_id = ? AND status = 'pending'
            """, (approved_by, supplier_id))
            return cursor.rowcount > 0
    
    def bulk_reject_supplier_submissions(self, supplier_id: int, rejected_by: str) -> bool:
        """Reject all pending submissions for a supplier"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE supplier_submissions 
                SET status = 'rejected', approved_at = CURRENT_TIMESTAMP, approved_by = ?
                WHERE supplier_id = ? AND status = 'pending'
            """, (rejected_by, supplier_id))
            return cursor.rowcount > 0
    
    def get_submissions_by_status(self, status: str) -> List[Dict]:
        """Get submissions by status"""
        return self.get_supplier_submissions(status=status)
    
    
    
    def export_to_optimizer_format(self) -> Dict[str, pd.DataFrame]:
        """Export approved data in the format expected by SelectiveNAFlexibleEConstraintOptimizer"""
        with sqlite3.connect(self.db_path) as conn:
            # Get Obj1_Coeff data (cost coefficients)
            obj1_query = """
                SELECT d.id as Depot, ss.supplier_id as Supplier,
                       ss.coc_rebate as 'COC Rebate(R/L)',
                       ss.cost_of_collection as 'Cost of Collection (R/L)',
                       ss.del_rebate as 'DEL Rebate(R/L)',
                       ss.zone_differential as 'Zone Differentials',
                       ss.distance_km as 'Distance(Km)'
                FROM supplier_submissions ss
                JOIN suppliers s ON ss.supplier_id = s.id
                JOIN depots d ON ss.depot_id = d.id
                WHERE ss.status = 'approved'
                ORDER BY d.id, ss.supplier_id
            """
            obj1_df = pd.read_sql_query(obj1_query, conn)
            
            # Get Obj2_Coeff data (scoring data) - use default scores since supplier_scores table removed
            suppliers = self.get_suppliers()
            
            # Create scores dataframe with default scores (optimizer reads from uploaded Excel anyway)
            scores_dict = {f"Supplier {s['id']}": 5.0 for s in suppliers}  # Default neutral score
            
            # Create the scores dataframe with the expected format
            obj2_data = [['Total Score', 1.0] + list(scores_dict.values())]
            obj2_columns = ['Scoring Element', 'Criteria Weighting'] + list(scores_dict.keys())
            obj2_df = pd.DataFrame(obj2_data, columns=obj2_columns)
            
            # Pad to ensure row 6 (index 5) contains the scores
            while len(obj2_df) < 6:
                obj2_df = pd.concat([obj2_df, pd.DataFrame([[''] * len(obj2_columns)], columns=obj2_columns)], ignore_index=True)
            
            # Get Annual Volumes data
            volumes_query = """
                SELECT name as 'Site Names', annual_volume as 'Annual Volume(Litres)'
                FROM depots
                WHERE annual_volume IS NOT NULL
                ORDER BY id
            """
            volumes_df = pd.read_sql_query(volumes_query, conn)
            
            return {
                'Obj1_Coeff': obj1_df,
                'Obj2_Coeff': obj2_df,
                'Annual Volumes': volumes_df
            }
    
    def create_temporary_excel_file(self) -> str:
        """Create a temporary Excel file for the optimizer"""
        data = self.export_to_optimizer_format()
        
        # Create temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = f"temp_optimizer_data_{timestamp}.xlsx"
        
        with pd.ExcelWriter(temp_file, engine='openpyxl') as writer:
            data['Obj1_Coeff'].to_excel(writer, sheet_name='Obj1_Coeff', index=False)
            data['Obj2_Coeff'].to_excel(writer, sheet_name='Obj2_Coeff', index=False)
            data['Annual Volumes'].to_excel(writer, sheet_name='Annual Volumes', index=False)
        
        return temp_file
    
    def get_approved_optimization_data(self) -> List[Dict]:
        """Get all approved submissions with supplier and depot details for optimization"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Simplified query without supplier_scores LEFT JOIN to avoid corruption issues
            query = """
                SELECT DISTINCT
                    ss.id as submission_id,
                    s.name as supplier_name,
                    s.id as supplier_id,
                    d.name as depot_name,
                    d.id as depot_id,
                    d.annual_volume,
                    ss.coc_rebate,
                    ss.cost_of_collection,
                    ss.del_rebate,
                    ss.zone_differential,
                    ss.distance_km,
                    ss.approved_at,
                    ss.approved_by,
                    NULL as total_score,
                    NULL as criteria_scores
                FROM supplier_submissions ss
                JOIN suppliers s ON ss.supplier_id = s.id
                JOIN depots d ON ss.depot_id = d.id
                WHERE ss.status = 'approved'
                ORDER BY s.name, d.name
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    
    
    def submit_supplier_evaluation(self, supplier_id: int, criteria_scores: Dict[str, float], 
                                   manager_name: str = None, manager_email: str = None) -> int:
        """Submit a supplier evaluation with all criteria scores as JSON"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            criteria_scores_json = json.dumps(criteria_scores)
            cursor.execute("""
                INSERT OR REPLACE INTO supplier_evaluations 
                (supplier_id, manager_name, manager_email, criteria_scores)
                VALUES (?, ?, ?, ?)
            """, (supplier_id, manager_name, manager_email, criteria_scores_json))
            return cursor.lastrowid
    
    def submit_supplier_evaluations_batch(self, evaluations: List[Dict], manager_name: str, manager_email: str) -> List[int]:
        """Submit multiple supplier evaluations at once"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Group evaluations by supplier_id to create JSON criteria scores
            supplier_evaluations = {}
            
            for evaluation in evaluations:
                supplier_id = evaluation['supplier_id']
                if supplier_id not in supplier_evaluations:
                    supplier_evaluations[supplier_id] = {}
                
                supplier_evaluations[supplier_id][evaluation['criterion_name']] = evaluation['score']
            
            # Submit one evaluation per supplier with all criteria scores
            evaluation_ids = []
            for supplier_id, criteria_scores in supplier_evaluations.items():
                criteria_scores_json = json.dumps(criteria_scores)
                cursor.execute("""
                    INSERT OR REPLACE INTO supplier_evaluations 
                    (supplier_id, manager_name, manager_email, criteria_scores)
                    VALUES (?, ?, ?, ?)
                """, (supplier_id, manager_name, manager_email, criteria_scores_json))
                evaluation_ids.append(cursor.lastrowid)
            
            return evaluation_ids
    
    def get_supplier_evaluations(self, supplier_id: int = None) -> List[Dict]:
        """Get supplier evaluations with optional filtering"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = """
                SELECT se.id, se.supplier_id, s.name as supplier_name,
                       se.manager_name, se.manager_email, se.criteria_scores,
                       se.submitted_at
                FROM supplier_evaluations se
                JOIN suppliers s ON se.supplier_id = s.id
            """
            
            conditions = []
            params = []
            
            if supplier_id:
                conditions.append("se.supplier_id = ?")
                params.append(supplier_id)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY se.submitted_at DESC"
            
            cursor.execute(query, params)
            
            # Parse results and expand criteria scores
            results = []
            for row in cursor.fetchall():
                result = {
                    'id': row[0],
                    'supplier_id': row[1],
                    'supplier_name': row[2],
                    'manager_name': row[3],
                    'manager_email': row[4],
                    'criteria_scores': json.loads(row[5]),
                    'submitted_at': row[6]
                }
                results.append(result)
            return results
    
    def get_aggregated_supplier_scores(self, criteria_names: List[str]) -> Dict[int, Dict[str, Dict]]:
        """Get aggregated scores for PROMETHEE II calculation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all evaluations with JSON criteria scores
            cursor.execute("""
                SELECT supplier_id, criteria_scores
                FROM supplier_evaluations
            """)
            
            # Initialize result structure
            result = {}
            
            for row in cursor.fetchall():
                supplier_id, criteria_scores_json = row
                criteria_scores = json.loads(criteria_scores_json)
                
                if supplier_id not in result:
                    result[supplier_id] = {}
                
                # Process each criterion from the JSON
                for criterion_name, score in criteria_scores.items():
                    if criterion_name in criteria_names:
                        if criterion_name not in result[supplier_id]:
                            result[supplier_id][criterion_name] = {
                                'scores': [],
                                'evaluations_count': 0
                            }
                        
                        result[supplier_id][criterion_name]['scores'].append(score)
                        result[supplier_id][criterion_name]['evaluations_count'] += 1
            
            # Calculate averages and confidence
            for supplier_id in result:
                for criterion_name in result[supplier_id]:
                    scores = result[supplier_id][criterion_name]['scores']
                    avg_score = sum(scores) / len(scores)
                    count = len(scores)
                    
                    result[supplier_id][criterion_name] = {
                        'score': avg_score,
                        'evaluations_count': count,
                        'confidence': count  # Show number of evaluations instead of percentage
                    }
            
            return result
    
    def get_supplier_evaluation_counts(self) -> Dict[int, int]:
        """Get the number of manager evaluations per supplier"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count unique evaluations per supplier (now one row per manager evaluation)
            cursor.execute("""
                SELECT supplier_id, COUNT(*) as manager_count
                FROM supplier_evaluations
                GROUP BY supplier_id
            """)
            
            result = {}
            for row in cursor.fetchall():
                supplier_id, manager_count = row
                result[supplier_id] = manager_count
            
            return result
    
    def clear_supplier_evaluations(self) -> Dict:
        """Clear all supplier evaluations and return count of cleared records"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get count before clearing
            cursor.execute("SELECT COUNT(*) FROM supplier_evaluations")
            count_before = cursor.fetchone()[0]
            
            # Clear all supplier evaluations
            cursor.execute("DELETE FROM supplier_evaluations")
            conn.commit()
            
            return {
                "message": "All supplier evaluations cleared successfully",
                "cleared_count": count_before
            }
    
    def save_promethee_results(self, supplier_id: int, positive_flow: float, negative_flow: float,
                              net_flow: float, ranking: int, confidence_level: float,
                              criteria_weights: str) -> int:
        """Save PROMETHEE II results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO promethee_results 
                (supplier_id, positive_flow, negative_flow, net_flow, ranking, confidence_level, criteria_weights)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (supplier_id, positive_flow, negative_flow, net_flow, ranking, confidence_level, criteria_weights))
            return cursor.lastrowid
    
    def get_promethee_results(self) -> List[Dict]:
        """Get PROMETHEE II results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pr.supplier_id, s.name as supplier_name,
                       pr.positive_flow, pr.negative_flow, pr.net_flow,
                       pr.ranking, pr.confidence_level, pr.criteria_weights,
                       pr.created_at
                FROM promethee_results pr
                JOIN suppliers s ON pr.supplier_id = s.id
                ORDER BY pr.ranking
            """)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def cleanup_duplicate_submissions(self) -> Dict:
        """Remove duplicate supplier-depot pairs, keeping the most recent approved submission"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Find duplicates
            cursor.execute("""
                SELECT supplier_id, depot_id, COUNT(*) as count
                FROM supplier_submissions
                WHERE status = 'approved'
                GROUP BY supplier_id, depot_id
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            
            if not duplicates:
                return {"message": "No duplicates found", "cleaned": 0}
            
            cleaned_count = 0
            for supplier_id, depot_id, count in duplicates:
                # Keep the most recent submission, delete others
                cursor.execute("""
                    DELETE FROM supplier_submissions
                    WHERE supplier_id = ? AND depot_id = ? AND status = 'approved'
                    AND id NOT IN (
                        SELECT id FROM supplier_submissions
                        WHERE supplier_id = ? AND depot_id = ? AND status = 'approved'
                        ORDER BY approved_at DESC, id DESC
                        LIMIT 1
                    )
                """, (supplier_id, depot_id, supplier_id, depot_id))
                cleaned_count += cursor.rowcount
            
            conn.commit()
            return {
                "message": f"Cleaned {cleaned_count} duplicate submissions",
                "duplicate_pairs": len(duplicates),
                "cleaned": cleaned_count
            }

    def get_evaluation_summary(self) -> Dict:
        """Get summary of depot evaluations for admin dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total evaluations (now represents complete manager evaluations)
            cursor.execute("SELECT COUNT(*) FROM supplier_evaluations")
            total_evaluations = cursor.fetchone()[0]
            
            # Evaluations by supplier (count of complete evaluations)
            cursor.execute("""
                SELECT s.name, COUNT(se.id) as evaluation_count
                FROM suppliers s
                LEFT JOIN supplier_evaluations se ON s.id = se.supplier_id
                GROUP BY s.id, s.name
                ORDER BY evaluation_count DESC
            """)
            supplier_evaluations = [{"supplier": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            # Count unique suppliers that have been evaluated
            cursor.execute("SELECT COUNT(DISTINCT supplier_id) FROM supplier_evaluations")
            suppliers_evaluated = cursor.fetchone()[0]
            
            # Count unique managers who participated
            cursor.execute("SELECT COUNT(DISTINCT manager_name) FROM supplier_evaluations WHERE manager_name IS NOT NULL")
            managers_participated = cursor.fetchone()[0]
            
            return {
                "total_evaluations": total_evaluations,
                "supplier_evaluations": supplier_evaluations,
                "suppliers_evaluated": suppliers_evaluated,
                "managers_participated": managers_participated
            }
    
    def save_bwm_weights(self, criteria_names: List[str], weights: Dict[str, float], 
                        best_criterion: str, worst_criterion: str, 
                        best_to_others: Dict[str, float], others_to_worst: Dict[str, float],
                        consistency_ratio: float, consistency_interpretation: str,
                        created_by: str = None) -> int:
        """Save BWM weights configuration to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bwm_weights 
                (criteria_names, weights, best_criterion, worst_criterion, 
                 best_to_others, others_to_worst, consistency_ratio, 
                 consistency_interpretation, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                json.dumps(criteria_names),
                json.dumps(weights),
                best_criterion,
                worst_criterion,
                json.dumps(best_to_others),
                json.dumps(others_to_worst),
                consistency_ratio,
                consistency_interpretation,
                created_by
            ))
            return cursor.lastrowid
    
    def get_latest_bwm_weights(self) -> Optional[Dict]:
        """Get the most recent BWM weights configuration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT criteria_names, weights, best_criterion, worst_criterion,
                       best_to_others, others_to_worst, consistency_ratio,
                       consistency_interpretation, created_at, created_by
                FROM bwm_weights
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    'criteria_names': json.loads(row[0]),
                    'weights': json.loads(row[1]),
                    'best_criterion': row[2],
                    'worst_criterion': row[3],
                    'best_to_others': json.loads(row[4]),
                    'others_to_worst': json.loads(row[5]),
                    'consistency_ratio': row[6],
                    'consistency_interpretation': row[7],
                    'created_at': row[8],
                    'created_by': row[9]
                }
            return None