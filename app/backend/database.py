import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create depots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS depots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    annual_volume REAL,
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
            
            # Create supplier_scores table for AHP data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supplier_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER NOT NULL,
                    total_score REAL NOT NULL,
                    criteria_scores TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
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
    
    def add_depot(self, name: str, annual_volume: float = None) -> int:
        """Add a new depot and return the ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO depots (name, annual_volume) VALUES (?, ?)",
                (name, annual_volume)
            )
            return cursor.lastrowid
    
    def get_suppliers(self) -> List[Dict]:
        """Get all suppliers"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM suppliers ORDER BY name")
            return [{"id": row[0], "name": row[1], "email": row[2]} for row in cursor.fetchall()]
    
    def get_depots(self) -> List[Dict]:
        """Get all depots"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, annual_volume FROM depots ORDER BY name")
            return [{"id": row[0], "name": row[1], "annual_volume": row[2]} for row in cursor.fetchall()]
    
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
    
    def save_supplier_scores(self, supplier_id: int, total_score: float, criteria_scores: str) -> int:
        """Save supplier AHP scores"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO supplier_scores 
                (supplier_id, total_score, criteria_scores)
                VALUES (?, ?, ?)
            """, (supplier_id, total_score, criteria_scores))
            return cursor.lastrowid
    
    def get_supplier_scores(self) -> List[Dict]:
        """Get all supplier scores"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.supplier_id, sup.name as supplier_name, 
                       s.total_score, s.criteria_scores
                FROM supplier_scores s
                JOIN suppliers sup ON s.supplier_id = sup.id
                ORDER BY s.total_score DESC
            """)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
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
            
            # Get Obj2_Coeff data (scoring data)
            suppliers = self.get_suppliers()
            scores_data = self.get_supplier_scores()
            
            # Create scores dataframe in the expected format
            scores_dict = {f"Supplier {s['id']}": 0 for s in suppliers}
            for score in scores_data:
                scores_dict[f"Supplier {score['supplier_id']}"] = score['total_score']
            
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
            
            query = """
                SELECT 
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
                    scores.total_score,
                    scores.criteria_scores
                FROM supplier_submissions ss
                JOIN suppliers s ON ss.supplier_id = s.id
                JOIN depots d ON ss.depot_id = d.id
                LEFT JOIN supplier_scores scores ON s.id = scores.supplier_id
                WHERE ss.status = 'approved'
                ORDER BY s.name, d.name
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]