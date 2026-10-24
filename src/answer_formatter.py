"""
Answer Formatter - Converts query results into natural language answers.

Generates clear, evidence-based answers with proper context and limitations.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .sql_executor import ExecutionResult
from .sql_generator import SQLQuery
from .result_validator import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class FormattedAnswer:
    """Complete formatted answer to user's question."""
    answer: str  # Direct answer to the question
    evidence: List[Dict[str, Any]]  # Supporting data
    explanation: str  # How the answer was calculated
    confidence: float  # Confidence level (0.0-1.0)
    limitations: List[str]  # Known limitations or caveats
    sql_query: str  # SQL used to generate answer
    metadata: Dict[str, Any]  # Additional metadata


class AnswerFormatter:
    """
    Formats query results into natural language answers.
    
    Provides context, evidence, and explicitly states limitations.
    """
    
    def __init__(self, show_sql: bool = True, max_evidence_rows: int = 10):
        """
        Initialize answer formatter.
        
        Args:
            show_sql: Include SQL query in formatted answer
            max_evidence_rows: Maximum rows to include as evidence
        """
        self.show_sql = show_sql
        self.max_evidence_rows = max_evidence_rows
        
        logger.info("Initialized AnswerFormatter")
    
    def format(
        self,
        question: str,
        sql_query: SQLQuery,
        execution_result: ExecutionResult,
        validation: ValidationResult
    ) -> FormattedAnswer:
        """
        Format complete answer from query results.
        
        Args:
            question: Original user question
            sql_query: Generated SQL query
            execution_result: Execution results
            validation: Validation results
        
        Returns:
            FormattedAnswer with natural language response
        """
        logger.info("Formatting answer")
        
        # Handle execution failure
        if not execution_result.success:
            return self._format_error_answer(question, sql_query, execution_result)
        
        # Handle empty results
        if execution_result.row_count == 0:
            return self._format_empty_answer(question, sql_query, validation)
        
        # Generate answer based on result type
        answer_text = self._generate_answer_text(
            question, execution_result, sql_query
        )
        
        # Select evidence rows
        evidence = execution_result.rows[:self.max_evidence_rows]
        
        # Generate explanation
        explanation = self._generate_explanation(
            sql_query, execution_result, validation
        )
        
        # Collect limitations
        limitations = self._collect_limitations(
            sql_query, execution_result, validation
        )
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(sql_query, validation, execution_result)
        
        # Metadata
        metadata = {
            "row_count": execution_result.row_count,
            "execution_time_ms": execution_result.execution_time_ms,
            "truncated": execution_result.truncated,
            "tables_used": sql_query.tables_used,
            "validation_issues": len(validation.issues)
        }
        
        return FormattedAnswer(
            answer=answer_text,
            evidence=evidence,
            explanation=explanation,
            confidence=confidence,
            limitations=limitations,
            sql_query=sql_query.sql if self.show_sql else "",
            metadata=metadata
        )
    
    def _format_error_answer(
        self,
        question: str,
        sql_query: SQLQuery,
        execution_result: ExecutionResult
    ) -> FormattedAnswer:
        """Format answer for failed execution."""
        
        return FormattedAnswer(
            answer=f"I was unable to answer this question due to a query execution error.",
            evidence=[],
            explanation=f"Error: {execution_result.error}",
            confidence=0.0,
            limitations=[
                "Query execution failed",
                "No results available",
                execution_result.error or "Unknown error"
            ],
            sql_query=sql_query.sql if self.show_sql else "",
            metadata={
                "error": execution_result.error,
                "row_count": 0,
                "execution_time_ms": 0,
                "truncated": False,
                "tables_used": sql_query.tables_used if sql_query else [],
                "validation_issues": 0
            }
        )
    
    def _format_empty_answer(
        self,
        question: str,
        sql_query: SQLQuery,
        validation: ValidationResult
    ) -> FormattedAnswer:
        """Format answer for empty results."""
        
        answer = "Based on the available data, no records match the specified criteria."
        
        limitations = [
            "No matching records found",
            "This could indicate: (1) the condition is too restrictive, "
            "(2) the data doesn't cover this time period or category, or "
            "(3) there may be a join or filter issue"
        ]
        
        limitations.extend(validation.suggestions)
        
        return FormattedAnswer(
            answer=answer,
            evidence=[],
            explanation=sql_query.explanation,
            confidence=0.3,
            limitations=limitations,
            sql_query=sql_query.sql if self.show_sql else "",
            metadata={
                "row_count": 0,
                "execution_time_ms": 0,
                "truncated": False,
                "tables_used": sql_query.tables_used if sql_query else [],
                "validation_issues": len(validation.issues)
            }
        )
    
    def _generate_answer_text(
        self,
        question: str,
        execution_result: ExecutionResult,
        sql_query: SQLQuery
    ) -> str:
        """Generate natural language answer text."""
        
        rows = execution_result.rows
        row_count = execution_result.row_count
        
        # Single value result (aggregation)
        if row_count == 1 and len(execution_result.column_names) == 1:
            col_name = execution_result.column_names[0]
            value = rows[0][col_name]
            
            if value is None:
                return "The result is NULL (no data available for this calculation)."
            
            # Format based on value type
            if isinstance(value, float):
                return f"The answer is **{value:,.2f}**."
            elif isinstance(value, int):
                return f"The answer is **{value:,}**."
            else:
                return f"The answer is **{value}**."
        
        # Multiple rows - summarize
        if row_count <= 5:
            # Small result - can list all
            return f"Found **{row_count}** matching record{'s' if row_count > 1 else ''}. See details below."
        elif row_count <= 20:
            return f"Found **{row_count}** matching records. Top results shown below."
        else:
            return (
                f"Found **{row_count}** matching records. "
                f"Showing top {min(self.max_evidence_rows, row_count)} results."
            )
    
    def _generate_explanation(
        self,
        sql_query: SQLQuery,
        execution_result: ExecutionResult,
        validation: ValidationResult
    ) -> str:
        """Generate explanation of how answer was calculated."""
        
        parts = [sql_query.explanation]
        
        # Add query details
        if sql_query.tables_used:
            parts.append(
                f"Data source: {', '.join(sql_query.tables_used)} "
                f"({execution_result.row_count} rows returned)"
            )
        
        # Add execution details
        exec_time = execution_result.execution_time_ms
        if exec_time < 1000:
            parts.append(f"Query completed in {exec_time:.0f}ms")
        else:
            parts.append(f"Query completed in {exec_time/1000:.1f}s")
        
        # Add validation warnings
        if validation.issues:
            parts.append(
                f"Note: {len(validation.issues)} validation issue(s) detected"
            )
        
        return ". ".join(parts) + "."
    
    def _collect_limitations(
        self,
        sql_query: SQLQuery,
        execution_result: ExecutionResult,
        validation: ValidationResult
    ) -> List[str]:
        """Collect all limitations and caveats."""
        
        limitations = []
        
        # Add SQL query warnings
        limitations.extend(sql_query.warnings)
        
        # Add validation issues
        limitations.extend(validation.issues)
        
        # Add truncation warning
        if execution_result.truncated:
            limitations.append(
                f"Results limited to {execution_result.row_count} rows. "
                "Full dataset may contain more records."
            )
        
        # Low confidence warning
        if validation.confidence < 0.5:
            limitations.append(
                "Low confidence in this answer. Manual verification recommended."
            )
        
        return limitations
    
    def _calculate_confidence(
        self,
        sql_query: SQLQuery,
        validation: ValidationResult,
        execution_result: ExecutionResult
    ) -> float:
        """Calculate overall confidence score."""
        
        # Start with SQL generation confidence
        confidence = sql_query.confidence
        
        # Combine with validation confidence
        confidence = (confidence + validation.confidence) / 2
        
        # Reduce for execution issues
        if execution_result.truncated:
            confidence *= 0.9
        
        if len(validation.issues) > 3:
            confidence *= 0.8
        
        return max(0.0, min(1.0, confidence))
    
    def format_as_text(self, formatted_answer: FormattedAnswer) -> str:
        """
        Convert FormattedAnswer to plain text format.
        
        Args:
            formatted_answer: FormattedAnswer to convert
        
        Returns:
            Plain text representation
        """
        lines = []
        
        # Answer
        lines.append("=" * 60)
        lines.append("ANSWER")
        lines.append("=" * 60)
        lines.append(formatted_answer.answer)
        lines.append("")
        
        # Evidence
        if formatted_answer.evidence:
            lines.append("EVIDENCE")
            lines.append("-" * 60)
            
            # Format as table
            if formatted_answer.evidence:
                headers = list(formatted_answer.evidence[0].keys())
                
                # Header row
                lines.append(" | ".join(str(h) for h in headers))
                lines.append("-" * 60)
                
                # Data rows
                for row in formatted_answer.evidence:
                    values = [str(row.get(h, ""))[:30] for h in headers]
                    lines.append(" | ".join(values))
            
            lines.append("")
        
        # Explanation
        lines.append("EXPLANATION")
        lines.append("-" * 60)
        lines.append(formatted_answer.explanation)
        lines.append("")
        
        # Confidence
        conf_pct = formatted_answer.confidence * 100
        conf_label = (
            "High" if conf_pct >= 80 else
            "Medium" if conf_pct >= 50 else
            "Low"
        )
        lines.append(f"Confidence: {conf_label} ({conf_pct:.0f}%)")
        lines.append("")
        
        # Limitations
        if formatted_answer.limitations:
            lines.append("LIMITATIONS & WARNINGS")
            lines.append("-" * 60)
            for lim in formatted_answer.limitations:
                lines.append(f"  ⚠ {lim}")
            lines.append("")
        
        # SQL (if enabled)
        if formatted_answer.sql_query:
            lines.append("SQL QUERY")
            lines.append("-" * 60)
            lines.append(formatted_answer.sql_query)
            lines.append("")
        
        return "\n".join(lines)
