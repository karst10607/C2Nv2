import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .constants import DEFAULT_RECENT_RUNS_LIMIT, MAX_RETRY_COUNT


class ImportDatabase:
    """SQLite database for tracking imports and failed images"""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).resolve().parents[1] / 'out' / 'import_history.db'
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema"""
        with self.conn:
            # Import runs table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS import_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    version TEXT,
                    total_pages INTEGER,
                    total_images INTEGER,
                    successful_pages INTEGER,
                    verified_images INTEGER,
                    duration_seconds INTEGER
                )
            ''')
            
            # Failed pages table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS failed_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    file_path TEXT NOT NULL,
                    page_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    expected_images INTEGER NOT NULL,
                    verified_images INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_timestamp TEXT,
                    last_error TEXT,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (run_id) REFERENCES import_runs(id)
                )
            ''')
            
            # Page authors/editors table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS page_authors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    page_id TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    role TEXT NOT NULL,  -- 'creator' or 'editor'
                    FOREIGN KEY (run_id) REFERENCES import_runs(id)
                )
            ''')
            
            # Create indexes for fast queries
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_failed_status 
                ON failed_pages(status, retry_count)
            ''')
            
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_page_id 
                ON failed_pages(page_id)
            ''')
            
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_author_name 
                ON page_authors(author_name)
            ''')
            
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_author_role 
                ON page_authors(role)
            ''')
            
            # Parsing/conversion errors table - tracks files that failed to parse or transform
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS parsing_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    file_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    traceback TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES import_runs(id)
                )
            ''')
            
            self.conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_parsing_errors_run 
                ON parsing_errors(run_id)
            ''')
    
    def start_import_run(self, version: str, total_pages: int, total_images: int) -> int:
        """Record the start of an import run, return run_id"""
        cursor = self.conn.execute('''
            INSERT INTO import_runs 
            (timestamp, version, total_pages, total_images, successful_pages, verified_images, duration_seconds)
            VALUES (?, ?, ?, ?, 0, 0, 0)
        ''', (datetime.now().isoformat(), version, total_pages, total_images))
        self.conn.commit()
        return cursor.lastrowid
    
    def finish_import_run(self, run_id: int, successful_pages: int, verified_images: int, duration_seconds: int):
        """Update import run with final statistics"""
        with self.conn:
            self.conn.execute('''
                UPDATE import_runs 
                SET successful_pages = ?, verified_images = ?, duration_seconds = ?
                WHERE id = ?
            ''', (successful_pages, verified_images, duration_seconds, run_id))
    
    def add_failed_page(self, run_id: int, file_path: str, page_id: str, title: str, 
                       expected_images: int, verified_images: int = 0, error: str = ''):
        """Record a page with failed/unverified images"""
        with self.conn:
            self.conn.execute('''
                INSERT INTO failed_pages 
                (run_id, file_path, page_id, title, expected_images, verified_images, last_error, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (run_id, file_path, page_id, title, expected_images, verified_images, error))
    
    def get_pending_retries(self, max_retry_count: int = MAX_RETRY_COUNT) -> List[Dict[str, Any]]:
        """Get pages that need retry (status=pending, retry_count < max)"""
        cursor = self.conn.execute('''
            SELECT id, file_path, page_id, title, expected_images, verified_images, retry_count
            FROM failed_pages
            WHERE status = 'pending' AND retry_count < ?
            ORDER BY retry_count ASC, id ASC
        ''', (max_retry_count,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_failed_pages_summary(self) -> Dict[str, Any]:
        """Get summary of failed pages"""
        cursor = self.conn.execute('''
            SELECT 
                COUNT(*) as total_failed,
                SUM(CASE WHEN retry_count = 0 THEN 1 ELSE 0 END) as never_retried,
                SUM(CASE WHEN retry_count >= 3 THEN 1 ELSE 0 END) as max_retries,
                SUM(expected_images - verified_images) as missing_images
            FROM failed_pages
            WHERE status = 'pending'
        ''')
        
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def update_retry_attempt(self, page_db_id: int, verified_images: int, success: bool, error: str = ''):
        """Update a page after retry attempt"""
        status = 'resolved' if success else 'pending'
        
        with self.conn:
            self.conn.execute('''
                UPDATE failed_pages
                SET retry_count = retry_count + 1,
                    verified_images = ?,
                    last_retry_timestamp = ?,
                    last_error = ?,
                    status = ?
                WHERE id = ?
            ''', (verified_images, datetime.now().isoformat(), error, status, page_db_id))
    
    def mark_resolved(self, page_db_id: int):
        """Mark a failed page as resolved"""
        with self.conn:
            self.conn.execute('''
                UPDATE failed_pages SET status = 'resolved' WHERE id = ?
            ''', (page_db_id,))
    
    def get_recent_runs(self, limit: int = DEFAULT_RECENT_RUNS_LIMIT) -> List[Dict[str, Any]]:
        """Get recent import runs"""
        cursor = self.conn.execute('''
            SELECT * FROM import_runs
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def add_page_authors(self, run_id: int, page_id: str, created_by: Optional[str] = None, 
                         last_modified_by: Optional[str] = None):
        """Record author/editor information for a page"""
        with self.conn:
            if created_by:
                self.conn.execute('''
                    INSERT INTO page_authors (run_id, page_id, author_name, role)
                    VALUES (?, ?, ?, 'creator')
                ''', (run_id, page_id, created_by))
            
            if last_modified_by:
                self.conn.execute('''
                    INSERT INTO page_authors (run_id, page_id, author_name, role)
                    VALUES (?, ?, ?, 'editor')
                ''', (run_id, page_id, last_modified_by))
    
    def get_author_statistics(self) -> List[Dict[str, Any]]:
        """
        Get author statistics sorted by total count (most frequent first).
        
        Returns list of dicts with:
        - author_name: Name of the author/editor
        - total_count: Total number of pages they created/edited
        - creator_count: Number of pages they created
        - editor_count: Number of pages they edited
        """
        cursor = self.conn.execute('''
            SELECT 
                author_name,
                COUNT(*) as total_count,
                SUM(CASE WHEN role = 'creator' THEN 1 ELSE 0 END) as creator_count,
                SUM(CASE WHEN role = 'editor' THEN 1 ELSE 0 END) as editor_count
            FROM page_authors
            GROUP BY author_name
            ORDER BY total_count DESC, author_name ASC
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_author_statistics_by_role(self, role: str = 'creator') -> List[Dict[str, Any]]:
        """
        Get author statistics filtered by role (creator or editor).
        
        Args:
            role: 'creator' or 'editor'
        
        Returns list of dicts sorted by count (most frequent first).
        """
        cursor = self.conn.execute('''
            SELECT 
                author_name,
                COUNT(*) as count
            FROM page_authors
            WHERE role = ?
            GROUP BY author_name
            ORDER BY count DESC, author_name ASC
        ''', (role,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def export_failed_to_json(self, output_path: Path):
        """Export current failed pages to JSON for compatibility"""
        cursor = self.conn.execute('''
            SELECT file_path, page_id, title, expected_images, verified_images, retry_count, last_error
            FROM failed_pages
            WHERE status = 'pending'
            ORDER BY id DESC
        ''')
        
        failed_pages = [dict(row) for row in cursor.fetchall()]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(failed_pages, f, indent=2, ensure_ascii=False)
    
    def add_parsing_error(self, run_id: int, file_path: str, filename: str, 
                          stage: str, error_type: str, error_message: str, 
                          traceback_str: Optional[str] = None):
        """
        Record a parsing/conversion error for a file.
        
        Args:
            run_id: The import run ID
            file_path: Full path to the file that failed
            filename: Just the filename for display
            stage: Where it failed - 'parsing', 'transform', or 'notion_upload'
            error_type: The exception class name (e.g., 'AttributeError')
            error_message: The error message string
            traceback_str: Full traceback for debugging (optional)
        """
        with self.conn:
            self.conn.execute('''
                INSERT INTO parsing_errors 
                (run_id, file_path, filename, stage, error_type, error_message, traceback, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (run_id, file_path, filename, stage, error_type, error_message, 
                  traceback_str, datetime.now().isoformat()))
    
    def get_parsing_errors(self, run_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get parsing errors, optionally filtered by run_id.
        
        Args:
            run_id: Optional run ID to filter by. If None, returns all errors.
            
        Returns:
            List of error records as dicts
        """
        if run_id is not None:
            cursor = self.conn.execute('''
                SELECT * FROM parsing_errors 
                WHERE run_id = ? 
                ORDER BY timestamp
            ''', (run_id,))
        else:
            cursor = self.conn.execute('''
                SELECT * FROM parsing_errors 
                ORDER BY timestamp DESC
            ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_parsing_errors_summary(self, run_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary of parsing errors by stage.
        
        Returns dict with counts by stage and total.
        """
        if run_id is not None:
            cursor = self.conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN stage = 'parsing' THEN 1 ELSE 0 END) as parsing_count,
                    SUM(CASE WHEN stage = 'transform' THEN 1 ELSE 0 END) as transform_count,
                    SUM(CASE WHEN stage = 'notion_upload' THEN 1 ELSE 0 END) as upload_count
                FROM parsing_errors
                WHERE run_id = ?
            ''', (run_id,))
        else:
            cursor = self.conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN stage = 'parsing' THEN 1 ELSE 0 END) as parsing_count,
                    SUM(CASE WHEN stage = 'transform' THEN 1 ELSE 0 END) as transform_count,
                    SUM(CASE WHEN stage = 'notion_upload' THEN 1 ELSE 0 END) as upload_count
                FROM parsing_errors
            ''')
        
        row = cursor.fetchone()
        return dict(row) if row else {'total': 0, 'parsing_count': 0, 'transform_count': 0, 'upload_count': 0}
    
    def export_parsing_errors_to_json(self, output_path: Path, run_id: Optional[int] = None):
        """
        Export parsing errors to JSON for easy review.
        
        Args:
            output_path: Path to write JSON file
            run_id: Optional run ID to filter by
        """
        errors = self.get_parsing_errors(run_id)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(errors, f, indent=2, ensure_ascii=False, default=str)
    
    def get_parsing_errors_by_stage(self, stage: str, run_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get parsing errors filtered by stage.
        
        Args:
            stage: 'parsing', 'transform', or 'notion_upload'
            run_id: Optional run ID to filter by
            
        Returns:
            List of error records matching the stage
        """
        if run_id is not None:
            cursor = self.conn.execute('''
                SELECT * FROM parsing_errors 
                WHERE stage = ? AND run_id = ?
                ORDER BY timestamp
            ''', (stage, run_id))
        else:
            cursor = self.conn.execute('''
                SELECT * FROM parsing_errors 
                WHERE stage = ?
                ORDER BY run_id DESC, timestamp
            ''', (stage,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_parsing_errors_by_error_type(self, error_type: str, run_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get parsing errors filtered by error type (exception class name).
        
        Args:
            error_type: Exception class name (e.g., 'AttributeError', 'KeyError')
            run_id: Optional run ID to filter by
            
        Returns:
            List of error records matching the error type
        """
        if run_id is not None:
            cursor = self.conn.execute('''
                SELECT * FROM parsing_errors 
                WHERE error_type = ? AND run_id = ?
                ORDER BY timestamp
            ''', (error_type, run_id))
        else:
            cursor = self.conn.execute('''
                SELECT * FROM parsing_errors 
                WHERE error_type = ?
                ORDER BY run_id DESC, timestamp
            ''', (error_type,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_runs_with_errors(self) -> List[Dict[str, Any]]:
        """
        Get all import runs that had parsing errors, with error counts.
        
        Returns:
            List of dicts with run info and error counts
        """
        cursor = self.conn.execute('''
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
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_error_type_summary(self, run_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get summary of errors grouped by error type.
        
        Args:
            run_id: Optional run ID to filter by
            
        Returns:
            List of dicts with error_type and count, sorted by count DESC
        """
        if run_id is not None:
            cursor = self.conn.execute('''
                SELECT error_type, COUNT(*) as count
                FROM parsing_errors
                WHERE run_id = ?
                GROUP BY error_type
                ORDER BY count DESC
            ''', (run_id,))
        else:
            cursor = self.conn.execute('''
                SELECT error_type, COUNT(*) as count
                FROM parsing_errors
                GROUP BY error_type
                ORDER BY count DESC
            ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

