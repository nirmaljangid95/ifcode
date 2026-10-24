"""
Tests for schema inspector module.
"""

import pytest
import sqlite3
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schema_inspector import SchemaInspector, SchemaInfo


@pytest.fixture
def test_db(tmp_path):
    """Create a simple test database."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create test tables
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            age INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            order_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Insert sample data
    cursor.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com', 30)")
    cursor.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@example.com', 25)")
    cursor.execute("INSERT INTO users VALUES (3, 'Charlie', NULL, 35)")
    
    cursor.execute("INSERT INTO orders VALUES (1, 1, 100.50, '2023-01-15')")
    cursor.execute("INSERT INTO orders VALUES (2, 1, 200.00, '2023-02-20')")
    cursor.execute("INSERT INTO orders VALUES (3, 2, 50.25, '2023-03-10')")
    
    conn.commit()
    conn.close()
    
    return str(db_path)


def test_schema_inspector_initialization(test_db):
    """Test schema inspector initialization."""
    inspector = SchemaInspector(test_db)
    assert inspector.database_path.exists()
    assert inspector.sample_rows == 5


def test_schema_inspection(test_db):
    """Test complete schema inspection."""
    inspector = SchemaInspector(test_db)
    schema = inspector.inspect()
    
    assert isinstance(schema, SchemaInfo)
    assert len(schema.tables) == 2
    assert 'users' in schema.tables
    assert 'orders' in schema.tables


def test_table_info(test_db):
    """Test table information extraction."""
    inspector = SchemaInspector(test_db)
    schema = inspector.inspect()
    
    users_table = schema.tables['users']
    assert users_table.name == 'users'
    assert users_table.row_count == 3
    assert len(users_table.columns) == 4
    assert 'id' in users_table.primary_keys


def test_column_info(test_db):
    """Test column information extraction."""
    inspector = SchemaInspector(test_db)
    schema = inspector.inspect()
    
    users_table = schema.tables['users']
    id_col = next(c for c in users_table.columns if c.name == 'id')
    
    assert id_col.data_type == 'INTEGER'
    assert id_col.primary_key is True
    assert id_col.nullable is False


def test_foreign_keys(test_db):
    """Test foreign key detection."""
    inspector = SchemaInspector(test_db)
    schema = inspector.inspect()
    
    orders_table = schema.tables['orders']
    assert len(orders_table.foreign_keys) == 1
    
    fk = orders_table.foreign_keys[0]
    assert fk['column'] == 'user_id'
    assert fk['references_table'] == 'users'
    assert fk['references_column'] == 'id'


def test_sample_values(test_db):
    """Test sample value collection."""
    inspector = SchemaInspector(test_db, sample_rows=3)
    schema = inspector.inspect()
    
    users_table = schema.tables['users']
    name_col = next(c for c in users_table.columns if c.name == 'name')
    
    assert len(name_col.sample_values) > 0
    assert 'Alice' in name_col.sample_values or 'Bob' in name_col.sample_values


def test_null_detection(test_db):
    """Test NULL value detection."""
    inspector = SchemaInspector(test_db)
    schema = inspector.inspect()
    
    users_table = schema.tables['users']
    email_col = next(c for c in users_table.columns if c.name == 'email')
    
    assert email_col.null_count > 0  # Charlie has NULL email


def test_relationship_discovery(test_db):
    """Test relationship discovery."""
    inspector = SchemaInspector(test_db)
    schema = inspector.inspect()
    
    assert len(schema.relationships) >= 1
    
    # Check explicit FK relationship
    fk_rel = next((r for r in schema.relationships if r['type'] == 'foreign_key'), None)
    assert fk_rel is not None
    assert fk_rel['from_table'] == 'orders'
    assert fk_rel['to_table'] == 'users'


def test_schema_summary(test_db):
    """Test schema summary generation."""
    inspector = SchemaInspector(test_db)
    schema = inspector.inspect()
    
    summary = inspector.get_schema_summary(schema)
    assert 'users' in summary
    assert 'orders' in summary
    assert '3 rows' in summary  # users table


def test_nonexistent_database():
    """Test error handling for missing database."""
    with pytest.raises(FileNotFoundError):
        SchemaInspector("/nonexistent/database.db")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
