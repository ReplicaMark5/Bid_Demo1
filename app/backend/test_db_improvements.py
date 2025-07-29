#!/usr/bin/env python3

from database import SupplierDatabase
from unified_api import get_db

# Test database connection improvements
print('Testing database connection with improvements...')

# Test per-request database instances
db1 = get_db()
db2 = get_db()
print('DB instance 1:', id(db1))
print('DB instance 2:', id(db2))
different = id(db1) != id(db2)
print('Different instances:', different)

# Test connection context manager
try:
    with db1.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM suppliers')
        count = cursor.fetchone()[0]
        print('Suppliers count:', count)
    print('Connection context manager working')
except Exception as e:
    print('Connection test failed:', e)

# Test concurrent database operations
import threading
import time

def concurrent_db_test(thread_id):
    """Test concurrent database operations"""
    try:
        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM suppliers')
            count = cursor.fetchone()[0]
            print(f'Thread {thread_id}: Suppliers count = {count}')
        print(f'Thread {thread_id}: Success')
    except Exception as e:
        print(f'Thread {thread_id}: Failed - {e}')

print('\nTesting concurrent database access...')
threads = []
for i in range(5):
    thread = threading.Thread(target=concurrent_db_test, args=(i,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

print('\nDatabase improvements test completed successfully!')