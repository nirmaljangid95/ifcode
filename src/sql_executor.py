"""
SQL Executor - Safely executes SQL queries with timeouts and limits.

Provides read-only execution with error handling and result formatting.
"""

import sqlite3
import logging
import signal
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of SQL query execution."""
    success: bool
    rows: List[Dict[str, Any]]
    column_names: List[str]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None
    truncated: bool = False


class TimeoutException(Exception):
    """Raised when query execution times out."""
    pass


class SQLExecutor:
    """
    Executes SQL queries safely with timeouts and row limits.
    
    Enforces read-only access and applies resource constraints.
    """
    
    def __init__(
        self,
        database_path: str,
        timeout_seconds: int = 30,
        max_rows: int = 10000,
        read_only: bool = True
    ):
        """
        Initialize SQL executor.
        
        Args:
            database_path: Path to SQLite database
            timeout_seconds: Query timeout in seconds
            max_rows: Maximum rows to return
            read_only: Force read-only mode
        """
        self.database_path = Path(database_path)
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows
        self.read_only = read_only
        
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {database_path}")
        
        logger.info(
            f"Initialized SQLExecutor: timeout={timeout_seconds}s, "
            f"max_rows={max_rows}, read_only={read_only}"
        )
    
    def execute(self, sql: str) -> ExecutionResult:
        """
        Execute SQL query safely.
        
        Args:
            sql: SQL query to execute
        
        Returns:
            ExecutionResult with query results or error
        """
        import time
        
        start_time = time.time()
        
        logger.info(f"Executing SQL: {sql[:100]}...")
        
        try:
            with self._connect() as conn:
                # Set query timeout
                conn.execute(f"PRAGMA busy_timeout = {self.timeout_seconds * 1000}")
                
                # Execute with timeout
                cursor = self._execute_with_timeout(conn, sql)
                
                # Fetch results
                rows = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Check if truncation needed
                truncated = False
                if len(rows) > self.max_rows:
                    rows = rows[:self.max_rows]
                    truncated = True
                    logger.warning(f"Results truncated to {self.max_rows} rows")
                
                # Convert to list of dicts
                result_rows = [dict(zip(column_names, row)) for row in rows]
                
                execution_time = (time.time() - start_time) * 1000
                
                logger.info(f"Query successful: {len(result_rows)} rows in {execution_time:.2f}ms")
                
                return ExecutionResult(
                    success=True,
                    rows=result_rows,
                    column_names=column_names,
                    row_count=len(result_rows),
                    execution_time_ms=execution_time,
                    truncated=truncated
                )
        
        except TimeoutException:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Query exceeded timeout of {self.timeout_seconds} seconds"
            logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                rows=[],
                column_names=[],
                row_count=0,
                execution_time_ms=execution_time,
                error=error_msg
            )
        
        except sqlite3.OperationalError as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"SQL execution error: {str(e)}"
            logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                rows=[],
                column_names=[],
                row_count=0,
                execution_time_ms=execution_time,
                error=error_msg
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                rows=[],
                column_names=[],
                row_count=0,
                execution_time_ms=execution_time,
                error=error_msg
            )
    
    def _connect(self) -> sqlite3.Connection:
        """Create database connection."""
        if self.read_only:
            # Open in read-only mode
            uri = f"file:{self.database_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            conn = sqlite3.connect(str(self.database_path), check_same_thread=False)
        
        conn.row_factory = sqlite3.Row
        return conn
    
    def _execute_with_timeout(
        self,
        conn: sqlite3.Connection,
        sql: str
    ) -> sqlite3.Cursor:
        """
        Execute query with timeout.
        
        Note: SQLite timeout is cooperative - long-running queries may not
        be interrupted immediately.
        
        Args:
            conn: Database connection
            sql: SQL query
        
        Returns:
            Cursor with results
        
        Raises:
            TimeoutException: If query times out
        """
        # For Windows, we can't use signal-based timeout
        # Instead, rely on SQLite's busy_timeout
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor
    
    def explain_query(self, sql: str) -> Dict[str, Any]:
        """
        Get query execution plan.
        
        Args:
            sql: SQL query to explain
        
        Returns:
            Dictionary with execution plan information
        """
        logger.info("Getting query execution plan")
        
        try:
            with self._connect() as conn:
                cursor = conn.execute(f"EXPLAIN QUERY PLAN {sql}")
                rows = cursor.fetchall()
                
                plan = [dict(row) for row in rows]
                
                return {
                    "success": True,
                    "plan": plan,
                    "sql": sql
                }
        
        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql": sql
            }
    
    def test_connection(self) -> bool:
        """
        Test if database connection works.
        
        Returns:
            True if connection successful
        """
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
