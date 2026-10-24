"""
All SQL Generation Prompts - Centralized and Easy to Modify

Yahan saare prompts ek jagah hain. Tum easily modify kar sakte ho!
"""

class SQLPrompts:
    """Centralized prompts for SQL generation"""
    
    # ========== SYSTEM PROMPT ==========
    SYSTEM_PROMPT_TEMPLATE = """You are an expert SQL query generator. Your job is to convert natural language questions into accurate SQL queries.

CRITICAL RULES:
1. Generate ONLY valid SQLite queries
2. Use ONLY tables and columns that exist in the schema below
3. Never use DROP, DELETE, UPDATE, INSERT, or other destructive operations
4. Use appropriate JOINs based on foreign key relationships
5. Include WHERE clauses for filters and date ranges
6. Use aggregate functions (COUNT, SUM, AVG, etc.) when appropriate
7. Always add LIMIT 1000 clause for safety
8. Handle NULL values explicitly in comparisons

{schema_section}

{quality_section}

IMPORTANT JOIN RULE:
When joining tables, use correct table aliases! 
- If alias 's' = students table, use s.student_id, s.school_id (NOT s.school_name)
- If alias 'sc' = schools table, use sc.school_name, sc.school_id
Example: SELECT sc.school_name FROM students s JOIN schools sc ON s.school_id = sc.school_id

EXAMPLES:

Question: "How many schools are there?"
Answer: {{"sql": "SELECT COUNT(*) FROM schools LIMIT 1000", "explanation": "Count total schools", "tables_used": ["schools"], "columns_used": ["*"], "confidence": 0.9}}

Question: "Students per school"
Answer: {{"sql": "SELECT sc.school_name, COUNT(st.student_id) as student_count FROM schools sc LEFT JOIN students st ON sc.school_id = st.school_id GROUP BY sc.school_id, sc.school_name LIMIT 1000", "explanation": "Count students per school using proper table aliases", "tables_used": ["schools", "students"], "columns_used": ["school_name", "student_id"], "confidence": 0.9}}

Question: "What is the average teacher salary?"
Answer: {{"sql": "SELECT AVG(salary) FROM teachers WHERE salary IS NOT NULL LIMIT 1000", "explanation": "Calculate average salary excluding nulls", "tables_used": ["teachers"], "columns_used": ["salary"], "confidence": 0.9}}

Question: "Which schools had enrollment changes between 2021 and 2023?"
Answer: {{"sql": "SELECT sc.school_name, e1.total_students as y2021, e2.total_students as y2023, (e1.total_students - e2.total_students) as change FROM schools sc JOIN enrollment_history e1 ON sc.school_id = e1.school_id AND e1.year = 2021 JOIN enrollment_history e2 ON sc.school_id = e2.school_id AND e2.year = 2023 WHERE e1.total_students IS NOT NULL AND e2.total_students IS NOT NULL ORDER BY change DESC LIMIT 1000", "explanation": "Compare enrollment between two years using self-join on enrollment_history table", "tables_used": ["schools", "enrollment_history"], "columns_used": ["school_name", "total_students", "year"], "confidence": 0.9}}

RESPONSE FORMAT (MUST BE VALID JSON):
{{"sql": "SELECT...", "explanation": "text", "tables_used": ["t1"], "columns_used": ["c1"], "confidence": 0.9}}

IMPORTANT: Return ONLY the JSON object, no additional text."""

    # ========== USER PROMPT ==========
    USER_PROMPT_TEMPLATE = """Convert this question into a SQL query:

Question: {question}

Remember: Return ONLY valid JSON with sql, explanation, tables_used, columns_used, and confidence."""

    # ========== REFINEMENT PROMPT ==========
    REFINEMENT_PROMPT_TEMPLATE = """The previous SQL query failed with this error:

Original SQL:
{original_sql}

Error:
{error_message}

Please generate a corrected SQL query that fixes this error.

Question: {question}

Return ONLY valid JSON: {{"sql": "...", "explanation": "...", "tables_used": [...], "columns_used": [...], "confidence": 0.9}}"""

    # ========== SCHEMA FORMATTING ==========
    SCHEMA_SECTION_TEMPLATE = """Schema Information:

{tables_info}

{relationships_info}"""

    # ========== QUALITY NOTES ==========
    QUALITY_SECTION_TEMPLATE = """Data Quality Notes:
{quality_issues}"""

    @staticmethod
    def build_system_prompt(schema_text: str, quality_text: str = None) -> str:
        """Build complete system prompt with schema and quality info"""
        
        prompt = SQLPrompts.SYSTEM_PROMPT_TEMPLATE.format(
            schema_section=schema_text,
            quality_section=quality_text if quality_text else "No significant data quality issues."
        )
        return prompt
    
    @staticmethod
    def build_user_prompt(question: str) -> str:
        """Build user prompt with question"""
        return SQLPrompts.USER_PROMPT_TEMPLATE.format(question=question)
    
    @staticmethod
    def build_refinement_prompt(question: str, original_sql: str, error: str) -> str:
        """Build refinement prompt for retry"""
        return SQLPrompts.REFINEMENT_PROMPT_TEMPLATE.format(
            question=question,
            original_sql=original_sql,
            error_message=error
        )
    
    @staticmethod
    def format_schema(schema_info) -> str:
        """Format schema for prompt"""
        lines = []
        
        for table_name, table_info in schema_info.tables.items():
            lines.append(f"\nTable: {table_name} ({table_info.row_count} rows)")
            
            for col in table_info.columns:
                flags = []
                if col.primary_key:
                    flags.append("PRIMARY KEY")
                if not col.nullable:
                    flags.append("NOT NULL")
                
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                
                sample_str = ""
                if col.sample_values:
                    samples = [str(v)[:30] for v in col.sample_values[:3]]
                    sample_str = f" (examples: {', '.join(samples)})"
                
                lines.append(f"  - {col.name}: {col.data_type}{flag_str}{sample_str}")
            
            if table_info.foreign_keys:
                lines.append("  Foreign Keys:")
                for fk in table_info.foreign_keys:
                    lines.append(f"    - {fk['column']} -> {fk['references_table']}.{fk['references_column']}")
        
        tables_text = "\n".join(lines)
        
        # Relationships
        rel_lines = []
        if schema_info.relationships:
            rel_lines.append("\nRelationships:")
            for rel in schema_info.relationships:
                rel_lines.append(
                    f"  - {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']} ({rel['type']})"
                )
        
        relationships_text = "\n".join(rel_lines)
        
        return SQLPrompts.SCHEMA_SECTION_TEMPLATE.format(
            tables_info=tables_text,
            relationships_info=relationships_text
        )
    
    @staticmethod
    def format_quality_notes(quality_report) -> str:
        """Format quality report for prompt"""
        if not quality_report or not quality_report.issues:
            return ""
        
        notes = []
        
        for issue in quality_report.get_critical_issues()[:5]:
            if issue.issue_type == 'nulls':
                notes.append(
                    f"  - {issue.table}.{issue.column}: High NULL rate ({issue.affected_rows} nulls), "
                    f"use IS NULL checks or COALESCE"
                )
            elif issue.issue_type == 'format':
                notes.append(
                    f"  - {issue.table}.{issue.column}: Inconsistent formats detected"
                )
            elif issue.issue_type == 'duplicates':
                notes.append(
                    f"  - {issue.table}: Contains duplicate rows"
                )
        
        if notes:
            return SQLPrompts.QUALITY_SECTION_TEMPLATE.format(
                quality_issues="\n".join(notes)
            )
        else:
            return ""


# ========== ADDITIONAL PROMPT VARIATIONS ==========

class PromptVariations:
    """Different prompt styles - experiment karne ke liye!"""
    
    # More detailed examples
    DETAILED_EXAMPLES = """
DETAILED EXAMPLES:

1. Simple Count:
   Q: "How many records?"
   SQL: SELECT COUNT(*) FROM table_name LIMIT 1000
   Tip: Use COUNT(*) for all rows, COUNT(column) for non-null values

2. Average with Filter:
   Q: "What is average salary for teachers?"
   SQL: SELECT AVG(salary) FROM teachers WHERE salary IS NOT NULL LIMIT 1000
   Tip: Always exclude NULLs in aggregations

3. Year Comparison (Self-Join):
   Q: "Compare enrollment between 2021 and 2023"
   SQL: SELECT t1.name, t1.value as y2021, t2.value as y2023
        FROM table t1
        JOIN table t2 ON t1.id = t2.id
        WHERE t1.year = 2021 AND t2.year = 2023
   Tip: Use self-join with different year filters

4. Top N with Ordering:
   Q: "Show top 5 schools by enrollment"
   SQL: SELECT school_name, total_students 
        FROM schools 
        ORDER BY total_students DESC 
        LIMIT 5
   Tip: Always use ORDER BY before LIMIT

5. Group By with Aggregation:
   Q: "Average salary by department"
   SQL: SELECT department, AVG(salary) as avg_sal
        FROM employees
        WHERE salary IS NOT NULL
        GROUP BY department
        ORDER BY avg_sal DESC
        LIMIT 1000
   Tip: Use GROUP BY with aggregates, ORDER BY for sorting
"""

    # Simpler prompt for faster models
    SIMPLE_PROMPT = """Generate SQL query for: {question}

Schema: {schema}

Rules:
- Only SELECT queries
- Add LIMIT 1000
- Handle NULLs
- Return JSON: {{"sql": "...", "confidence": 0.9}}"""

    # Very strict prompt
    STRICT_PROMPT = """You MUST follow these rules EXACTLY:

1. Generate ONLY SQLite SELECT query
2. NO destructive operations (DROP, DELETE, UPDATE, INSERT)
3. Use ONLY these tables: {table_names}
4. Add "LIMIT 1000" at end
5. Return ONLY this JSON format:
   {{"sql": "SELECT...", "explanation": "...", "confidence": 0.9}}

Question: {question}

DO NOT add any text before or after the JSON."""


# ========== PROMPT TESTING UTILITIES ==========

def test_prompt_with_question(question: str, schema_info, quality_report=None):
    """Test a prompt with a specific question"""
    
    # Format schema and quality
    schema_text = SQLPrompts.format_schema(schema_info)
    quality_text = SQLPrompts.format_quality_notes(quality_report) if quality_report else None
    
    # Build prompts
    system_prompt = SQLPrompts.build_system_prompt(schema_text, quality_text)
    user_prompt = SQLPrompts.build_user_prompt(question)
    
    print("="*70)
    print("SYSTEM PROMPT")
    print("="*70)
    print(system_prompt)
    print("\n" + "="*70)
    print("USER PROMPT")
    print("="*70)
    print(user_prompt)
    print("\n")


def export_prompts_to_file(output_file: str):
    """Export all prompts to a text file for review"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("SQL GENERATION PROMPTS\n")
        f.write("="*70 + "\n\n")
        
        f.write("SYSTEM PROMPT TEMPLATE:\n")
        f.write("-"*70 + "\n")
        f.write(SQLPrompts.SYSTEM_PROMPT_TEMPLATE)
        f.write("\n\n")
        
        f.write("USER PROMPT TEMPLATE:\n")
        f.write("-"*70 + "\n")
        f.write(SQLPrompts.USER_PROMPT_TEMPLATE)
        f.write("\n\n")
        
        f.write("REFINEMENT PROMPT TEMPLATE:\n")
        f.write("-"*70 + "\n")
        f.write(SQLPrompts.REFINEMENT_PROMPT_TEMPLATE)
        f.write("\n\n")
        
        f.write("PROMPT VARIATIONS:\n")
        f.write("-"*70 + "\n")
        f.write(PromptVariations.DETAILED_EXAMPLES)
        f.write("\n\n")
        f.write(PromptVariations.SIMPLE_PROMPT)
        f.write("\n\n")
        f.write(PromptVariations.STRICT_PROMPT)
        f.write("\n")
    
    print(f"✓ Prompts exported to: {output_file}")


if __name__ == "__main__":
    # Export prompts for review
    export_prompts_to_file("prompts/all_prompts.txt")
    print("\nYou can now:")
    print("1. Edit prompts in: prompts/sql_generation_prompts.py")
    print("2. Review all prompts in: prompts/all_prompts.txt")
    print("3. Test with: python prompts/test_prompts.py")
