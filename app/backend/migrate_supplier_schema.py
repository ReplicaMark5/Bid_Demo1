#!/usr/bin/env python3
"""
Database migration script to add new profile columns to the suppliers table.
This script handles the addition of new fields for supplier profile information.
"""

import sqlite3
import os
import sys

def migrate_supplier_schema(db_path="supplier_data.db"):
    """
    Migrate the supplier schema to include new fields for profile information.
    
    New fields added:
    - company_profile: TEXT
    - annual_revenue: REAL
    - number_of_employees: INTEGER
    - bbee_level: INTEGER (1-8)
    - black_ownership_percent: REAL
    - black_female_ownership_percent: REAL
    - bbee_compliant: BOOLEAN
    - cipc_cor_documents: TEXT
    - tax_certificate: TEXT
    - fuel_products_offered: TEXT
    - product_service_type: TEXT
    - geographical_network: TEXT
    - delivery_types_offered: TEXT
    - method_of_sourcing: TEXT
    - invest_in_refuelling_equipment: TEXT
    - reciprocal_business: TEXT
    """
    
    print(f"Starting migration for database: {db_path}")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Warning: Database {db_path} does not exist. Creating new database with updated schema.")
        # If database doesn't exist, create it with the new schema
        from database import SupplierDatabase
        db = SupplierDatabase(db_path)
        print("✅ New database created with updated schema")
        return
    
    # Connect to existing database
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(suppliers)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Current suppliers table columns: {column_names}")
        
        # List of new columns to add
        new_columns = [
            ("company_profile", "TEXT"),
            ("annual_revenue", "REAL"),
            ("number_of_employees", "INTEGER"),
            ("bbee_level", "INTEGER"),
            ("black_ownership_percent", "REAL"),
            ("black_female_ownership_percent", "REAL"),
            ("bbee_compliant", "BOOLEAN"),
            ("cipc_cor_documents", "TEXT"),
            ("tax_certificate", "TEXT"),
            ("fuel_products_offered", "TEXT"),
            ("product_service_type", "TEXT"),
            ("geographical_network", "TEXT"),
            ("delivery_types_offered", "TEXT"),
            ("method_of_sourcing", "TEXT"),
            ("invest_in_refuelling_equipment", "TEXT"),
            ("reciprocal_business", "TEXT")
        ]
        
        # Add missing columns
        for col_name, col_type in new_columns:
            if col_name not in column_names:
                print(f"Adding column: {col_name} ({col_type})")
                cursor.execute(f"ALTER TABLE suppliers ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column {col_name} already exists, skipping")
        
        conn.commit()
        
        # Verify the updated schema
        cursor.execute("PRAGMA table_info(suppliers)")
        updated_columns = cursor.fetchall()
        updated_column_names = [col[1] for col in updated_columns]
        
        print(f"Updated suppliers table columns: {updated_column_names}")
        print("✅ Migration completed successfully")

def main():
    """Main function to run the migration"""
    db_path = "supplier_data.db"
    
    # Check if a custom database path is provided
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    try:
        migrate_supplier_schema(db_path)
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()