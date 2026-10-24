"""
Schema Inspector - Discovers database structure, relationships, and sample data.

This module inspects SQLite databases to extract:
- Tables and their columns
- Data types and constraints
- Primary and foreign keys
- Sample values for each column
- Basic statistics
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    nullable: bool
    primary_key: bool
    default_value: Optional[str] = None
    sample_values: List[Any] = field(default_factory=list)
    unique_count: int = 0
    null_count: int = 0
    total_count: int = 0


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    row_count: int = 0
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class SchemaInfo:
    """Complete database schema information."""
    database_path: str
    tables: Dict[str, TableInfo] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)


class SchemaInspector:
    """
    Inspects SQLite database schema and extracts structural information.
    
    This class provides read-only access to database metadata without
    modifying the original database.
    """
    
    def __init__(self, database_path: str, sample_rows: int = 5):
        """
        Initialize schema inspector.
        
        Args:
            database_path: Path to SQLite database file
            sample_rows: Number of sample rows to fetch per table
        """
        self.database_path = Path(database_path)
        self.sample_rows = sample_rows
        
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {database_path}")
        
        logger.info(f"Initialized SchemaInspector for: {database_path}")
    
    def inspect(self) -> SchemaInfo:
        """
        Perform complete schema inspection.
        
        Returns:
            SchemaInfo object with complete database structure
        """
        logger.info("Starting schema inspection...")
        
        schema = SchemaInfo(database_path=str(self.database_path))
        
        with self._connect() as conn:
            # Get all tables
            table_names = self._get_table_names(conn)
            logger.info(f"Found {len(table_names)} tables")
            
            # Inspect each table
            for table_name in table_names:
                try:
                    table_info = self._inspect_table(conn, table_name)
                    schema.tables[table_name] = table_info
                    logger.debug(f"Inspected table: {table_name} ({table_info.row_count} rows)")
                except Exception as e:
                    logger.error(f"Failed to inspect table {table_name}: {e}")
            
            # Discover relationships
            schema.relationships = self._discover_relationships(conn, schema.tables)
            logger.info(f"Discovered {len(schema.relationships)} relationships")
        
        logger.info("Schema inspection complete")
        return schema
    
    def _connect(self) -> sqlite3.Connection:
        """Create read-only database connection."""
        # Open in read-only mode using URI
        uri = f"file:{self.database_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    
    def _get_table_names(self, conn: sqlite3.Connection) -> List[str]:
        """Get list of all user tables (excluding system tables)."""
        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        return [row[0] for row in cursor.fetchall()]
    
    def _inspect_table(self, conn: sqlite3.Connection, table_name: str) -> TableInfo:
        """
        Inspect a single table and gather all metadata.
        
        Args:
            conn: Database connection
            table_name: Name of table to inspect
        
        Returns:
            TableInfo with complete table metadata
        """
        table_info = TableInfo(name=table_name)
        
        # Get column information
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns_data = cursor.fetchall()
        
        for col_data in columns_data:
            col_info = ColumnInfo(
                name=col_data[1],
                data_type=col_data[2],
                nullable=not bool(col_data[3]),  # notnull flag
                primary_key=bool(col_data[5]),
                default_value=col_data[4]
            )
            
            if col_info.primary_key:
                table_info.primary_keys.append(col_info.name)
            
            table_info.columns.append(col_info)
        
        # Get foreign keys
        cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
        fk_data = cursor.fetchall()
        
        for fk in fk_data:
            table_info.foreign_keys.append({
                "column": fk[3],  # from column
                "references_table": fk[2],  # to table
                "references_column": fk[4]  # to column
            })
        
        # Get row count
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        table_info.row_count = cursor.fetchone()[0]
        
        # Get sample values and statistics for each column
        if table_info.row_count > 0:
            for col_info in table_info.columns:
                self._gather_column_stats(conn, table_name, col_info)
        
        return table_info
    
    def _gather_column_stats(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        col_info: ColumnInfo
    ):
        """
        Gather statistics and sample values for a column.
        
        Args:
            conn: Database connection
            table_name: Name of table
            col_info: ColumnInfo object to populate (modified in place)
        """
        col_name = col_info.name
        
        # Total count
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        col_info.total_count = cursor.fetchone()[0]
        
        # NULL count
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL")
        col_info.null_count = cursor.fetchone()[0]
        
        # Unique count
        try:
            cursor = conn.execute(f"SELECT COUNT(DISTINCT {col_name}) FROM {table_name}")
            col_info.unique_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            # Some types can't use DISTINCT
            col_info.unique_count = -1
        
        # Sample values (non-null, distinct)
        try:
            cursor = conn.execute(f"""
                SELECT DISTINCT {col_name}
                FROM {table_name}
                WHERE {col_name} IS NOT NULL
                LIMIT {self.sample_rows}
            """)
            col_info.sample_values = [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not fetch samples for {table_name}.{col_name}: {e}")
            col_info.sample_values = []
    
    def _discover_relationships(
        self,
        conn: sqlite3.Connection,
        tables: Dict[str, TableInfo]
    ) -> List[Dict[str, Any]]:
        """
        Discover relationships between tables.
        
        Includes explicit foreign keys and attempts to infer implicit relationships
        based on column naming patterns.
        
        Args:
            conn: Database connection
            tables: Dictionary of table information
        
        Returns:
            List of relationship dictionaries
        """
        relationships = []
        
        # Explicit foreign keys
        for table_name, table_info in tables.items():
            for fk in table_info.foreign_keys:
                relationships.append({
                    "from_table": table_name,
                    "from_column": fk["column"],
                    "to_table": fk["references_table"],
                    "to_column": fk["references_column"],
                    "type": "foreign_key",
                    "confidence": 1.0
                })
        
        # Infer implicit relationships (column name patterns)
        # Pattern: table_id or tableId likely references table(id)
        for table_name, table_info in tables.items():
            for col_info in table_info.columns:
                col_name = col_info.name.lower()
                
                # Skip if already has explicit FK
                if any(fk["column"] == col_info.name for fk in table_info.foreign_keys):
                    continue
                
                # Check for pattern: other_table_id
                if col_name.endswith("_id") or col_name.endswith("id"):
                    # Extract potential table name
                    potential_table = col_name.replace("_id", "").replace("id", "")
                    
                    # Look for matching table
                    for other_table in tables.keys():
                        if other_table.lower() == potential_table or \
                           other_table.lower() == potential_table + "s" or \
                           other_table.lower() + "s" == potential_table:
                            
                            # Check if other table has an 'id' column
                            other_table_info = tables[other_table]
                            if any(c.name.lower() == "id" for c in other_table_info.columns):
                                relationships.append({
                                    "from_table": table_name,
                                    "from_column": col_info.name,
                                    "to_table": other_table,
                                    "to_column": "id",
                                    "type": "inferred",
                                    "confidence": 0.7  # Lower confidence for inferred
                                })
                                logger.debug(
                                    f"Inferred relationship: {table_name}.{col_info.name} -> "
                                    f"{other_table}.id"
                                )
        
        return relationships
    
    def get_schema_summary(self, schema: SchemaInfo) -> str:
        """
        Generate human-readable schema summary.
        
        Args:
            schema: SchemaInfo object
        
        Returns:
            Formatted string describing the schema
        """
        summary_parts = [
            f"Database: {schema.database_path}",
            f"Tables: {len(schema.tables)}",
            f"Relationships: {len(schema.relationships)}",
            "\n--- Tables ---"
        ]
        
        for table_name, table_info in sorted(schema.tables.items()):
            summary_parts.append(
                f"\n{table_name} ({table_info.row_count} rows, "
                f"{len(table_info.columns)} columns)"
            )
            
            for col in table_info.columns:
                flags = []
                if col.primary_key:
                    flags.append("PK")
                if not col.nullable:
                    flags.append("NOT NULL")
                
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                
                null_pct = (col.null_count / col.total_count * 100) if col.total_count > 0 else 0
                
                sample_str = ""
                if col.sample_values:
                    samples = [str(v)[:20] for v in col.sample_values[:3]]
                    sample_str = f" Examples: {', '.join(samples)}"
                
                summary_parts.append(
                    f"  - {col.name}: {col.data_type}{flag_str} "
                    f"({null_pct:.1f}% null){sample_str}"
                )
        
        if schema.relationships:
            summary_parts.append("\n--- Relationships ---")
            for rel in schema.relationships:
                summary_parts.append(
                    f"  {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']} "
                    f"({rel['type']})"
                )
        
        return "\n".join(summary_parts)
