"""
Result Validator - Verifies query results match the question intent.

Checks for common issues like:
- Empty results vs. failed queries
- NULL values in critical columns
- Unexpected data ranges
- Duplicate or inconsistent results
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .sql_executor import ExecutionResult
from .sql_generator import SQLQuery

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating query execution."""
    is_valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    
    def add_issue(self, issue: str):
        """Add a validation issue."""
        self.issues.append(issue)
        self.confidence *= 0.9  # Reduce confidence with each issue
    
    def add_suggestion(self, suggestion: str):
        """Add a suggestion for improvement."""
        self.suggestions.append(suggestion)


class ResultValidator:
    """
    Validates SQL execution results to ensure they answer the user's question.
    
    Performs sanity checks and detects common issues.
    """
    
    def __init__(
        self,
        check_nulls: bool = True,
        check_duplicates: bool = True,
        check_ranges: bool = True
    ):
        """
        Initialize result validator.
        
        Args:
            check_nulls: Check for excessive NULL values
            check_duplicates: Check for duplicate rows
            check_ranges: Check for reasonable date/numeric ranges
        """
        self.check_nulls = check_nulls
        self.check_duplicates = check_duplicates
        self.check_ranges = check_ranges
        
        logger.info("Initialized ResultValidator")
    
    def validate(
        self,
        execution_result: ExecutionResult,
        sql_query: SQLQuery,
        question: str
    ) -> ValidationResult:
        """
        Validate query execution results.
        
        Args:
            execution_result: Result from SQL execution
            sql_query: Original SQL query object
            question: Original user question
        
        Returns:
            ValidationResult with validation outcome
        """
        logger.info("Validating query results")
        
        validation = ValidationResult(
            is_valid=True,
            confidence=1.0,
            issues=[],
            suggestions=[]
        )
        
        # Check if execution succeeded
        if not execution_result.success:
            validation.is_valid = False
            validation.confidence = 0.0
            validation.add_issue(f"Query execution failed: {execution_result.error}")
            return validation
        
        # Check for empty results
        if execution_result.row_count == 0:
            validation.add_issue("Query returned no rows")
            validation.add_suggestion(
                "This could mean: (1) no data matches the criteria, "
                "(2) incorrect JOIN conditions, or (3) wrong filters"
            )
            validation.confidence = 0.3
            return validation
        
        # Check if truncated
        if execution_result.truncated:
            validation.add_issue(
                f"Results were truncated (showing first {execution_result.row_count} rows)"
            )
            validation.add_suggestion("Consider adding more specific filters to reduce result size")
        
        # Perform content validation
        if self.check_nulls:
            self._check_null_values(execution_result, validation)
        
        if self.check_duplicates:
            self._check_duplicates(execution_result, validation)
        
        if self.check_ranges:
            self._check_value_ranges(execution_result, validation)
        
        # Check result structure matches question intent
        self._check_question_alignment(execution_result, sql_query, question, validation)
        
        logger.info(
            f"Validation complete: valid={validation.is_valid}, "
            f"confidence={validation.confidence:.2f}, "
            f"issues={len(validation.issues)}"
        )
        
        return validation
    
    def _check_null_values(
        self,
        execution_result: ExecutionResult,
        validation: ValidationResult
    ):
        """Check for excessive NULL values in results."""
        
        if not execution_result.rows:
            return
        
        # Count NULLs per column
        null_counts = {col: 0 for col in execution_result.column_names}
        
        for row in execution_result.rows:
            for col_name, value in row.items():
                if value is None:
                    null_counts[col_name] += 1
        
        # Check each column
        total_rows = len(execution_result.rows)
        
        for col_name, null_count in null_counts.items():
            if null_count > 0:
                null_ratio = null_count / total_rows
                
                if null_ratio > 0.5:  # More than 50% nulls
                    validation.add_issue(
                        f"Column '{col_name}' has {null_count}/{total_rows} NULL values "
                        f"({null_ratio*100:.1f}%)"
                    )
                    validation.add_suggestion(
                        f"Consider using COALESCE or filtering out NULLs in '{col_name}'"
                    )
    
    def _check_duplicates(
        self,
        execution_result: ExecutionResult,
        validation: ValidationResult
    ):
        """Check for completely duplicate rows."""
        
        if len(execution_result.rows) < 2:
            return
        
        # Convert rows to tuples for hashing
        row_tuples = [tuple(sorted(row.items())) for row in execution_result.rows]
        unique_rows = len(set(row_tuples))
        duplicate_count = len(row_tuples) - unique_rows
        
        if duplicate_count > 0:
            dup_ratio = duplicate_count / len(row_tuples)
            
            if dup_ratio > 0.1:  # More than 10% duplicates
                validation.add_issue(
                    f"Results contain {duplicate_count} duplicate rows "
                    f"({dup_ratio*100:.1f}%)"
                )
                validation.add_suggestion(
                    "Consider using DISTINCT or checking for missing GROUP BY"
                )
    
    def _check_value_ranges(
        self,
        execution_result: ExecutionResult,
        validation: ValidationResult
    ):
        """Check if numeric and date values are in reasonable ranges."""
        
        if not execution_result.rows:
            return
        
        current_year = datetime.now().year
        
        for col_name in execution_result.column_names:
            values = [row[col_name] for row in execution_result.rows if row[col_name] is not None]
            
            if not values:
                continue
            
            # Check numeric ranges
            if all(isinstance(v, (int, float)) for v in values):
                min_val = min(values)
                max_val = max(values)
                
                # Check for suspiciously large ranges
                if max_val > 0 and min_val >= 0:
                    range_ratio = max_val / (min_val + 1)
                    if range_ratio > 10000:
                        validation.add_issue(
                            f"Column '{col_name}' has very wide range: {min_val} to {max_val}"
                        )
            
            # Check date values
            if all(isinstance(v, str) for v in values):
                # Try to parse as dates
                years = []
                for v in values[:10]:  # Sample first 10
                    year_match = self._extract_year(str(v))
                    if year_match:
                        years.append(year_match)
                
                if years:
                    min_year = min(years)
                    max_year = max(years)
                    
                    # Check for unreasonable years
                    if min_year < 1900 or max_year > current_year + 10:
                        validation.add_issue(
                            f"Column '{col_name}' contains suspicious years: {min_year}-{max_year}"
                        )
    
    def _check_question_alignment(
        self,
        execution_result: ExecutionResult,
        sql_query: SQLQuery,
        question: str,
        validation: ValidationResult
    ):
        """Check if results align with question intent."""
        
        question_lower = question.lower()
        
        # Check for aggregation intent
        agg_keywords = ['total', 'sum', 'average', 'count', 'how many', 'maximum', 'minimum']
        expects_aggregation = any(kw in question_lower for kw in agg_keywords)
        
        if expects_aggregation:
            # Should return few rows (aggregated results)
            if execution_result.row_count > 100:
                validation.add_issue(
                    f"Question suggests aggregation but query returned {execution_result.row_count} rows"
                )
                validation.add_suggestion(
                    "Consider adding GROUP BY or aggregate functions (COUNT, SUM, AVG)"
                )
        
        # Check for comparison intent
        comparison_keywords = ['compare', 'difference', 'vs', 'versus', 'between']
        expects_comparison = any(kw in question_lower for kw in comparison_keywords)
        
        if expects_comparison and execution_result.row_count == 1:
            validation.add_issue(
                "Question suggests comparison but query returned only 1 row"
            )
            validation.add_suggestion(
                "Consider grouping by the dimension you want to compare"
            )
        
        # Check for ranking/top intent
        ranking_keywords = ['top', 'bottom', 'highest', 'lowest', 'best', 'worst']
        expects_ranking = any(kw in question_lower for kw in ranking_keywords)
        
        if expects_ranking:
            # Should have ORDER BY and LIMIT
            sql_lower = sql_query.sql.lower()
            if 'order by' not in sql_lower:
                validation.add_issue("Question suggests ranking but query has no ORDER BY")
                validation.add_suggestion("Add ORDER BY clause to rank results")
            
            if 'limit' not in sql_lower:
                validation.add_suggestion("Consider adding LIMIT to show only top results")
    
    @staticmethod
    def _extract_year(date_str: str) -> Optional[int]:
        """Extract year from date string."""
        import re
        
        # Look for 4-digit year
        match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if match:
            return int(match.group())
        
        return None
    
    def suggest_fixes(
        self,
        validation: ValidationResult,
        execution_result: ExecutionResult
    ) -> List[str]:
        """
        Generate specific SQL fix suggestions based on validation issues.
        
        Args:
            validation: ValidationResult with issues
            execution_result: Original execution result
        
        Returns:
            List of SQL modification suggestions
        """
        fixes = []
        
        for issue in validation.issues:
            if 'NULL values' in issue:
                # Extract column name
                import re
                col_match = re.search(r"Column '(\w+)'", issue)
                if col_match:
                    col = col_match.group(1)
                    fixes.append(f"Add: WHERE {col} IS NOT NULL")
                    fixes.append(f"Or use: COALESCE({col}, 'default_value')")
            
            elif 'duplicate rows' in issue:
                fixes.append("Add: DISTINCT after SELECT")
                fixes.append("Or check if GROUP BY is needed")
            
            elif 'no ORDER BY' in issue:
                # Suggest ordering by first numeric column
                numeric_cols = [
                    col for col in execution_result.column_names
                    if any(
                        isinstance(row[col], (int, float))
                        for row in execution_result.rows
                        if row[col] is not None
                    )
                ]
                if numeric_cols:
                    fixes.append(f"Add: ORDER BY {numeric_cols[0]} DESC")
            
            elif 'truncated' in issue:
                fixes.append("Add more specific WHERE conditions")
                fixes.append("Or reduce date range")
        
        return fixes
