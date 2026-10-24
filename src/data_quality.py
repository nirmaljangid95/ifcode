"""
Data Quality Checker - Detects and reports data quality issues.

Identifies:
- NULL values and empty strings
- Duplicates
- Inconsistent formats (dates, numbers, case)
- Unexpected data types
- Outliers and anomalies
"""

import sqlite3
import logging
import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .schema_inspector import SchemaInfo, TableInfo, ColumnInfo

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """Represents a data quality issue."""
    severity: str  # 'critical', 'warning', 'info'
    issue_type: str  # 'nulls', 'duplicates', 'format', 'type', 'outlier'
    table: str
    column: Optional[str]
    description: str
    affected_rows: int
    sample_values: List[Any] = field(default_factory=list)


@dataclass
class QualityReport:
    """Complete data quality report."""
    database_path: str
    issues: List[QualityIssue] = field(default_factory=list)
    total_tables_checked: int = 0
    total_columns_checked: int = 0
    
    def add_issue(self, issue: QualityIssue):
        """Add an issue to the report."""
        self.issues.append(issue)
        logger.debug(f"{issue.severity.upper()}: {issue.description}")
    
    def get_critical_issues(self) -> List[QualityIssue]:
        """Return only critical issues."""
        return [i for i in self.issues if i.severity == 'critical']
    
    def get_warnings(self) -> List[QualityIssue]:
        """Return only warnings."""
        return [i for i in self.issues if i.severity == 'warning']


class DataQualityChecker:
    """
    Analyzes database for data quality issues without modifying data.
    
    Focuses on detecting issues that could affect SQL generation
    and result interpretation.
    """
    
    def __init__(
        self,
        database_path: str,
        null_threshold: float = 0.5,
        duplicate_threshold: float = 0.3,
        sample_size: int = 100
    ):
        """
        Initialize data quality checker.
        
        Args:
            database_path: Path to SQLite database
            null_threshold: Warn if more than this fraction are NULL
            duplicate_threshold: Warn if more than this fraction are duplicates
            sample_size: Number of rows to sample for format checks
        """
        self.database_path = Path(database_path)
        self.null_threshold = null_threshold
        self.duplicate_threshold = duplicate_threshold
        self.sample_size = sample_size
        
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {database_path}")
        
        logger.info(f"Initialized DataQualityChecker for: {database_path}")
    
    def check(self, schema: SchemaInfo) -> QualityReport:
        """
        Perform comprehensive data quality check.
        
        Args:
            schema: SchemaInfo from SchemaInspector
        
        Returns:
            QualityReport with all detected issues
        """
        logger.info("Starting data quality check...")
        
        report = QualityReport(database_path=str(self.database_path))
        
        with self._connect() as conn:
            for table_name, table_info in schema.tables.items():
                report.total_tables_checked += 1
                
                # Check table-level issues
                self._check_table_level(conn, table_info, report)
                
                # Check each column
                for col_info in table_info.columns:
                    report.total_columns_checked += 1
                    self._check_column_quality(conn, table_info, col_info, report)
        
        logger.info(
            f"Data quality check complete: {len(report.issues)} issues found "
            f"({len(report.get_critical_issues())} critical, {len(report.get_warnings())} warnings)"
        )
        
        return report
    
    def _connect(self) -> sqlite3.Connection:
        """Create read-only database connection."""
        uri = f"file:{self.database_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _check_table_level(
        self,
        conn: sqlite3.Connection,
        table_info: TableInfo,
        report: QualityReport
    ):
        """Check table-level quality issues."""
        
        # Empty table
        if table_info.row_count == 0:
            report.add_issue(QualityIssue(
                severity='warning',
                issue_type='empty',
                table=table_info.name,
                column=None,
                description=f"Table '{table_info.name}' is empty",
                affected_rows=0
            ))
            return
        
        # Check for completely duplicate rows
        try:
            # Get all column names
            cols = ", ".join([c.name for c in table_info.columns])
            
            cursor = conn.execute(f"""
                SELECT COUNT(*) - COUNT(DISTINCT {cols})
                FROM {table_info.name}
            """)
            duplicate_rows = cursor.fetchone()[0]
            
            if duplicate_rows > 0:
                dup_ratio = duplicate_rows / table_info.row_count
                
                severity = 'critical' if dup_ratio > self.duplicate_threshold else 'warning'
                
                report.add_issue(QualityIssue(
                    severity=severity,
                    issue_type='duplicates',
                    table=table_info.name,
                    column=None,
                    description=(
                        f"Table '{table_info.name}' has {duplicate_rows} completely "
                        f"duplicate rows ({dup_ratio*100:.1f}%)"
                    ),
                    affected_rows=duplicate_rows
                ))
        except sqlite3.OperationalError:
            # DISTINCT may fail on some column types
            pass
    
    def _check_column_quality(
        self,
        conn: sqlite3.Connection,
        table_info: TableInfo,
        col_info: ColumnInfo,
        report: QualityReport
    ):
        """Check quality issues for a specific column."""
        
        table_name = table_info.name
        col_name = col_info.name
        
        # Skip if column has no data
        if col_info.total_count == 0:
            return
        
        # Check NULL values
        self._check_nulls(table_info, col_info, report)
        
        # Check empty strings (for text columns)
        if 'TEXT' in col_info.data_type.upper() or 'CHAR' in col_info.data_type.upper():
            self._check_empty_strings(conn, table_info, col_info, report)
        
        # Check date format consistency
        if self._is_date_column(col_info):
            self._check_date_formats(conn, table_info, col_info, report)
        
        # Check numeric format (for numeric types stored as text)
        if 'TEXT' in col_info.data_type.upper() and self._looks_numeric(col_info):
            self._check_numeric_consistency(conn, table_info, col_info, report)
        
        # Check duplicate values in supposedly unique columns
        if col_info.primary_key or 'unique' in col_name.lower() or 'id' in col_name.lower():
            self._check_uniqueness(conn, table_info, col_info, report)
    
    def _check_nulls(
        self,
        table_info: TableInfo,
        col_info: ColumnInfo,
        report: QualityReport
    ):
        """Check for excessive NULL values."""
        
        if col_info.null_count == 0:
            return
        
        null_ratio = col_info.null_count / col_info.total_count
        
        if null_ratio > self.null_threshold:
            severity = 'critical' if null_ratio > 0.8 else 'warning'
            
            report.add_issue(QualityIssue(
                severity=severity,
                issue_type='nulls',
                table=table_info.name,
                column=col_info.name,
                description=(
                    f"Column '{table_info.name}.{col_info.name}' has {col_info.null_count} "
                    f"NULL values ({null_ratio*100:.1f}%)"
                ),
                affected_rows=col_info.null_count
            ))
    
    def _check_empty_strings(
        self,
        conn: sqlite3.Connection,
        table_info: TableInfo,
        col_info: ColumnInfo,
        report: QualityReport
    ):
        """Check for empty strings in text columns."""
        
        cursor = conn.execute(f"""
            SELECT COUNT(*)
            FROM {table_info.name}
            WHERE {col_info.name} = ''
        """)
        empty_count = cursor.fetchone()[0]
        
        if empty_count > 0:
            empty_ratio = empty_count / col_info.total_count
            
            if empty_ratio > 0.1:  # More than 10% empty
                report.add_issue(QualityIssue(
                    severity='warning',
                    issue_type='empty_strings',
                    table=table_info.name,
                    column=col_info.name,
                    description=(
                        f"Column '{table_info.name}.{col_info.name}' has {empty_count} "
                        f"empty strings ({empty_ratio*100:.1f}%)"
                    ),
                    affected_rows=empty_count
                ))
    
    def _check_date_formats(
        self,
        conn: sqlite3.Connection,
        table_info: TableInfo,
        col_info: ColumnInfo,
        report: QualityReport
    ):
        """Check for inconsistent date formats."""
        
        # Sample non-null values
        cursor = conn.execute(f"""
            SELECT DISTINCT {col_info.name}
            FROM {table_info.name}
            WHERE {col_info.name} IS NOT NULL
            LIMIT {self.sample_size}
        """)
        samples = [row[0] for row in cursor.fetchall()]
        
        if not samples:
            return
        
        # Detect format patterns
        formats_found = set()
        for value in samples:
            fmt = self._detect_date_format(str(value))
            if fmt:
                formats_found.add(fmt)
        
        if len(formats_found) > 1:
            report.add_issue(QualityIssue(
                severity='warning',
                issue_type='format',
                table=table_info.name,
                column=col_info.name,
                description=(
                    f"Column '{table_info.name}.{col_info.name}' has inconsistent date "
                    f"formats: {', '.join(formats_found)}"
                ),
                affected_rows=-1,
                sample_values=samples[:5]
            ))
    
    def _check_numeric_consistency(
        self,
        conn: sqlite3.Connection,
        table_info: TableInfo,
        col_info: ColumnInfo,
        report: QualityReport
    ):
        """Check for numeric values stored inconsistently as text."""
        
        cursor = conn.execute(f"""
            SELECT {col_info.name}
            FROM {table_info.name}
            WHERE {col_info.name} IS NOT NULL
            LIMIT {self.sample_size}
        """)
        samples = [row[0] for row in cursor.fetchall()]
        
        non_numeric = []
        for value in samples:
            try:
                float(str(value).replace(',', ''))
            except (ValueError, AttributeError):
                non_numeric.append(value)
        
        if non_numeric and len(non_numeric) < len(samples) * 0.9:
            # Mix of numeric and non-numeric
            report.add_issue(QualityIssue(
                severity='warning',
                issue_type='type',
                table=table_info.name,
                column=col_info.name,
                description=(
                    f"Column '{table_info.name}.{col_info.name}' contains mix of "
                    f"numeric and non-numeric values"
                ),
                affected_rows=len(non_numeric),
                sample_values=non_numeric[:5]
            ))
    
    def _check_uniqueness(
        self,
        conn: sqlite3.Connection,
        table_info: TableInfo,
        col_info: ColumnInfo,
        report: QualityReport
    ):
        """Check if supposedly unique column has duplicates."""
        
        if col_info.primary_key:
            return  # PKs are enforced by database
        
        # Count duplicates
        cursor = conn.execute(f"""
            SELECT {col_info.name}, COUNT(*) as cnt
            FROM {table_info.name}
            WHERE {col_info.name} IS NOT NULL
            GROUP BY {col_info.name}
            HAVING cnt > 1
            LIMIT 10
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            total_dup_rows = sum(row[1] for row in duplicates)
            
            report.add_issue(QualityIssue(
                severity='warning',
                issue_type='duplicates',
                table=table_info.name,
                column=col_info.name,
                description=(
                    f"Column '{table_info.name}.{col_info.name}' (appears to be a unique "
                    f"identifier) has {len(duplicates)} duplicate values"
                ),
                affected_rows=total_dup_rows,
                sample_values=[row[0] for row in duplicates[:5]]
            ))
    
    @staticmethod
    def _is_date_column(col_info: ColumnInfo) -> bool:
        """Heuristic to detect if column likely contains dates."""
        name_lower = col_info.name.lower()
        date_keywords = ['date', 'time', 'year', 'month', 'day', 'created', 'updated', 'modified']
        
        # Check name
        if any(kw in name_lower for kw in date_keywords):
            return True
        
        # Check data type
        if 'DATE' in col_info.data_type.upper() or 'TIME' in col_info.data_type.upper():
            return True
        
        # Check sample values
        if col_info.sample_values:
            sample_str = str(col_info.sample_values[0])
            return DataQualityChecker._detect_date_format(sample_str) is not None
        
        return False
    
    @staticmethod
    def _detect_date_format(value: str) -> Optional[str]:
        """Detect date format pattern."""
        patterns = {
            r'^\d{4}-\d{2}-\d{2}$': 'YYYY-MM-DD',
            r'^\d{2}/\d{2}/\d{4}$': 'MM/DD/YYYY',
            r'^\d{2}-\d{2}-\d{4}$': 'DD-MM-YYYY',
            r'^\d{4}/\d{2}/\d{2}$': 'YYYY/MM/DD',
            r'^\d{8}$': 'YYYYMMDD',
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$': 'YYYY-MM-DD HH:MM:SS',
        }
        
        for pattern, fmt in patterns.items():
            if re.match(pattern, value):
                return fmt
        
        return None
    
    @staticmethod
    def _looks_numeric(col_info: ColumnInfo) -> bool:
        """Heuristic to detect if text column contains numeric values."""
        if not col_info.sample_values:
            return False
        
        numeric_count = 0
        for value in col_info.sample_values:
            try:
                float(str(value).replace(',', ''))
                numeric_count += 1
            except (ValueError, AttributeError):
                pass
        
        return numeric_count >= len(col_info.sample_values) * 0.8
    
    def get_quality_summary(self, report: QualityReport) -> str:
        """Generate human-readable quality report summary."""
        
        summary_parts = [
            f"Data Quality Report: {report.database_path}",
            f"Tables checked: {report.total_tables_checked}",
            f"Columns checked: {report.total_columns_checked}",
            f"Total issues: {len(report.issues)}",
            f"  - Critical: {len(report.get_critical_issues())}",
            f"  - Warnings: {len(report.get_warnings())}",
            ""
        ]
        
        if report.get_critical_issues():
            summary_parts.append("=== CRITICAL ISSUES ===")
            for issue in report.get_critical_issues():
                summary_parts.append(f"  ⚠ {issue.description}")
            summary_parts.append("")
        
        if report.get_warnings():
            summary_parts.append("=== WARNINGS ===")
            for issue in report.get_warnings()[:10]:  # Limit to first 10
                summary_parts.append(f"  ⚠ {issue.description}")
            
            if len(report.get_warnings()) > 10:
                summary_parts.append(f"  ... and {len(report.get_warnings()) - 10} more warnings")
        
        return "\n".join(summary_parts)
