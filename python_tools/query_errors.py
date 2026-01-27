#!/usr/bin/env python3
"""
Query parsing errors from the database for the Electron UI.
Returns JSON to stdout.

This is a standalone script that directly queries the SQLite database
without importing the full src package (avoids relative import issues).
"""
import json
import sys
import argparse
import sqlite3
from pathlib import Path


def get_db_path():
    """Get path to import_history.db"""
    # Check if running from packaged app
    import os
    if 'APP_RESOURCE_PATH' in os.environ:
        return Path(os.environ['APP_RESOURCE_PATH']) / 'out' / 'import_history.db'
    # Development mode - look relative to this script
    return Path(__file__).resolve().parents[1] / 'out' / 'import_history.db'


def get_parsing_errors(conn, run_id=None, stage=None):
    """Get parsing errors from database"""
    cursor = conn.cursor()
    
    if run_id and stage:
        cursor.execute('''
            SELECT * FROM parsing_errors 
            WHERE run_id = ? AND stage = ?
            ORDER BY timestamp
        ''', (run_id, stage))
    elif run_id:
        cursor.execute('''
            SELECT * FROM parsing_errors 
            WHERE run_id = ?
            ORDER BY timestamp
        ''', (run_id,))
    elif stage:
        cursor.execute('''
            SELECT * FROM parsing_errors 
            WHERE stage = ?
            ORDER BY run_id DESC, timestamp
        ''', (stage,))
    else:
        cursor.execute('''
            SELECT * FROM parsing_errors 
            ORDER BY run_id DESC, timestamp DESC
            LIMIT 100
        ''')
    
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_parsing_errors_summary(conn, run_id=None):
    """Get summary of parsing errors"""
    cursor = conn.cursor()
    
    if run_id:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN stage = 'parsing' THEN 1 ELSE 0 END) as parsing_count,
                SUM(CASE WHEN stage = 'transform' THEN 1 ELSE 0 END) as transform_count,
                SUM(CASE WHEN stage = 'notion_upload' THEN 1 ELSE 0 END) as upload_count
            FROM parsing_errors
            WHERE run_id = ?
        ''', (run_id,))
    else:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN stage = 'parsing' THEN 1 ELSE 0 END) as parsing_count,
                SUM(CASE WHEN stage = 'transform' THEN 1 ELSE 0 END) as transform_count,
                SUM(CASE WHEN stage = 'notion_upload' THEN 1 ELSE 0 END) as upload_count
            FROM parsing_errors
        ''')
    
    row = cursor.fetchone()
    if row:
        return {
            'total': row[0] or 0,
            'parsing_count': row[1] or 0,
            'transform_count': row[2] or 0,
            'upload_count': row[3] or 0
        }
    return {'total': 0, 'parsing_count': 0, 'transform_count': 0, 'upload_count': 0}


def get_runs_with_errors(conn):
    """Get all runs that have parsing errors"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            ir.id as run_id,
            ir.timestamp,
            ir.total_pages,
            COUNT(pe.id) as error_count,
            SUM(CASE WHEN pe.stage = 'parsing' THEN 1 ELSE 0 END) as parsing_errors,
            SUM(CASE WHEN pe.stage = 'transform' THEN 1 ELSE 0 END) as transform_errors,
            SUM(CASE WHEN pe.stage = 'notion_upload' THEN 1 ELSE 0 END) as upload_errors
        FROM import_runs ir
        LEFT JOIN parsing_errors pe ON ir.id = pe.run_id
        GROUP BY ir.id
        HAVING error_count > 0
        ORDER BY ir.timestamp DESC
    ''')
    
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def main():
    parser = argparse.ArgumentParser(description='Query parsing errors from database')
    parser.add_argument('--run-id', type=int, help='Filter by specific run ID')
    parser.add_argument('--stage', type=str, help='Filter by stage (parsing, transform, notion_upload)')
    parser.add_argument('--summary', action='store_true', help='Return summary only')
    parser.add_argument('--runs-with-errors', action='store_true', help='List runs that have errors')
    args = parser.parse_args()
    
    db_path = get_db_path()
    
    if not db_path.exists():
        print(json.dumps({
            'type': 'errors',
            'data': {
                'errors': [],
                'summary': {'total': 0, 'parsing_count': 0, 'transform_count': 0, 'upload_count': 0}
            }
        }))
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        
        if args.runs_with_errors:
            result = {
                'type': 'runs_with_errors',
                'data': get_runs_with_errors(conn)
            }
        elif args.summary:
            run_id = args.run_id if args.run_id else None
            result = {
                'type': 'summary',
                'data': {
                    'counts': get_parsing_errors_summary(conn, run_id)
                }
            }
        else:
            run_id = args.run_id if args.run_id else None
            stage = args.stage if args.stage else None
            errors = get_parsing_errors(conn, run_id, stage)
            summary = get_parsing_errors_summary(conn, run_id)
            
            result = {
                'type': 'errors',
                'data': {
                    'errors': errors,
                    'summary': summary
                }
            }
        
        print(json.dumps(result, default=str))
        
    except Exception as e:
        print(json.dumps({
            'type': 'error',
            'message': str(e)
        }))
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == '__main__':
    main()
