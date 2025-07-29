import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import json
import time
import random
import threading
from contextlib import contextmanager

class SupplierDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to the database in the backend directory
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(backend_dir, "supplier_data_clean.db")
        self.db_path = db_path
        self._lock = threading.RLock()
        self.init_database()
    
    @contextmanager
    def get_connection(self, timeout: float = 30.0, retries: int = 3):
        """
        Get a database connection with proper timeout and retry handling.
        Uses safe database connection settings to avoid disk I/O errors.
        """
        connection = None
        try:
            for attempt in range(retries):
                try:
                    connection = sqlite3.connect(
                        self.db_path, 
                        timeout=timeout,
                        isolation_level=None  # Autocommit mode for better concurrency
                    )
                    
                    # Safe PRAGMA settings - avoid WAL mode due to WSL2 file system issues
                    try:
                        # Try WAL mode first, fall back to DELETE if it fails
                        result = connection.execute("PRAGMA journal_mode=WAL")
                        journal_mode = result.fetchone()[0] if result else None
                        if journal_mode != 'wal':
                            print(f"Warning: WAL mode not enabled (got {journal_mode}), using DELETE mode instead")
                            connection.execute("PRAGMA journal_mode=DELETE")
                    except (sqlite3.OperationalError, sqlite3.DatabaseError) as pragma_error:
                        if any(phrase in str(pragma_error).lower() for phrase in ["disk i/o error", "database is locked", "unable to open"]):
                            print(f"Warning: WAL mode failed ({pragma_error}), using DELETE mode instead")
                            try:
                                connection.execute("PRAGMA journal_mode=DELETE")
                            except sqlite3.OperationalError:
                                # If DELETE mode also fails, continue without setting journal mode
                                print("Warning: Could not set any journal mode, continuing with default")
                        else:
                            raise
                    
                    # Apply other PRAGMA settings with error handling
                    try:
                        connection.execute("PRAGMA synchronous=NORMAL")
                    except sqlite3.OperationalError as e:
                        if "disk i/o error" in str(e).lower():
                            print(f"Warning: Could not set synchronous mode, using default")
                        else:
                            raise
                    
                    # Set other non-critical PRAGMA settings with individual error handling
                    for pragma_cmd, description in [
                        ("PRAGMA cache_size=10000", "cache size"),
                        ("PRAGMA temp_store=MEMORY", "temp store"),
                        ("PRAGMA busy_timeout=30000", "busy timeout")
                    ]:
                        try:
                            connection.execute(pragma_cmd)
                        except sqlite3.OperationalError as e:
                            if "disk i/o error" in str(e).lower():
                                print(f"Warning: Could not set {description}, using default")
                            else:
                                raise
                    
                    # Connection successfully created and configured
                    break
                    
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e).lower() and attempt < retries - 1:
                        # Exponential backoff with jitter
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        print(f"Database locked, retrying in {delay:.2f}s (attempt {attempt + 1}/{retries})")
                        if connection:
                            connection.close()
                            connection = None
                        time.sleep(delay)
                        continue
                    elif "disk I/O error" in str(e).lower():
                        # Handle disk I/O errors specifically
                        print(f"Database disk I/O error on attempt {attempt + 1}: {e}")
                        if connection:
                            connection.close()
                            connection = None
                        if attempt < retries - 1:
                            delay = (2 ** attempt) + random.uniform(0, 1)
                            print(f"Retrying in {delay:.2f}s...")
                            time.sleep(delay)
                            continue
                        else:
                            raise sqlite3.OperationalError(f"Persistent disk I/O error after {retries} attempts. This may be due to WSL2 file system limitations. Try moving the database to a native Linux path or use a different journal mode.")
                    else:
                        if connection:
                            connection.close()
                            connection = None
                        raise
                except Exception as e:
                    if connection:
                        connection.close()
                        connection = None
                    raise
            
            # Yield the connection for use
            yield connection
            
        finally:
            # Only close the connection here after the with block is done
            if connection:
                try:
                    connection.close()
                except:
                    pass
    
    def execute_with_retry(self, query: str, params: tuple = (), timeout: float = 30.0, retries: int = 3):
        """Execute a query with retry logic for database locks"""
        with self.get_connection(timeout, retries) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount
    
    def init_database(self):
        """Initialize the database with required tables"""
        with self.get_connection() as conn:
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
                    "B-BBEE_level" INTEGER,
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
                    participant_name TEXT,
                    participant_email TEXT,
                    criteria_scores TEXT NOT NULL,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
                    UNIQUE(supplier_id, participant_name)
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
            
            # Create profile scoring configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile_scoring_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    criteria_name TEXT NOT NULL,
                    option_value TEXT NOT NULL,
                    score REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(criteria_name, option_value)
                )
            """)
            
            # Create unified supplier criteria scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supplier_criteria_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER NOT NULL,
                    criterion_name TEXT NOT NULL,
                    score REAL NOT NULL,
                    data_source TEXT NOT NULL DEFAULT 'unknown',
                    score_count INTEGER DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
                    UNIQUE(supplier_id, criterion_name)
                )
            """)
            
            # Create audit log table for tracking refresh operations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unified_scores_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    supplier_id INTEGER,
                    criteria_affected TEXT,
                    trigger_source TEXT NOT NULL,
                    records_affected INTEGER DEFAULT 0,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def add_supplier(self, name: str, email: str = None) -> int:
        """Add a new supplier and return the ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO suppliers (name, email) VALUES (?, ?)",
                (name, email)
            )
            supplier_id = cursor.lastrowid
            
            # Create initial unified scores for new supplier (non-blocking)
            try:
                bwm_data = self.get_latest_bwm_weights()
                if bwm_data:
                    # Use threading to make this non-blocking
                    import threading
                    def refresh_in_background():
                        try:
                            self.refresh_unified_scores_for_supplier(supplier_id, bwm_data['criteria_names'], "supplier_creation")
                            print(f"Event-driven refresh: New supplier {supplier_id} created, initial unified scores added")
                        except Exception as e:
                            print(f"Background refresh warning: Failed to create initial unified scores for new supplier {supplier_id}: {e}")
                    
                    thread = threading.Thread(target=refresh_in_background, daemon=True)
                    thread.start()
                else:
                    print(f"Warning: No BWM weights found for initial unified scores creation for supplier {supplier_id}")
            except Exception as e:
                # Don't fail the supplier creation if unified scores creation fails
                print(f"Warning: Failed to create initial unified scores for new supplier {supplier_id}: {e}")
            
            return supplier_id
    
    def update_supplier_profile(self, supplier_id: int, profile_data: Dict) -> bool:
        """Update supplier profile information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE suppliers SET
                    company_profile = ?,
                    annual_revenue = ?,
                    number_of_employees = ?,
                    "B-BBEE_level" = ?,
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
            
            success = cursor.rowcount > 0
            
            # Trigger unified table refresh for this supplier after successful profile update (non-blocking)
            if success:
                try:
                    # Get current BWM criteria names to refresh properly
                    bwm_data = self.get_latest_bwm_weights()
                    if bwm_data:
                        # Use threading to make this non-blocking
                        import threading
                        def refresh_in_background():
                            try:
                                self.refresh_unified_scores_for_supplier(supplier_id, bwm_data['criteria_names'], "profile_update")
                                print(f"Event-driven refresh: Supplier {supplier_id} profile updated, unified scores refreshed")
                            except Exception as e:
                                print(f"Background refresh warning: Failed to refresh unified scores for supplier {supplier_id} after profile update: {e}")
                        
                        thread = threading.Thread(target=refresh_in_background, daemon=True)
                        thread.start()
                    else:
                        print(f"Warning: No BWM weights found for unified scores refresh after supplier {supplier_id} profile update")
                except Exception as e:
                    # Don't fail the profile update if refresh fails, but log the issue
                    print(f"Warning: Failed to refresh unified scores for supplier {supplier_id} after profile update: {e}")
            
            return success
    
    def add_depot(self, name: str, annual_volume: float = None, country: str = None, 
                  town: str = None, lats: float = None, longs: float = None, 
                  fuel_zone: str = None, tankage_size: float = None, 
                  number_of_pumps: int = None, equipment_value: float = None) -> int:
        """Add a new depot and return the ID"""
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, email, company_profile, annual_revenue, number_of_employees,
                       "B-BBEE_level", black_ownership_percent, black_female_ownership_percent,
                       bbee_compliant, cipc_cor_documents, tax_certificate, fuel_products_offered,
                       product_service_type, geographical_network, delivery_types_offered,
                       method_of_sourcing, invest_in_refuelling_equipment, reciprocal_business
                FROM suppliers ORDER BY name
            """)
            columns = ["id", "name", "email", "company_profile", "annual_revenue", "number_of_employees",
                      "B-BBEE_level", "black_ownership_percent", "black_female_ownership_percent",
                      "bbee_compliant", "cipc_cor_documents", "tax_certificate", "fuel_products_offered",
                      "product_service_type", "geographical_network", "delivery_types_offered",
                      "method_of_sourcing", "invest_in_refuelling_equipment", "reciprocal_business"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_supplier_by_id(self, supplier_id: int) -> Optional[Dict]:
        """Get a specific supplier by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, email, company_profile, annual_revenue, number_of_employees,
                       "B-BBEE_level", black_ownership_percent, black_female_ownership_percent,
                       bbee_compliant, cipc_cor_documents, tax_certificate, fuel_products_offered,
                       product_service_type, geographical_network, delivery_types_offered,
                       method_of_sourcing, invest_in_refuelling_equipment, reciprocal_business
                FROM suppliers WHERE id = ?
            """, (supplier_id,))
            row = cursor.fetchone()
            if row:
                columns = ["id", "name", "email", "company_profile", "annual_revenue", "number_of_employees",
                          "B-BBEE_level", "black_ownership_percent", "black_female_ownership_percent",
                          "bbee_compliant", "cipc_cor_documents", "tax_certificate", "fuel_products_offered",
                          "product_service_type", "geographical_network", "delivery_types_offered",
                          "method_of_sourcing", "invest_in_refuelling_equipment", "reciprocal_business"]
                return dict(zip(columns, row))
            return None
    
    def get_depots(self) -> List[Dict]:
        """Get all depots"""
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE supplier_submissions 
                SET status = 'rejected', approved_at = CURRENT_TIMESTAMP, approved_by = ?
                WHERE id = ?
            """, (rejected_by, submission_id))
            return cursor.rowcount > 0
    
    def bulk_approve_supplier_submissions(self, supplier_id: int, approved_by: str) -> bool:
        """Approve all pending submissions for a supplier"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE supplier_submissions 
                SET status = 'approved', approved_at = CURRENT_TIMESTAMP, approved_by = ?
                WHERE supplier_id = ? AND status = 'pending'
            """, (approved_by, supplier_id))
            return cursor.rowcount > 0
    
    def bulk_reject_supplier_submissions(self, supplier_id: int, rejected_by: str) -> bool:
        """Reject all pending submissions for a supplier"""
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
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
    
    
    
    def submit_single_supplier_evaluation(self, supplier_id: int, criterion_name: str, score: float,
                                         participant_name: str = None, participant_email: str = None) -> int:
        """Submit a single criterion evaluation for a supplier"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert the single evaluation into the new table
            cursor.execute("""
                INSERT INTO supplier_evaluations 
                (supplier_id, participant_name, participant_email, criteria_scores)
                VALUES (?, ?, ?, ?)
            """, (supplier_id, participant_name, participant_email, json.dumps({criterion_name: score})))
            
            evaluation_id = cursor.lastrowid
            conn.commit()
            
            # Refresh unified scores for this supplier in a separate transaction
            try:
                # We only have one criterion, so pass it as the criteria list
                self.refresh_unified_scores_for_supplier(supplier_id, [criterion_name])
            except Exception as e:
                print(f"Warning: Failed to refresh unified scores for supplier {supplier_id}: {e}")
            
            return evaluation_id

    def submit_supplier_evaluation(self, supplier_id: int, criteria_scores: Dict[str, float], 
                                   participant_name: str = None, participant_email: str = None) -> int:
        """Submit a supplier evaluation with all criteria scores as JSON"""
        
        # Step 1: Complete the main evaluation submission transaction first
        evaluation_id = None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            criteria_scores_json = json.dumps(criteria_scores)
            cursor.execute("""
                INSERT OR REPLACE INTO supplier_evaluations 
                (supplier_id, participant_name, participant_email, criteria_scores)
                VALUES (?, ?, ?, ?)
            """, (supplier_id, participant_name, participant_email, criteria_scores_json))
            evaluation_id = cursor.lastrowid
            
            # Commit the main transaction before doing refresh operations
            conn.commit()
        
        # Step 2: Now refresh unified scores in separate transaction (after main transaction is complete)
        if evaluation_id:
            try:
                # Get current BWM criteria names to refresh properly
                bwm_data = self.get_latest_bwm_weights()
                if bwm_data:
                    self.refresh_unified_scores_for_supplier(supplier_id, bwm_data['criteria_names'], "evaluation_submission")
            except Exception as e:
                # Don't fail the evaluation submission if refresh fails
                print(f"Warning: Failed to refresh unified scores for supplier {supplier_id}: {e}")
        
        return evaluation_id
    
    def submit_supplier_evaluations_batch(self, evaluations: List[Dict], participant_name: str, participant_email: str) -> List[int]:
        """Submit multiple supplier evaluations at once with proper transaction isolation"""
        
        evaluation_ids = []
        supplier_ids_to_refresh = []
        
        # Step 1: Complete the main evaluation submission transaction first
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Group evaluations by supplier_id to create JSON criteria scores
                supplier_evaluations = {}
                
                for evaluation in evaluations:
                    supplier_id = evaluation['supplier_id']
                    if supplier_id not in supplier_evaluations:
                        supplier_evaluations[supplier_id] = {}
                    
                    supplier_evaluations[supplier_id][evaluation['criterion_name']] = evaluation['score']
                
                # Submit one evaluation per supplier with all criteria scores
                for supplier_id, criteria_scores in supplier_evaluations.items():
                    criteria_scores_json = json.dumps(criteria_scores)
                    cursor.execute("""
                        INSERT OR REPLACE INTO supplier_evaluations 
                        (supplier_id, participant_name, participant_email, criteria_scores)
                        VALUES (?, ?, ?, ?)
                    """, (supplier_id, participant_name, participant_email, criteria_scores_json))
                    evaluation_id = cursor.lastrowid
                    evaluation_ids.append(evaluation_id)
                    
                    # Track which suppliers need unified scores refresh
                    if evaluation_id:
                        supplier_ids_to_refresh.append(supplier_id)
                
                # Explicitly commit the main transaction within the connection context
                conn.commit()
                
        except Exception as e:
            print(f"Error in batch submission transaction: {e}")
            raise
        
        # Step 2: Now refresh unified scores in separate, independent transactions
        # This prevents transaction conflicts and database locks
        if supplier_ids_to_refresh:
            self._refresh_unified_scores_batch_async(supplier_ids_to_refresh)
        
        return evaluation_ids
    
    def _refresh_unified_scores_batch_async(self, supplier_ids: List[int]):
        """Refresh unified scores for multiple suppliers asynchronously to prevent blocking"""
        def refresh_batch_in_background():
            try:
                bwm_data = self.get_latest_bwm_weights()
                if not bwm_data:
                    print("Warning: No BWM weights found for unified scores refresh")
                    return
                
                for supplier_id in supplier_ids:
                    try:
                        # Each refresh gets its own independent transaction
                        self.refresh_unified_scores_for_supplier(supplier_id, bwm_data['criteria_names'], "batch_evaluation_submission")
                    except Exception as e:
                        # Log but don't fail other refreshes
                        print(f"Warning: Failed to refresh unified scores for supplier {supplier_id}: {e}")
                        
                print(f"Background batch refresh completed for {len(supplier_ids)} suppliers")
                
            except Exception as e:
                print(f"Error in background batch refresh: {e}")
        
        # Run refresh in background thread to avoid blocking the main response
        import threading
        thread = threading.Thread(target=refresh_batch_in_background, daemon=True)
        thread.start()
    
    def get_supplier_evaluations(self, supplier_id: int = None) -> List[Dict]:
        """Get supplier evaluations with optional filtering"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT se.id, se.supplier_id, s.name as supplier_name,
                       se.participant_name, se.participant_email, se.criteria_scores,
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
                    'participant_name': row[3],
                    'participant_email': row[4],
                    'criteria_scores': json.loads(row[5]),
                    'submitted_at': row[6]
                }
                results.append(result)
            return results
    
    def get_profile_scores_for_suppliers(self, criteria_names: List[str]) -> Dict[int, Dict[str, Dict]]:
        """Get profile criteria scores for all suppliers based on their profile data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Define mapping from BWM criteria names to profile_scoring_config criteria names
            criteria_column_mapping = {
                'B-BBEE Level': 'B-BBEE Level',  # Fixed: use consistent naming
                'Geographical Network': 'geographical_network', 
                'Method of Sourcing': 'method_of_sourcing',
                'Product/Service Type': 'product_service_type',
                'Investment in Equipment': 'invest_in_refuelling_equipment',
                'Reciprocal Business': 'reciprocal_business'
            }
            
            # Get all suppliers with their profile data
            cursor.execute("""
                SELECT id, name, "B-BBEE_level", geographical_network, method_of_sourcing, 
                       product_service_type, invest_in_refuelling_equipment, reciprocal_business
                FROM suppliers
            """)
            
            suppliers = cursor.fetchall()
            
            # Get all profile scoring configurations
            cursor.execute("""
                SELECT criteria_name, option_value, score
                FROM profile_scoring_config
            """)
            
            scoring_config = {}
            for row in cursor.fetchall():
                criteria_name, option_value, score = row
                if criteria_name not in scoring_config:
                    scoring_config[criteria_name] = {}
                scoring_config[criteria_name][option_value] = score
            
            result = {}
            
            # Process each supplier
            for supplier_row in suppliers:
                supplier_id = supplier_row[0]
                supplier_name = supplier_row[1]
                
                # Map supplier data to profile values
                supplier_profile = {
                    'B-BBEE Level': supplier_row[2],  # Fixed: use consistent naming
                    'geographical_network': supplier_row[3],
                    'method_of_sourcing': supplier_row[4],
                    'product_service_type': supplier_row[5],
                    'invest_in_refuelling_equipment': supplier_row[6],
                    'reciprocal_business': supplier_row[7]
                }
                
                result[supplier_id] = {}
                
                # Calculate scores for each requested criteria that is a profile criteria
                for criterion_name in criteria_names:
                    if criterion_name in criteria_column_mapping:
                        config_criteria_name = criteria_column_mapping[criterion_name]
                        supplier_value = supplier_profile[config_criteria_name]
                        
                        # Special handling for B-BBEE Level - convert integer to expected string format
                        if config_criteria_name == 'B-BBEE Level' and supplier_value is not None:
                            if isinstance(supplier_value, (int, float)):
                                if supplier_value >= 5:
                                    supplier_value = "Level 5+"
                                else:
                                    supplier_value = f"Level {int(supplier_value)}"
                        
                        # Look up score from scoring config using the config criteria name
                        if config_criteria_name in scoring_config and supplier_value:
                            if supplier_value in scoring_config[config_criteria_name]:
                                score = scoring_config[config_criteria_name][supplier_value]
                                result[supplier_id][criterion_name] = {
                                    'score': score,
                                    'evaluations_count': 1,  # Profile data is always available
                                    'confidence': 100,  # Profile data has perfect confidence
                                    'source': 'profile'
                                }
                            else:
                                # Handle case where supplier value doesn't match any config
                                print(f"Warning: No scoring config found for {config_criteria_name}='{supplier_value}' (supplier {supplier_name})")
                                result[supplier_id][criterion_name] = {
                                    'score': 0.0,  # Default score
                                    'evaluations_count': 1,
                                    'confidence': 50,  # Lower confidence for default
                                    'source': 'profile_default'
                                }
                        else:
                            # Supplier has no data for this profile criteria
                            result[supplier_id][criterion_name] = {
                                'score': 0.0,  # Default score
                                'evaluations_count': 1, 
                                'confidence': 0,  # No confidence when data is missing
                                'source': 'profile_missing'
                            }
            
            return result

    def get_aggregated_supplier_scores(self, criteria_names: List[str]) -> Dict[int, Dict[str, Dict]]:
        """Get aggregated scores for PROMETHEE II calculation - combines survey and profile scores"""
        
        # Get survey scores from evaluations
        survey_scores = self._get_survey_scores(criteria_names)
        
        # Get profile scores from supplier data
        profile_scores = self.get_profile_scores_for_suppliers(criteria_names)
        
        # Merge the two score sources
        result = {}
        
        # Start with profile scores (always available for all suppliers)
        for supplier_id, profile_criteria in profile_scores.items():
            result[supplier_id] = profile_criteria.copy()
        
        # Add/override with survey scores where available
        for supplier_id, survey_criteria in survey_scores.items():
            if supplier_id not in result:
                result[supplier_id] = {}
            
            for criterion_name, score_data in survey_criteria.items():
                result[supplier_id][criterion_name] = score_data
        
        return result
    
    def _get_survey_scores(self, criteria_names: List[str]) -> Dict[int, Dict[str, Dict]]:
        """Get aggregated survey scores from supplier evaluations"""
        with self.get_connection() as conn:
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
                    # Find matching criterion name in the criteria_names list (may have spaces)
                    matched_criterion = None
                    for criteria_name in criteria_names:
                        if criteria_name.strip() == criterion_name.strip():
                            matched_criterion = criteria_name
                            break
                    
                    if matched_criterion:
                        if matched_criterion not in result[supplier_id]:
                            result[supplier_id][matched_criterion] = {
                                'scores': [],
                                'evaluations_count': 0
                            }
                        
                        result[supplier_id][matched_criterion]['scores'].append(score)
                        result[supplier_id][matched_criterion]['evaluations_count'] += 1
            
            # Calculate averages and confidence for survey scores
            for supplier_id in result:
                for criterion_name in result[supplier_id]:
                    scores = result[supplier_id][criterion_name]['scores']
                    avg_score = sum(scores) / len(scores)
                    count = len(scores)
                    
                    result[supplier_id][criterion_name] = {
                        'score': avg_score,
                        'evaluations_count': count,
                        'confidence': count,  # Show number of evaluations
                        'source': 'survey'
                    }
            
            return result
    
    def calculate_threshold_recommendations(self, criteria_names: List[str]) -> Dict[str, Dict]:
        """Calculate intelligent threshold recommendations for PROMETHEE II based on actual data"""
        recommendations = {}
        
        # Get current scores for all criteria from unified table
        aggregated_scores = self.get_unified_supplier_scores(criteria_names)
        
        # Define criteria types for specialized logic
        PROFILE_CRITERIA = {
            'Product/Service Type', 'Geographical Network', 'Method of Sourcing',
            'Investment in Equipment', 'Reciprocal Business', 'B-BBEE Level'
        }
        
        for criterion_name in criteria_names:
            # Collect all scores for this criterion
            scores = []
            for supplier_id, criteria_data in aggregated_scores.items():
                if criterion_name in criteria_data:
                    scores.append(criteria_data[criterion_name]['score'])
            
            if len(scores) < 2:
                # Fallback for insufficient data
                recommendations[criterion_name] = {
                    "indifference_threshold": 0.5,
                    "preference_threshold": 2.0,
                    "recommendation_method": "fallback",
                    "explanation": "Insufficient data - using default values",
                    "data_stats": {"count": len(scores)}
                }
                continue
            
            # Calculate basic statistics
            min_score = min(scores)
            max_score = max(scores)
            data_range = max_score - min_score
            mean_score = sum(scores) / len(scores)
            std_dev = (sum((x - mean_score) ** 2 for x in scores) / len(scores)) ** 0.5
            
            # Determine criterion type and apply specialized logic
            criterion_type = "profile" if criterion_name in PROFILE_CRITERIA else "survey"
            
            if criterion_type == "profile":
                recommendations[criterion_name] = self._calculate_profile_threshold(
                    criterion_name, scores, min_score, max_score, data_range, std_dev
                )
            else:
                recommendations[criterion_name] = self._calculate_survey_threshold(
                    criterion_name, scores, min_score, max_score, data_range, std_dev
                )
            
            # Add common statistics
            recommendations[criterion_name].update({
                "data_stats": {
                    "count": len(scores),
                    "min": round(min_score, 2),
                    "max": round(max_score, 2),
                    "range": round(data_range, 2),
                    "mean": round(mean_score, 2),
                    "std_dev": round(std_dev, 2)
                },
                "criterion_type": criterion_type
            })
        
        return recommendations
    
    def _calculate_profile_threshold(self, criterion_name: str, scores: List[float], 
                                   min_score: float, max_score: float, 
                                   data_range: float, std_dev: float) -> Dict:
        """Calculate thresholds for profile criteria with specialized logic"""
        
        if "B-BBEE" in criterion_name:
            # B-BBEE levels are discrete with meaningful differences
            return {
                "indifference_threshold": 2.0,
                "preference_threshold": 5.0,
                "recommendation_method": "discrete_levels",
                "explanation": "B-BBEE levels: 2pt indifference (within level group), 5pt preference (different groups)"
            }
        
        elif any(keyword in criterion_name for keyword in ["Network", "Type", "Sourcing"]):
            # Categorical-like scoring with moderate sensitivity
            indiff = max(1.0, data_range * 0.08)  # 8% of range
            pref = max(3.0, data_range * 0.25)    # 25% of range
            return {
                "indifference_threshold": round(indiff, 1),
                "preference_threshold": round(pref, 1),
                "recommendation_method": "categorical_profile",
                "explanation": f"Categorical profile: 8% range indifference, 25% range preference"
            }
        
        elif "Investment" in criterion_name or "Equipment" in criterion_name:
            # Binary or limited options, less sensitive
            indiff = max(0.5, data_range * 0.10)  # 10% of range
            pref = max(2.0, data_range * 0.40)    # 40% of range
            return {
                "indifference_threshold": round(indiff, 1),
                "preference_threshold": round(pref, 1),
                "recommendation_method": "binary_profile",
                "explanation": "Binary/limited options: 10% range indifference, 40% range preference"
            }
        
        else:
            # General profile criteria - moderate sensitivity
            indiff = max(0.5, data_range * 0.05)  # 5% of range
            pref = max(2.0, data_range * 0.20)    # 20% of range
            return {
                "indifference_threshold": round(indiff, 1),
                "preference_threshold": round(pref, 1),
                "recommendation_method": "general_profile",
                "explanation": "General profile: 5% range indifference, 20% range preference"
            }
    
    def _calculate_survey_threshold(self, criterion_name: str, scores: List[float],
                                  min_score: float, max_score: float,
                                  data_range: float, std_dev: float) -> Dict:
        """Calculate thresholds for survey criteria (subjective 1-10 scale)"""
        
        # Survey criteria are subjective ratings, use established psychological thresholds
        if data_range <= 1.0:
            # Very small range, use minimal thresholds
            return {
                "indifference_threshold": 0.2,
                "preference_threshold": 0.5,
                "recommendation_method": "narrow_survey",
                "explanation": "Narrow survey range: minimal differences considered"
            }
        else:
            # Standard survey scale sensitivity
            indiff = 0.5  # Half-point differences often negligible
            pref = min(2.0, data_range * 0.25)  # Quarter of range or 2 points max
            return {
                "indifference_threshold": round(indiff, 1),
                "preference_threshold": round(pref, 1),
                "recommendation_method": "standard_survey",
                "explanation": f"Standard survey: 0.5pt indifference, {round(pref, 1)}pt preference (25% of range)"
            }
    
    def get_threshold_recommendation_alternatives(self, criteria_names: List[str]) -> Dict[str, Dict]:
        """Get alternative threshold recommendation strategies"""
        base_recommendations = self.calculate_threshold_recommendations(criteria_names)
        alternatives = {}
        
        for criterion_name, base_rec in base_recommendations.items():
            data_range = base_rec["data_stats"]["range"]
            std_dev = base_rec["data_stats"]["std_dev"]
            
            alternatives[criterion_name] = {
                "conservative": {
                    "indifference_threshold": round(max(0.1, data_range * 0.10), 1),
                    "preference_threshold": round(max(1.0, data_range * 0.30), 1),
                    "description": "Less sensitive to small differences"
                },
                "sensitive": {
                    "indifference_threshold": round(max(0.1, data_range * 0.02), 1),
                    "preference_threshold": round(max(0.5, data_range * 0.10), 1),
                    "description": "More sensitive to small differences"
                },
                "standard_deviation": {
                    "indifference_threshold": round(max(0.1, std_dev * 0.5), 1),
                    "preference_threshold": round(max(0.5, std_dev * 1.5), 1),
                    "description": "Based on data variability"
                },
                "recommended": base_rec  # The main recommendation
            }
        
        return alternatives

    def get_supplier_evaluation_counts(self) -> Dict[int, int]:
        """Get the number of manager evaluations per supplier"""
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get count before clearing
            cursor.execute("SELECT COUNT(*) FROM supplier_evaluations")
            count_before = cursor.fetchone()[0]
            
            # Clear all supplier evaluations
            cursor.execute("DELETE FROM supplier_evaluations")
            conn.commit()
            
            # Trigger full re-migration after clearing all evaluations
            # All survey-based scores need to be recalculated (will become defaults)
            try:
                bwm_data = self.get_latest_bwm_weights()
                if bwm_data:
                    migration_result = self.migrate_to_unified_criteria_scores(bwm_data['criteria_names'])
                    print(f"Event-driven refresh: All supplier evaluations cleared, full re-migration triggered")
                    print(f"Re-migration stats: {migration_result.get('stats', {})}")
                else:
                    print("Warning: No BWM weights found for full re-migration after clearing evaluations")
            except Exception as e:
                # Don't fail the clear operation if re-migration fails
                print(f"Warning: Failed to trigger full re-migration after clearing evaluations: {e}")
            
            return {
                "message": "All supplier evaluations cleared successfully",
                "cleared_count": count_before
            }
    
    def delete_supplier_evaluation(self, evaluation_id: int) -> Dict[str, Any]:
        """Delete a specific supplier evaluation"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get supplier_id before deletion for refresh
            cursor.execute("SELECT supplier_id FROM supplier_evaluations WHERE id = ?", (evaluation_id,))
            result = cursor.fetchone()
            if not result:
                return {"success": False, "message": "Evaluation not found"}
            
            supplier_id = result[0]
            
            # Delete the evaluation
            cursor.execute("DELETE FROM supplier_evaluations WHERE id = ?", (evaluation_id,))
            conn.commit()
            
            # Trigger unified table refresh for affected supplier
            try:
                bwm_data = self.get_latest_bwm_weights()
                if bwm_data:
                    self.refresh_unified_scores_for_supplier(supplier_id, bwm_data['criteria_names'], "evaluation_deletion")
                    print(f"Event-driven refresh: Evaluation {evaluation_id} deleted for supplier {supplier_id}, unified scores refreshed")
                else:
                    print(f"Warning: No BWM weights found for unified scores refresh after deleting evaluation {evaluation_id}")
            except Exception as e:
                # Don't fail the deletion if refresh fails
                print(f"Warning: Failed to refresh unified scores for supplier {supplier_id} after deleting evaluation {evaluation_id}: {e}")
            
            return {
                "success": True,
                "message": "Supplier evaluation deleted successfully"
            }
    
    def save_profile_scoring_config(self, config_data: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Save profile scoring configuration to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing configuration
            cursor.execute("DELETE FROM profile_scoring_config")
            
            # Insert new configuration
            for criteria_name, options in config_data.items():
                for option_value, score in options.items():
                    cursor.execute("""
                        INSERT INTO profile_scoring_config 
                        (criteria_name, option_value, score, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, (criteria_name, option_value, float(score)))
            
            conn.commit()
            
            # Trigger full re-migration after scoring configuration changes
            # All existing suppliers need to be re-evaluated with the new scoring rules
            try:
                bwm_data = self.get_latest_bwm_weights()
                if bwm_data:
                    migration_result = self.migrate_to_unified_criteria_scores(bwm_data['criteria_names'])
                    print(f"Event-driven refresh: Profile scoring config updated, full re-migration triggered")
                    print(f"Re-migration stats: {migration_result.get('stats', {})}")
                else:
                    print("Warning: No BWM weights found for full re-migration after profile scoring config update")
            except Exception as e:
                # Don't fail the config save if re-migration fails, but log the issue
                print(f"Warning: Failed to trigger full re-migration after profile scoring config update: {e}")
            
            return {
                "success": True,
                "message": "Profile scoring configuration saved successfully"
            }
    
    def get_profile_scoring_config(self) -> Dict[str, Dict[str, float]]:
        """Get profile scoring configuration from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT criteria_name, option_value, score 
                FROM profile_scoring_config 
                ORDER BY criteria_name, option_value
            """)
            
            config = {}
            for row in cursor.fetchall():
                criteria_name, option_value, score = row
                if criteria_name not in config:
                    config[criteria_name] = {}
                config[criteria_name][option_value] = float(score)
            
            return config
    
    def get_supplier_profile_scores(self, supplier_id: int) -> Dict[str, float]:
        """Calculate numerical scores for a supplier's profile based on configuration"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get supplier profile data
            cursor.execute("""
                SELECT product_service_type, geographical_network, method_of_sourcing,
                       invest_in_refuelling_equipment, reciprocal_business, "B-BBEE_level"
                FROM suppliers WHERE id = ?
            """, (supplier_id,))
            
            supplier_data = cursor.fetchone()
            if not supplier_data:
                return {}
            
            # Get scoring configuration
            scoring_config = self.get_profile_scoring_config()
            
            # Calculate scores
            profile_scores = {}
            fields = [
                ('product_service_type', supplier_data[0]),
                ('geographical_network', supplier_data[1]),
                ('method_of_sourcing', supplier_data[2]),
                ('invest_in_refuelling_equipment', supplier_data[3]),
                ('reciprocal_business', supplier_data[4]),
                ('bbee_level', str(supplier_data[5]) if supplier_data[5] else None)
            ]
            
            for field_name, field_value in fields:
                if field_name in scoring_config and field_value in scoring_config[field_name]:
                    profile_scores[field_name] = scoring_config[field_name][field_value]
                else:
                    profile_scores[field_name] = 0.0  # Default score if no match
            
            return profile_scores
    
    def save_promethee_results(self, supplier_id: int, positive_flow: float, negative_flow: float,
                              net_flow: float, ranking: int, confidence_level: float,
                              criteria_weights: str) -> int:
        """Save PROMETHEE II results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO promethee_results 
                (supplier_id, positive_flow, negative_flow, net_flow, ranking, confidence_level, criteria_weights)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (supplier_id, positive_flow, negative_flow, net_flow, ranking, confidence_level, criteria_weights))
            return cursor.lastrowid
    
    def get_promethee_results(self) -> List[Dict]:
        """Get PROMETHEE II results"""
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
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
        with self.get_connection() as conn:
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
            
            # Count unique participants who participated
            cursor.execute("SELECT COUNT(DISTINCT participant_name) FROM supplier_evaluations WHERE participant_name IS NOT NULL")
            participants_participated = cursor.fetchone()[0]
            
            return {
                "total_evaluations": total_evaluations,
                "supplier_evaluations": supplier_evaluations,
                "suppliers_evaluated": suppliers_evaluated,
                "participants_participated": participants_participated
            }
    
    def save_bwm_weights(self, criteria_names: List[str], weights: Dict[str, float], 
                        best_criterion: str, worst_criterion: str, 
                        best_to_others: Dict[str, float], others_to_worst: Dict[str, float],
                        consistency_ratio: float, consistency_interpretation: str,
                        created_by: str = None) -> int:
        """Save BWM weights configuration to database"""
        with self.get_connection() as conn:
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
            bwm_id = cursor.lastrowid
            
            # Trigger full re-migration after BWM weights change
            # Criteria names or weights have changed, need to refresh entire unified table
            try:
                migration_result = self.migrate_to_unified_criteria_scores(criteria_names)
                print(f"Event-driven refresh: BWM weights updated, full re-migration triggered")
                print(f"New criteria: {criteria_names}")
                print(f"Re-migration stats: {migration_result.get('stats', {})}")
            except Exception as e:
                # Don't fail the BWM save if re-migration fails, but log the issue
                print(f"Warning: Failed to trigger full re-migration after BWM weights update: {e}")
            
            return bwm_id
    
    def get_latest_bwm_weights(self) -> Optional[Dict]:
        """Get the most recent BWM weights configuration"""
        with self.get_connection() as conn:
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
    
    def migrate_to_unified_criteria_scores(self, criteria_names: List[str]) -> Dict[str, Any]:
        """Migrate existing data to unified supplier_criteria_scores table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing unified scores
            cursor.execute("DELETE FROM supplier_criteria_scores")
            
            # Get all suppliers
            cursor.execute("SELECT id FROM suppliers")
            supplier_ids = [row[0] for row in cursor.fetchall()]
            
            migration_stats = {
                "suppliers_processed": 0,
                "profile_scores_added": 0,
                "survey_scores_added": 0,
                "default_scores_added": 0
            }
            
            for supplier_id in supplier_ids:
                migration_stats["suppliers_processed"] += 1
                
                # Populate profile scores
                profile_scores = self._get_profile_scores_for_supplier(supplier_id, criteria_names)
                for criterion_name, score_data in profile_scores.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO supplier_criteria_scores 
                        (supplier_id, criterion_name, score, data_source, score_count, last_updated)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (supplier_id, criterion_name, score_data['score'], 'profile', 1))
                    migration_stats["profile_scores_added"] += 1
                
                # Populate survey scores (aggregated)
                survey_scores = self._get_survey_scores_for_supplier(supplier_id, criteria_names)
                for criterion_name, score_data in survey_scores.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO supplier_criteria_scores 
                        (supplier_id, criterion_name, score, data_source, score_count, last_updated)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (supplier_id, criterion_name, score_data['score'], 'survey', score_data['count']))
                    migration_stats["survey_scores_added"] += 1
                
                # Add default scores for missing criteria
                existing_criteria = set(profile_scores.keys()) | set(survey_scores.keys())
                for criterion_name in criteria_names:
                    if criterion_name not in existing_criteria:
                        # Use a mid-range default score
                        default_score = 5.0  # Assuming 1-10 scale
                        cursor.execute("""
                            INSERT OR REPLACE INTO supplier_criteria_scores 
                            (supplier_id, criterion_name, score, data_source, score_count, last_updated)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (supplier_id, criterion_name, default_score, 'default', 0))
                        migration_stats["default_scores_added"] += 1
            
            conn.commit()
            
            return {
                "success": True,
                "message": "Migration completed successfully",
                "stats": migration_stats
            }
    
    def _get_profile_scores_for_supplier(self, supplier_id: int, criteria_names: List[str]) -> Dict[str, Dict]:
        """Get profile scores for a single supplier"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Define mapping from BWM criteria names to profile database columns
            criteria_column_mapping = {
                'B-BBEE Level': 'B-BBEE Level',  # Fixed: use consistent naming
                'Geographical Network': 'geographical_network', 
                'Method of Sourcing': 'method_of_sourcing',
                'Product/Service Type': 'product_service_type',
                'Investment in Equipment': 'invest_in_refuelling_equipment',
                'Reciprocal Business': 'reciprocal_business'
            }
            
            # Get supplier profile data
            cursor.execute("""
                SELECT "B-BBEE_level", geographical_network, method_of_sourcing, 
                       product_service_type, invest_in_refuelling_equipment, reciprocal_business
                FROM suppliers WHERE id = ?
            """, (supplier_id,))
            
            supplier_data = cursor.fetchone()
            if not supplier_data:
                return {}
            
            # Get scoring configuration
            scoring_config = self.get_profile_scoring_config()
            
            # Calculate scores
            profile_scores = {}
            fields = [
                ('product_service_type', supplier_data[3]),
                ('geographical_network', supplier_data[1]),
                ('method_of_sourcing', supplier_data[2]),
                ('invest_in_refuelling_equipment', supplier_data[4]),
                ('reciprocal_business', supplier_data[5]),
                ('B-BBEE Level', supplier_data[0])  # Fixed: use consistent naming and raw integer
            ]
            
            for config_name, value in fields:
                # Find matching BWM criterion name
                bwm_criterion = None
                for bwm_name, db_column in criteria_column_mapping.items():
                    if db_column == config_name or config_name in db_column:
                        bwm_criterion = bwm_name
                        break
                
                if bwm_criterion and bwm_criterion in criteria_names and value is not None:
                    # Special handling for B-BBEE Level - convert integer to expected string format
                    converted_value = value
                    if config_name == 'B-BBEE Level' and isinstance(value, (int, float)):
                        if value >= 5:
                            converted_value = "Level 5+"
                        else:
                            converted_value = f"Level {int(value)}"
                    
                    if config_name in scoring_config and converted_value in scoring_config[config_name]:
                        score = scoring_config[config_name][converted_value]
                        profile_scores[bwm_criterion] = {
                            'score': score,
                            'source': 'profile',
                            'raw_value': value
                        }
            
            return profile_scores
    
    def _get_survey_scores_for_supplier(self, supplier_id: int, criteria_names: List[str]) -> Dict[str, Dict]:
        """Get aggregated survey scores for a single supplier"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all evaluations for this supplier
            cursor.execute("""
                SELECT criteria_scores
                FROM supplier_evaluations
                WHERE supplier_id = ?
            """, (supplier_id,))
            
            # Aggregate scores
            aggregated_scores = {}
            for row in cursor.fetchall():
                criteria_scores = json.loads(row[0])
                
                for criterion_name, score in criteria_scores.items():
                    # Find matching criterion name in the criteria_names list (may have spaces)
                    matched_criterion = None
                    for criteria_name in criteria_names:
                        if criteria_name.strip() == criterion_name.strip():
                            matched_criterion = criteria_name
                            break
                    
                    if matched_criterion:
                        if matched_criterion not in aggregated_scores:
                            aggregated_scores[matched_criterion] = []
                        aggregated_scores[matched_criterion].append(float(score))
            
            # Calculate averages
            result = {}
            for criterion_name, scores in aggregated_scores.items():
                if scores:  # Only include if there are actual scores
                    avg_score = sum(scores) / len(scores)
                    result[criterion_name] = {
                        'score': round(avg_score, 2),
                        'count': len(scores),
                        'source': 'survey'
                    }
            
            return result
    
    def get_unified_supplier_scores(self, criteria_names: List[str]) -> Dict[int, Dict[str, Dict]]:
        """Get all supplier scores from unified table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build criteria filter
            criteria_placeholders = ','.join(['?' for _ in criteria_names])
            
            cursor.execute(f"""
                SELECT supplier_id, criterion_name, score, data_source, score_count
                FROM supplier_criteria_scores
                WHERE criterion_name IN ({criteria_placeholders})
                ORDER BY supplier_id, criterion_name
            """, criteria_names)
            
            result = {}
            for row in cursor.fetchall():
                supplier_id, criterion_name, score, data_source, score_count = row
                
                if supplier_id not in result:
                    result[supplier_id] = {}
                
                result[supplier_id][criterion_name] = {
                    'score': score,
                    'source': data_source,
                    'count': score_count
                }
            
            return result
    
    def update_supplier_criteria_score(self, supplier_id: int, criterion_name: str, 
                                     score: float, data_source: str = 'manual') -> bool:
        """Update a single supplier criteria score"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO supplier_criteria_scores 
                (supplier_id, criterion_name, score, data_source, score_count, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (supplier_id, criterion_name, score, data_source, 1))
            
            success = cursor.rowcount > 0
            
            # Refresh unified scores for this supplier if profile was updated
            if success and data_source == 'profile':
                try:
                    # Get current BWM criteria names to refresh properly
                    bwm_data = self.get_latest_bwm_weights()
                    if bwm_data:
                        self.refresh_unified_scores_for_supplier(supplier_id, bwm_data['criteria_names'], "manual_score_update")
                except Exception as e:
                    # Don't fail the profile update if refresh fails
                    print(f"Warning: Failed to refresh unified scores for supplier {supplier_id}: {e}")
            
            return success
    
    def refresh_unified_scores_for_supplier(self, supplier_id: int, criteria_names: List[str], 
                                           trigger_source: str = "manual") -> bool:
        """Refresh unified scores for a specific supplier when their data changes"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Remove existing scores for this supplier
                cursor.execute("DELETE FROM supplier_criteria_scores WHERE supplier_id = ?", (supplier_id,))
                
                # Get fresh profile and survey scores
                profile_scores = self._get_profile_scores_for_supplier(supplier_id, criteria_names)
                survey_scores = self._get_survey_scores_for_supplier(supplier_id, criteria_names)
                
                records_added = 0
                
                # Insert profile scores
                for criterion_name, score_data in profile_scores.items():
                    cursor.execute("""
                        INSERT INTO supplier_criteria_scores 
                        (supplier_id, criterion_name, score, data_source, score_count, last_updated)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (supplier_id, criterion_name, score_data['score'], 'profile', 1))
                    records_added += 1
                
                # Insert survey scores (these override profile scores for the same criteria)
                for criterion_name, score_data in survey_scores.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO supplier_criteria_scores 
                        (supplier_id, criterion_name, score, data_source, score_count, last_updated)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (supplier_id, criterion_name, score_data['score'], 'survey', score_data['count']))
                    records_added += 1
                
                # Add default scores for missing criteria
                existing_criteria = set(profile_scores.keys()) | set(survey_scores.keys())
                for criterion_name in criteria_names:
                    if criterion_name not in existing_criteria:
                        cursor.execute("""
                            INSERT INTO supplier_criteria_scores 
                            (supplier_id, criterion_name, score, data_source, score_count, last_updated)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (supplier_id, criterion_name, 5.0, 'default', 0))
                        records_added += 1
                
                conn.commit()
                
                # Log successful operation
                self._log_unified_scores_operation(
                    operation_type="supplier_refresh",
                    trigger_source=trigger_source,
                    supplier_id=supplier_id,
                    criteria_affected=criteria_names,
                    records_affected=records_added,
                    success=True
                )
                
                return True
                
        except Exception as e:
            # Log failed operation
            self._log_unified_scores_operation(
                operation_type="supplier_refresh",
                trigger_source=trigger_source,
                supplier_id=supplier_id,
                criteria_affected=criteria_names,
                records_affected=0,
                success=False,
                error_message=str(e)
            )
            raise
    
    def ensure_unified_scores_populated(self, criteria_names: List[str]) -> Dict[str, Any]:
        """Ensure unified scores table is populated, migrate if empty"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if table has any data
            cursor.execute("SELECT COUNT(*) FROM supplier_criteria_scores")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Table is empty, run migration
                return self.migrate_to_unified_criteria_scores(criteria_names)
            else:
                # Check if we have data for all current criteria
                cursor.execute("""
                    SELECT DISTINCT criterion_name 
                    FROM supplier_criteria_scores
                """)
                existing_criteria = {row[0] for row in cursor.fetchall()}
                missing_criteria = set(criteria_names) - existing_criteria
                
                if missing_criteria:
                    # Re-run migration to add missing criteria
                    return self.migrate_to_unified_criteria_scores(criteria_names)
                else:
                    return {
                        "success": True,
                        "message": "Unified scores already populated",
                        "existing_records": count
                    }
    
    def _log_unified_scores_operation(self, operation_type: str, trigger_source: str, 
                                    supplier_id: int = None, criteria_affected: List[str] = None,
                                    records_affected: int = 0, success: bool = True, 
                                    error_message: str = None):
        """Log unified scores refresh operations for audit trail"""
        try:
            with self.get_connection(timeout=10.0, retries=2) as conn:  # Shorter timeout for logging
                
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO unified_scores_audit_log 
                    (operation_type, supplier_id, criteria_affected, trigger_source, 
                     records_affected, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    operation_type,
                    supplier_id,
                    json.dumps(criteria_affected) if criteria_affected else None,
                    trigger_source,
                    records_affected,
                    success,
                    error_message
                ))
                conn.commit()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                # Skip logging if database is locked to prevent blocking main operations
                print(f"Warning: Failed to log unified scores operation: database is locked")
            else:
                print(f"Warning: Failed to log unified scores operation: {e}")
        except Exception as e:
            # Don't fail operations if audit logging fails
            print(f"Warning: Failed to log unified scores operation: {e}")
    
    def get_unified_scores_audit_log(self, limit: int = 50) -> List[Dict]:
        """Get recent audit log entries for unified scores operations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT operation_type, supplier_id, criteria_affected, trigger_source,
                       records_affected, success, error_message, timestamp
                FROM unified_scores_audit_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def check_unified_scores_freshness(self, criteria_names: List[str]) -> Dict[str, Any]:
        """Check if unified scores table is up-to-date with source data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get latest update times from source tables
            cursor.execute("SELECT MAX(created_at) FROM bwm_weights")
            latest_bwm_update = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(submitted_at) FROM supplier_evaluations")
            latest_evaluation_update = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(updated_at) FROM profile_scoring_config")
            latest_config_update = cursor.fetchone()[0]
            
            # Get latest unified table update
            cursor.execute("SELECT MAX(last_updated) FROM supplier_criteria_scores")
            latest_unified_update = cursor.fetchone()[0]
            
            # Check for missing suppliers in unified table
            cursor.execute("""
                SELECT COUNT(*) FROM suppliers s
                WHERE s.id NOT IN (
                    SELECT DISTINCT supplier_id FROM supplier_criteria_scores
                )
            """)
            missing_suppliers = cursor.fetchone()[0]
            
            # Check for missing criteria in unified table
            cursor.execute("SELECT DISTINCT criterion_name FROM supplier_criteria_scores")
            existing_criteria = {row[0] for row in cursor.fetchall()}
            missing_criteria = set(criteria_names) - existing_criteria
            
            # Determine if refresh is needed
            needs_refresh = (
                missing_suppliers > 0 or
                len(missing_criteria) > 0 or
                (latest_bwm_update and latest_unified_update and latest_bwm_update > latest_unified_update) or
                (latest_evaluation_update and latest_unified_update and latest_evaluation_update > latest_unified_update) or
                (latest_config_update and latest_unified_update and latest_config_update > latest_unified_update)
            )
            
            return {
                "needs_refresh": needs_refresh,
                "latest_bwm_update": latest_bwm_update,
                "latest_evaluation_update": latest_evaluation_update,
                "latest_config_update": latest_config_update,
                "latest_unified_update": latest_unified_update,
                "missing_suppliers": missing_suppliers,
                "missing_criteria": list(missing_criteria),
                "existing_criteria": list(existing_criteria)
            }