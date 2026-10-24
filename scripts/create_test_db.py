"""
Create a test database with intentionally messy data for testing the agent.

This database simulates real-world data quality issues:
- NULL values
- Duplicates
- Inconsistent date formats
- Empty strings
- Mixed data types
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path


def create_test_database(db_path: str):
    """Create a test SQLite database with messy data."""
    
    # Remove existing database
    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()
    
    # Create parent directory
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Creating test database: {db_path}")
    
    # Create schools table
    print("Creating schools table...")
    cursor.execute("""
        CREATE TABLE schools (
            school_id INTEGER PRIMARY KEY,
            school_name TEXT,
            district TEXT,
            city TEXT,
            state TEXT,
            founded_year INTEGER,
            type TEXT
        )
    """)
    
    schools_data = [
        (1, "Lincoln High School", "District 1", "Springfield", "IL", 1965, "Public"),
        (2, "Washington Elementary", "District 1", "Springfield", "IL", 1978, "Public"),
        (3, "Jefferson Middle School", "District 2", "Springfield", "IL", None, "Public"),  # NULL year
        (4, "Roosevelt Academy", None, "Springfield", "IL", 2005, "Private"),  # NULL district
        (5, "Kennedy School", "District 1", "", "IL", 1990, "Public"),  # Empty city
        (6, "Lincoln High School", "District 3", "Chicago", "IL", 1965, "Public"),  # Duplicate name
        (7, "Madison High", "District 2", "Chicago", "IL", 1999, "Public"),
        (8, None, "District 1", "Springfield", "IL", 2010, "Charter"),  # NULL name
    ]
    
    cursor.executemany(
        "INSERT INTO schools VALUES (?, ?, ?, ?, ?, ?, ?)",
        schools_data
    )
    
    # Create students table with enrollment data
    print("Creating students table...")
    cursor.execute("""
        CREATE TABLE students (
            student_id INTEGER PRIMARY KEY,
            school_id INTEGER,
            first_name TEXT,
            last_name TEXT,
            enrollment_date TEXT,  -- Inconsistent date formats
            grade_level INTEGER,
            status TEXT,
            FOREIGN KEY (school_id) REFERENCES schools(school_id)
        )
    """)
    
    # Generate messy student data
    first_names = ["John", "Mary", "James", "Patricia", "Michael", "Jennifer", "William", "Linda"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    statuses = ["Active", "Inactive", "Graduated", None, "active", "ACTIVE"]  # Mixed case and NULL
    
    student_id = 1
    for school_id in range(1, 8):
        # Number of students per school (varied)
        num_students = random.randint(50, 200)
        
        for _ in range(num_students):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            grade = random.randint(1, 12)
            status = random.choice(statuses)
            
            # Inconsistent date formats
            year = random.randint(2015, 2023)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            
            date_formats = [
                f"{year}-{month:02d}-{day:02d}",  # YYYY-MM-DD
                f"{month:02d}/{day:02d}/{year}",  # MM/DD/YYYY
                f"{year}{month:02d}{day:02d}",    # YYYYMMDD
                None,  # NULL
                ""     # Empty string
            ]
            enrollment_date = random.choice(date_formats)
            
            cursor.execute(
                "INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?)",
                (student_id, school_id, first_name, last_name, enrollment_date, grade, status)
            )
            student_id += 1
    
    # Create enrollment_history table (for year-over-year comparisons)
    print("Creating enrollment_history table...")
    cursor.execute("""
        CREATE TABLE enrollment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER,
            year INTEGER,
            total_students INTEGER,
            recorded_date TEXT,
            FOREIGN KEY (school_id) REFERENCES schools(school_id)
        )
    """)
    
    # Generate enrollment history (2021-2023)
    for school_id in range(1, 8):
        base_enrollment = random.randint(100, 300)
        
        for year in [2021, 2022, 2023]:
            # Some schools have falling enrollment
            if school_id in [1, 4]:  # Lincoln and Roosevelt have falling enrollment
                change = random.randint(-20, -5)
            elif school_id in [2, 6]:  # Washington and another Lincoln growing
                change = random.randint(5, 20)
            else:
                change = random.randint(-10, 10)
            
            enrollment = base_enrollment + change
            base_enrollment = enrollment
            
            # Some records have NULL dates
            recorded_date = f"{year}-09-01" if random.random() > 0.1 else None
            
            cursor.execute(
                "INSERT INTO enrollment_history (school_id, year, total_students, recorded_date) VALUES (?, ?, ?, ?)",
                (school_id, year, enrollment, recorded_date)
            )
    
    # Add some duplicate records (data quality issue)
    cursor.execute(
        "INSERT INTO enrollment_history (school_id, year, total_students, recorded_date) VALUES (1, 2023, 250, '2023-09-01')"
    )
    
    # Create teachers table
    print("Creating teachers table...")
    cursor.execute("""
        CREATE TABLE teachers (
            teacher_id INTEGER PRIMARY KEY,
            school_id INTEGER,
            full_name TEXT,
            subject TEXT,
            hire_date TEXT,
            salary REAL,
            FOREIGN KEY (school_id) REFERENCES schools(school_id)
        )
    """)
    
    subjects = ["Math", "English", "Science", "History", "Art", "Music", "PE", None]
    
    teacher_id = 1
    for school_id in range(1, 8):
        num_teachers = random.randint(10, 30)
        
        for _ in range(num_teachers):
            first = random.choice(first_names)
            last = random.choice(last_names)
            full_name = f"{first} {last}"
            subject = random.choice(subjects)
            
            # Hire date (some NULL)
            if random.random() > 0.2:
                year = random.randint(2005, 2023)
                hire_date = f"{year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
            else:
                hire_date = None
            
            # Salary (some NULL, some as text with commas)
            if random.random() > 0.1:
                salary = random.uniform(40000, 90000)
            else:
                salary = None
            
            cursor.execute(
                "INSERT INTO teachers VALUES (?, ?, ?, ?, ?, ?)",
                (teacher_id, school_id, full_name, subject, hire_date, salary)
            )
            teacher_id += 1
    
    conn.commit()
    
    # Print summary
    print("\nDatabase created successfully!")
    print("\nTables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for table in cursor.fetchall():
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} rows")
    
    print("\nData quality issues intentionally included:")
    print("  - NULL values in various columns")
    print("  - Inconsistent date formats")
    print("  - Duplicate records")
    print("  - Empty strings")
    print("  - Mixed case values")
    print("  - Missing foreign key values")
    
    conn.close()
    
    return db_path


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Default path
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "test_messy.db"
    
    # Allow custom path from command line
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    
    create_test_database(str(db_path))
    print(f"\nTest database created at: {db_path}")
    print("\nExample questions to try:")
    print("  - Which schools had falling enrollment between 2021 and 2023?")
    print("  - What is the average teacher salary by subject?")
    print("  - How many students are currently enrolled in each school?")
    print("  - Which school has the most teachers?")
