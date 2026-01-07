#!/usr/bin/env python3
"""
Query parsing errors from the database for the Electron UI.
Returns JSON to stdout.
"""
import json
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from database import ImportDatabase


def main():
    parser = argparse.ArgumentParser(description='Query parsing errors from database')
    parser.add_argument('--run-id', type=int, help='Filter by specific run ID')
    parser.add_argument('--stage', type=str, help='Filter by stage (parsing, transform, notion_upload)')
    parser.add_argument('--summary', action='store_true', help='Return summary only')
    parser.add_argument('--runs-with-errors', action='store_true', help='List runs that have errors')
    args = parser.parse_args()
    
    db = ImportDatabase()
    
    try:
        if args.runs_with_errors:
            # Get all runs with errors
            result = {
                'type': 'runs_with_errors',
                'data': db.get_runs_with_errors()
            }
        elif args.summary:
            # Get summary
            run_id = args.run_id if args.run_id else None
            summary = db.get_parsing_errors_summary(run_id)
            error_types = db.get_error_type_summary(run_id)
            result = {
                'type': 'summary',
                'data': {
                    'counts': summary,
                    'by_error_type': error_types
                }
            }
        else:
            # Get errors list
            run_id = args.run_id if args.run_id else None
            
            if args.stage:
                errors = db.get_parsing_errors_by_stage(args.stage, run_id)
            else:
                errors = db.get_parsing_errors(run_id)
            
            # Also get summary
            summary = db.get_parsing_errors_summary(run_id)
            
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
        db.close()


if __name__ == '__main__':
    main()

