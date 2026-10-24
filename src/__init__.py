"""
Data-Analyst Agent for Messy Databases

An AI-powered agent that answers business questions by analyzing databases,
generating SQL queries, and providing validated answers.
"""

__version__ = "0.1.0"
__author__ = "Data Analyst Agent Team"

from .agent import DataAnalystAgent
from .schema_inspector import SchemaInspector
from .data_quality import DataQualityChecker
from .sql_generator import SQLGenerator
from .sql_executor import SQLExecutor
from .result_validator import ResultValidator
from .answer_formatter import AnswerFormatter

__all__ = [
    "DataAnalystAgent",
    "SchemaInspector",
    "DataQualityChecker",
    "SQLGenerator",
    "SQLExecutor",
    "ResultValidator",
    "AnswerFormatter",
]
