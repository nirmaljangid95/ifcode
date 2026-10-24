"""
SQL Generator - Converts natural language questions to SQL using LLM.

Uses schema information and data quality insights to generate accurate,
safe SQL queries.

Prompts are centralized in prompts/sql_generation_prompts.py for easy modification.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .models.llm_client import LLMClient
from .schema_inspector import SchemaInfo
from .data_quality import QualityReport

# Import centralized prompts
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from prompts.sql_generation_prompts import SQLPrompts
except ImportError:
    # Fallback if prompts file not found
    SQLPrompts = None

logger = logging.getLogger(__name__)


@dataclass
class SQLQuery:
    """Generated SQL query with metadata."""
    sql: str
    explanation: str
    tables_used: List[str]
    columns_used: List[str]
    confidence: float
    warnings: List[str]


class SQLGenerator:
    """
    Generates SQL queries from natural language using LLM with schema context.
    
    Includes safety checks and validation before returning queries.
    """
    
    # SQL keywords that modify data (blocked)
    DESTRUCTIVE_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
        'CREATE', 'TRUNCATE', 'REPLACE', 'GRANT', 'REVOKE'
    ]
    
    def __init__(
        self,
        llm_client: LLMClient,
        schema: SchemaInfo,
        quality_report: Optional[QualityReport] = None,
        max_tables: int = 5
    ):
        """
        Initialize SQL generator.
        
        Args:
            llm_client: LLM client for generation
            schema: Database schema information
            quality_report: Optional data quality report
            max_tables: Maximum tables allowed in a query
        """
        self.llm_client = llm_client
        self.schema = schema
        self.quality_report = quality_report
        self.max_tables = max_tables
        
        logger.info("Initialized SQLGenerator")
    
    def generate(self, question: str) -> SQLQuery:
        """
        Generate SQL query from natural language question.
        
        Args:
            question: Natural language question about the data
        
        Returns:
            SQLQuery object with generated SQL and metadata
        
        Raises:
            ValueError: If SQL generation fails or produces unsafe query
        """
        logger.info(f"Generating SQL for question: {question}")
        
        # Build context for LLM
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(question)
        
        # Generate SQL using LLM
        response = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1  # Low temperature for deterministic output
        )
        
        if not response.success:
            raise ValueError(f"LLM generation failed: {response.error}")
        
        # Parse response
        sql_query = self._parse_llm_response(response.content)
        
        # Validate safety
        self._validate_safety(sql_query)
        
        # Add warnings based on quality report
        if self.quality_report:
            sql_query.warnings.extend(self._get_relevant_warnings(sql_query))
        
        logger.info(f"Generated SQL: {sql_query.sql[:100]}...")
        
        return sql_query
    
    def _build_system_prompt(self) -> str:
        """Build system prompt using centralized prompts."""
        
        if SQLPrompts:
            # Use centralized prompts
            schema_text = SQLPrompts.format_schema(self.schema)
            quality_text = SQLPrompts.format_quality_notes(self.quality_report) if self.quality_report else None
            return SQLPrompts.build_system_prompt(schema_text, quality_text)
        else:
            # Fallback to inline prompt (if prompts file not found)
            return self._build_system_prompt_fallback()
    
    def _build_system_prompt_fallback(self) -> str:
        """Fallback system prompt if centralized file not available."""
        
        prompt_parts = [
            "You are an expert SQL query generator. Your job is to convert natural language questions into accurate SQL queries.",
            "",
            "CRITICAL RULES:",
            "1. Generate ONLY valid SQLite queries",
            "2. Use ONLY tables and columns that exist in the schema below",
            "3. Never use DROP, DELETE, UPDATE, INSERT, or other destructive operations",
            "4. Use appropriate JOINs based on foreign key relationships",
            "5. Include WHERE clauses for filters and date ranges",
            "6. Use aggregate functions (COUNT, SUM, AVG, etc.) when appropriate",
            "7. Always add LIMIT 1000 clause for safety",
            "8. Handle NULL values explicitly in comparisons",
            "",
            "Schema Information:",
            self._format_schema_for_llm(),
        ]
        
        if self.quality_report:
            prompt_parts.extend([
                "",
                "Data Quality Notes:",
                self._format_quality_notes()
            ])
        
        prompt_parts.extend([
            "",
            "EXAMPLES:",
            "",
            'Question: "How many schools are there?"',
            'Answer: {"sql": "SELECT COUNT(*) FROM schools LIMIT 1000", "explanation": "Count total schools", "tables_used": ["schools"], "columns_used": ["*"], "confidence": 0.9}',
            "",
            'Question: "Which schools had enrollment changes between 2021 and 2023?"',
            'Answer: {"sql": "SELECT s.school_name, e1.total_students as y2021, e2.total_students as y2023, (e1.total_students - e2.total_students) as change FROM schools s JOIN enrollment_history e1 ON s.school_id = e1.school_id AND e1.year = 2021 JOIN enrollment_history e2 ON s.school_id = e2.school_id AND e2.year = 2023 WHERE e1.total_students IS NOT NULL AND e2.total_students IS NOT NULL ORDER BY change DESC LIMIT 1000", "explanation": "Compare enrollment between two years using self-join", "tables_used": ["schools", "enrollment_history"], "columns_used": ["school_name", "total_students", "year"], "confidence": 0.9}',
            "",
            "RESPONSE FORMAT (MUST BE VALID JSON):",
            '{"sql": "SELECT...", "explanation": "text", "tables_used": ["t1"], "columns_used": ["c1"], "confidence": 0.9}'
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_user_prompt(self, question: str) -> str:
        """Build user prompt with the question."""
        
        if SQLPrompts:
            return SQLPrompts.build_user_prompt(question)
        else:
            return f"Convert this question into a SQL query:\n\nQuestion: {question}"
    
    def _format_schema_for_llm(self) -> str:
        """Format schema information in a concise, LLM-friendly format."""
        
        lines = []
        
        for table_name, table_info in self.schema.tables.items():
            # Table header
            lines.append(f"\nTable: {table_name} ({table_info.row_count} rows)")
            
            # Columns
            for col in table_info.columns:
                flags = []
                if col.primary_key:
                    flags.append("PRIMARY KEY")
                if not col.nullable:
                    flags.append("NOT NULL")
                
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                
                # Sample values
                sample_str = ""
                if col.sample_values:
                    samples = [str(v)[:30] for v in col.sample_values[:3]]
                    sample_str = f" (examples: {', '.join(samples)})"
                
                lines.append(f"  - {col.name}: {col.data_type}{flag_str}{sample_str}")
            
            # Foreign keys
            if table_info.foreign_keys:
                lines.append("  Foreign Keys:")
                for fk in table_info.foreign_keys:
                    lines.append(
                        f"    - {fk['column']} -> {fk['references_table']}.{fk['references_column']}"
                    )
        
        # Relationships
        if self.schema.relationships:
            lines.append("\nRelationships:")
            for rel in self.schema.relationships:
                lines.append(
                    f"  - {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']} ({rel['type']})"
                )
        
        return "\n".join(lines)
    
    def _format_quality_notes(self) -> str:
        """Format quality issues relevant to SQL generation."""
        
        if not self.quality_report or not self.quality_report.issues:
            return "No significant data quality issues detected."
        
        notes = []
        
        # Focus on critical issues and high NULL rates
        for issue in self.quality_report.get_critical_issues()[:5]:
            if issue.issue_type == 'nulls':
                notes.append(
                    f"  - {issue.table}.{issue.column}: High NULL rate ({issue.affected_rows} nulls), "
                    f"use COALESCE or IS NULL checks"
                )
            elif issue.issue_type == 'format':
                notes.append(
                    f"  - {issue.table}.{issue.column}: Inconsistent formats, may need CAST or type conversion"
                )
        
        return "\n".join(notes) if notes else "No critical issues affecting query generation."
    
    def _parse_llm_response(self, response_text: str) -> SQLQuery:
        """
        Parse LLM response into SQLQuery object with better error handling.
        
        Args:
            response_text: Raw LLM response
        
        Returns:
            SQLQuery object
        
        Raises:
            ValueError: If response cannot be parsed
        """
        import json
        
        # Clean response text
        response_text = response_text.strip()
        
        # Try to find JSON object (handle multiline)
        json_match = re.search(r'\{.*?"sql".*?\}', response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group()
            
            # Clean up common JSON issues
            json_str = json_str.replace('\n', ' ')  # Remove newlines inside JSON
            json_str = re.sub(r'\s+', ' ', json_str)  # Collapse whitespace
            
            try:
                data = json.loads(json_str)
                
                sql = data.get('sql', '').strip()
                
                # Clean SQL
                sql = sql.replace('\\n', ' ')
                sql = re.sub(r'\s+', ' ', sql)
                sql = sql.strip()
                
                # Remove trailing garbage
                if sql.endswith(('",', '",')):
                    sql = sql.rstrip('",')
                
                return SQLQuery(
                    sql=sql,
                    explanation=data.get('explanation', ''),
                    tables_used=data.get('tables_used', []),
                    columns_used=data.get('columns_used', []),
                    confidence=float(data.get('confidence', 0.7)),
                    warnings=[]
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse JSON: {e}")
        
        # Fallback: try to extract just the SQL
        sql_match = re.search(r'SELECT\s+.+?(?:;|LIMIT\s+\d+|$)', response_text, re.IGNORECASE | re.DOTALL)
        
        if sql_match:
            sql = sql_match.group().strip().rstrip(';')
            
            # Clean it
            sql = re.sub(r'\s+', ' ', sql)
            
            return SQLQuery(
                sql=sql,
                explanation="Extracted from LLM response",
                tables_used=self._extract_tables_from_sql(sql),
                columns_used=[],
                confidence=0.6,
                warnings=["Could not parse structured response, extracted SQL directly"]
            )
        
        raise ValueError(f"Could not extract SQL from LLM response: {response_text[:200]}")
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query."""
        tables = []
        
        # Match FROM clause
        from_match = re.search(r'FROM\s+(\w+)', sql, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1))
        
        # Match JOIN clauses
        join_matches = re.findall(r'JOIN\s+(\w+)', sql, re.IGNORECASE)
        tables.extend(join_matches)
        
        return list(set(tables))
    
    def _validate_safety(self, sql_query: SQLQuery):
        """
        Validate that SQL query is safe to execute.
        
        Args:
            sql_query: SQLQuery to validate
        
        Raises:
            ValueError: If query is unsafe
        """
        sql_upper = sql_query.sql.upper()
        
        # Check for destructive keywords
        for keyword in self.DESTRUCTIVE_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', sql_upper):
                raise ValueError(
                    f"SQL query contains forbidden keyword: {keyword}. "
                    f"Only SELECT queries are allowed."
                )
        
        # Must be SELECT query
        if not sql_upper.strip().startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        # Check table count
        if len(sql_query.tables_used) > self.max_tables:
            raise ValueError(
                f"Query uses too many tables ({len(sql_query.tables_used)}). "
                f"Maximum allowed: {self.max_tables}"
            )
        
        # Verify tables exist
        for table in sql_query.tables_used:
            if table not in self.schema.tables:
                raise ValueError(f"Table '{table}' does not exist in schema")
        
        logger.debug("SQL query passed safety validation")
    
    def _get_relevant_warnings(self, sql_query: SQLQuery) -> List[str]:
        """Get data quality warnings relevant to this query."""
        
        warnings = []
        
        for issue in self.quality_report.issues:
            if issue.severity != 'critical':
                continue
            
            if issue.table in sql_query.tables_used:
                if issue.issue_type == 'nulls':
                    warnings.append(
                        f"Note: Column {issue.table}.{issue.column} has many NULL values "
                        f"({issue.affected_rows})"
                    )
                elif issue.issue_type == 'duplicates':
                    warnings.append(
                        f"Note: Table {issue.table} contains duplicate rows"
                    )
        
        return warnings
    
    def refine_query(self, original_query: SQLQuery, refinement_request: str) -> SQLQuery:
        """
        Refine an existing query based on feedback.
        
        Args:
            original_query: Original SQLQuery
            refinement_request: How to modify the query (e.g., error message)
        
        Returns:
            Refined SQLQuery
        """
        logger.info(f"Refining query based on: {refinement_request}")
        
        if SQLPrompts:
            # Use centralized refinement prompt
            system_prompt = self._build_system_prompt()
            user_prompt = SQLPrompts.build_refinement_prompt(
                question="",  # Not needed in refinement
                original_sql=original_query.sql,
                error=refinement_request
            )
        else:
            # Fallback
            system_prompt = self._build_system_prompt()
            user_prompt = f"""
Original SQL:
{original_query.sql}

Original explanation:
{original_query.explanation}

Refinement request:
{refinement_request}

Generate an improved SQL query addressing the refinement request.
"""
        
        response = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        if not response.success:
            raise ValueError(f"LLM refinement failed: {response.error}")
        
        refined_query = self._parse_llm_response(response.content)
        self._validate_safety(refined_query)
        
        return refined_query
