#!/usr/bin/env python3
"""
Database migration script to restructure depot_evaluations table.
This script converts the current table structure (multiple rows per evaluation)
to a new structure (single row per evaluation with JSON criteria scores).
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List

def migrate_depot_evaluations_schema(db_path: str = "supplier_data.db"):
    """
    Migrate depot_evaluations table to store criteria scores as JSON
    """
    print("Starting depot_evaluations schema migration...")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Step 1: Create new table structure
        print("Creating new depot_evaluations table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS depot_evaluations_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depot_id INTEGER NOT NULL,
                supplier_id INTEGER NOT NULL,
                manager_name TEXT,
                manager_email TEXT,
                criteria_scores TEXT NOT NULL,  -- JSON format: {"criterion1": score1, "criterion2": score2, ...}
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (depot_id) REFERENCES depots (id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
                UNIQUE(depot_id, supplier_id, manager_name, manager_email)
            )
        """)
        
        # Step 2: Check if old table exists and has data
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='depot_evaluations'")
        if not cursor.fetchone():
            print("No existing depot_evaluations table found. Creating new empty table...")
            cursor.execute("ALTER TABLE depot_evaluations_new RENAME TO depot_evaluations")
            conn.commit()
            return
        
        # Step 3: Get existing data grouped by evaluation (depot_id, supplier_id, manager)
        print("Retrieving existing evaluation data...")
        cursor.execute("""
            SELECT depot_id, supplier_id, manager_name, manager_email, 
                   criterion_name, score, submitted_at
            FROM depot_evaluations
            ORDER BY depot_id, supplier_id, manager_name, manager_email, submitted_at
        """)
        
        existing_data = cursor.fetchall()
        
        # Step 4: Group criteria by evaluation
        evaluations = {}
        for row in existing_data:
            depot_id, supplier_id, manager_name, manager_email, criterion_name, score, submitted_at = row
            
            # Create evaluation key
            eval_key = (depot_id, supplier_id, manager_name, manager_email)
            
            if eval_key not in evaluations:
                evaluations[eval_key] = {
                    'depot_id': depot_id,
                    'supplier_id': supplier_id,
                    'manager_name': manager_name,
                    'manager_email': manager_email,
                    'criteria_scores': {},
                    'submitted_at': submitted_at
                }
            
            # Add criterion score
            evaluations[eval_key]['criteria_scores'][criterion_name] = score
        
        # Step 5: Insert migrated data into new table
        print(f"Migrating {len(evaluations)} evaluations...")
        for eval_data in evaluations.values():
            criteria_scores_json = json.dumps(eval_data['criteria_scores'])
            
            cursor.execute("""
                INSERT INTO depot_evaluations_new 
                (depot_id, supplier_id, manager_name, manager_email, criteria_scores, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                eval_data['depot_id'],
                eval_data['supplier_id'],
                eval_data['manager_name'],
                eval_data['manager_email'],
                criteria_scores_json,
                eval_data['submitted_at']
            ))
        
        # Step 6: Replace old table with new one
        print("Replacing old table with new structure...")
        cursor.execute("DROP TABLE depot_evaluations")
        cursor.execute("ALTER TABLE depot_evaluations_new RENAME TO depot_evaluations")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Step 7: Verify migration
        cursor.execute("SELECT COUNT(*) FROM depot_evaluations")
        new_count = cursor.fetchone()[0]
        print(f"New table has {new_count} evaluation records")
        
        # Show sample data
        cursor.execute("SELECT * FROM depot_evaluations LIMIT 3")
        sample_data = cursor.fetchall()
        print("Sample migrated data:")
        for row in sample_data:
            print(f"  ID: {row[0]}, Depot: {row[1]}, Supplier: {row[2]}, Manager: {row[3]}")
            criteria_scores = json.loads(row[5])
            print(f"    Criteria: {criteria_scores}")

def rollback_migration(db_path: str = "supplier_data.db"):
    """
    Rollback the migration by converting JSON criteria back to individual rows
    """
    print("Rolling back depot_evaluations schema migration...")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Step 1: Create old table structure
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS depot_evaluations_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depot_id INTEGER NOT NULL,
                supplier_id INTEGER NOT NULL,
                criterion_name TEXT NOT NULL,
                score REAL NOT NULL,
                manager_name TEXT,
                manager_email TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (depot_id) REFERENCES depots (id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
                UNIQUE(depot_id, supplier_id, criterion_name)
            )
        """)
        
        # Step 2: Get current data
        cursor.execute("SELECT * FROM depot_evaluations")
        current_data = cursor.fetchall()
        
        # Step 3: Convert JSON criteria back to individual rows
        for row in current_data:
            id, depot_id, supplier_id, manager_name, manager_email, criteria_scores_json, submitted_at = row
            criteria_scores = json.loads(criteria_scores_json)
            
            for criterion_name, score in criteria_scores.items():
                cursor.execute("""
                    INSERT INTO depot_evaluations_old 
                    (depot_id, supplier_id, criterion_name, score, manager_name, manager_email, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (depot_id, supplier_id, criterion_name, score, manager_name, manager_email, submitted_at))
        
        # Step 4: Replace current table with old structure
        cursor.execute("DROP TABLE depot_evaluations")
        cursor.execute("ALTER TABLE depot_evaluations_old RENAME TO depot_evaluations")
        
        conn.commit()
        print("Rollback completed successfully!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        migrate_depot_evaluations_schema()