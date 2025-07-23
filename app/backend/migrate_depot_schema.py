#!/usr/bin/env python3
"""
Database migration script to add new columns to the depots table.
This script handles the addition of new fields for expanded depot information.
"""

import sqlite3
import os
import sys

def migrate_depot_schema(db_path="supplier_data.db"):
    """
    Migrate the depot schema to include new fields for expanded depot information.
    
    New fields added:
    - country: TEXT
    - town: TEXT  
    - lats: REAL (latitude)
    - longs: REAL (longitude)
    - fuel_zone: TEXT
    - tankage_size: REAL
    - number_of_pumps: INTEGER
    - equipment_value: REAL
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
        cursor.execute("PRAGMA table_info(depots)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Current depot table columns: {column_names}")
        
        # List of new columns to add
        new_columns = [
            ("country", "TEXT"),
            ("town", "TEXT"),
            ("lats", "REAL"),
            ("longs", "REAL"),
            ("fuel_zone", "TEXT"),
            ("tankage_size", "REAL"),
            ("number_of_pumps", "INTEGER"),
            ("equipment_value", "REAL")
        ]
        
        # Add missing columns
        for col_name, col_type in new_columns:
            if col_name not in column_names:
                print(f"Adding column: {col_name} ({col_type})")
                cursor.execute(f"ALTER TABLE depots ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column {col_name} already exists, skipping")
        
        conn.commit()
        
        # Verify the updated schema
        cursor.execute("PRAGMA table_info(depots)")
        updated_columns = cursor.fetchall()
        updated_column_names = [col[1] for col in updated_columns]
        
        print(f"Updated depot table columns: {updated_column_names}")
        print("✅ Migration completed successfully")

def main():
    """Main function to run the migration"""
    db_path = "supplier_data.db"
    
    # Check if a custom database path is provided
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    try:
        migrate_depot_schema(db_path)
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()