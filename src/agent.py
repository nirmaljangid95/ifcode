"""
Data Analyst Agent - Main orchestrator.

Coordinates all components to answer natural language questions about databases.
"""

import logging
from typing import Optional
from pathlib import Path

from .models.llm_client import LLMClient
from .schema_inspector import SchemaInspector, SchemaInfo
from .data_quality import DataQualityChecker, QualityReport
from .sql_generator import SQLGenerator, SQLQuery
from .sql_executor import SQLExecutor, ExecutionResult
from .result_validator import ResultValidator, ValidationResult
from .answer_formatter import AnswerFormatter, FormattedAnswer

logger = logging.getLogger(__name__)


class DataAnalystAgent:
    """
    Main agent that answers natural language questions about databases.
    
    Workflow:
    1. Inspect database schema
    2. Check data quality
    3. Generate SQL from question
    4. Execute SQL safely
    5. Validate results
    6. Format answer
    7. Retry if needed
    """
    
    def __init__(
        self,
        database_path: str,
        llm_client: LLMClient,
        max_retry_attempts: int = 2,
        timeout_seconds: int = 30,
        max_rows: int = 10000,
        enable_validation: bool = True
    ):
        """
        Initialize Data Analyst Agent.
        
        Args:
            database_path: Path to SQLite database
            llm_client: LLM client for SQL generation
            max_retry_attempts: Maximum query retry attempts
            timeout_seconds: Query timeout
            max_rows: Maximum rows to return
            enable_validation: Enable result validation
        """
        self.database_path = Path(database_path)
        self.llm_client = llm_client
        self.max_retry_attempts = max_retry_attempts
        self.enable_validation = enable_validation
        
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {database_path}")
        
        # Initialize components
        logger.info("Initializing Data Analyst Agent...")
        
        self.schema_inspector = SchemaInspector(str(self.database_path))
        self.data_quality_checker = DataQualityChecker(str(self.database_path))
        self.sql_executor = SQLExecutor(
            str(self.database_path),
            timeout_seconds=timeout_seconds,
            max_rows=max_rows
        )
        self.result_validator = ResultValidator()
        self.answer_formatter = AnswerFormatter()
        
        # Cached schema and quality info
        self.schema: Optional[SchemaInfo] = None
        self.quality_report: Optional[QualityReport] = None
        self.sql_generator: Optional[SQLGenerator] = None
        
        logger.info("Data Analyst Agent initialized")
    
    def initialize(self):
        """
        Initialize by inspecting schema and checking data quality.
        
        This should be called once before asking questions.
        """
        logger.info("Starting agent initialization...")
        
        # Inspect schema
        logger.info("Step 1: Inspecting database schema...")
        self.schema = self.schema_inspector.inspect()
        logger.info(f"Found {len(self.schema.tables)} tables")
        
        # Check data quality
        logger.info("Step 2: Checking data quality...")
        self.quality_report = self.data_quality_checker.check(self.schema)
        logger.info(
            f"Quality check complete: {len(self.quality_report.issues)} issues found"
        )
        
        # Initialize SQL generator with schema and quality info
        self.sql_generator = SQLGenerator(
            llm_client=self.llm_client,
            schema=self.schema,
            quality_report=self.quality_report
        )
        
        logger.info("Agent initialization complete")
    
    def ask(self, question: str) -> FormattedAnswer:
        """
        Answer a natural language question about the database.
        
        Args:
            question: Natural language question
        
        Returns:
            FormattedAnswer with complete response
        
        Raises:
            ValueError: If agent not initialized
        """
        if not self.schema or not self.sql_generator:
            raise ValueError(
                "Agent not initialized. Call initialize() first."
            )
        
        logger.info(f"Processing question: {question}")
        
        # Attempt to answer with retries
        for attempt in range(self.max_retry_attempts + 1):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retry_attempts + 1}")
                
                # Generate SQL
                logger.info("Generating SQL...")
                sql_query = self.sql_generator.generate(question)
                logger.info(f"Generated SQL: {sql_query.sql}")
                
                # Execute SQL
                logger.info("Executing SQL...")
                execution_result = self.sql_executor.execute(sql_query.sql)
                
                # Validate results
                if self.enable_validation:
                    logger.info("Validating results...")
                    validation = self.result_validator.validate(
                        execution_result, sql_query, question
                    )
                else:
                    validation = ValidationResult(
                        is_valid=True,
                        confidence=1.0,
                        issues=[],
                        suggestions=[]
                    )
                
                # If execution succeeded and validation passed, format answer
                if execution_result.success and (validation.is_valid or not self.enable_validation):
                    logger.info("Formatting answer...")
                    answer = self.answer_formatter.format(
                        question, sql_query, execution_result, validation
                    )
                    
                    logger.info(
                        f"Answer generated with confidence {answer.confidence:.2f}"
                    )
                    return answer
                
                # If validation failed but we have results, still return but with warnings
                if execution_result.success and not validation.is_valid:
                    logger.warning(
                        f"Validation failed but returning results anyway "
                        f"(confidence: {validation.confidence:.2f})"
                    )
                    answer = self.answer_formatter.format(
                        question, sql_query, execution_result, validation
                    )
                    return answer
                
                # If execution failed, try to refine query
                if attempt < self.max_retry_attempts:
                    logger.warning(
                        f"Execution failed: {execution_result.error}. Retrying..."
                    )
                    
                    # Refine query based on error
                    refinement = f"Previous query failed with error: {execution_result.error}. Please fix the query."
                    sql_query = self.sql_generator.refine_query(sql_query, refinement)
                else:
                    # Max retries reached, return error answer
                    logger.error("Max retries reached, returning error answer")
                    validation = ValidationResult(
                        is_valid=False,
                        confidence=0.0,
                        issues=[execution_result.error or "Unknown error"],
                        suggestions=[]
                    )
                    answer = self.answer_formatter.format(
                        question, sql_query, execution_result, validation
                    )
                    return answer
            
            except Exception as e:
                logger.error(f"Error in attempt {attempt + 1}: {e}")
                
                if attempt >= self.max_retry_attempts:
                    # Return error answer
                    error_result = ExecutionResult(
                        success=False,
                        rows=[],
                        column_names=[],
                        row_count=0,
                        execution_time_ms=0,
                        error=str(e)
                    )
                    
                    error_query = SQLQuery(
                        sql="",
                        explanation="Query generation failed",
                        tables_used=[],
                        columns_used=[],
                        confidence=0.0,
                        warnings=[str(e)]
                    )
                    
                    validation = ValidationResult(
                        is_valid=False,
                        confidence=0.0,
                        issues=[str(e)],
                        suggestions=[]
                    )
                    
                    return self.answer_formatter.format(
                        question, error_query, error_result, validation
                    )
        
        # Fallback (should not reach here)
        raise RuntimeError("Unexpected error in answer generation")
    
    def get_schema_summary(self) -> str:
        """
        Get human-readable schema summary.
        
        Returns:
            Formatted schema description
        
        Raises:
            ValueError: If agent not initialized
        """
        if not self.schema:
            raise ValueError("Agent not initialized. Call initialize() first.")
        
        return self.schema_inspector.get_schema_summary(self.schema)
    
    def get_quality_summary(self) -> str:
        """
        Get human-readable data quality summary.
        
        Returns:
            Formatted quality report
        
        Raises:
            ValueError: If agent not initialized
        """
        if not self.quality_report:
            raise ValueError("Agent not initialized. Call initialize() first.")
        
        return self.data_quality_checker.get_quality_summary(self.quality_report)
    
    def explain_query(self, sql: str) -> dict:
        """
        Get execution plan for a SQL query.
        
        Args:
            sql: SQL query to explain
        
        Returns:
            Dictionary with execution plan
        """
        return self.sql_executor.explain_query(sql)
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection works
        """
        return self.sql_executor.test_connection()
