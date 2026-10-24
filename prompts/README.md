# SQL Generation Prompts - Easy to Modify! 🎯

## 📁 Files

- **`sql_generation_prompts.py`** - All prompts in one place
- **`all_prompts.txt`** - Human-readable version (auto-generated)
- **`test_prompts.py`** - Test your modified prompts

## 🎨 How to Modify Prompts

### 1. Edit the Main Prompts

Open `sql_generation_prompts.py` and modify:

```python
class SQLPrompts:
    # This is the main system prompt
    SYSTEM_PROMPT_TEMPLATE = """
    You are an expert SQL generator...
    
    [EDIT THIS SECTION]
    """
    
    # User prompt template
    USER_PROMPT_TEMPLATE = """
    Convert this question...
    
    [EDIT THIS SECTION]
    """
```

### 2. Add More Examples

In `SYSTEM_PROMPT_TEMPLATE`, add more examples:

```python
EXAMPLES:

Question: "Your new example question"
Answer: {{"sql": "SELECT ...", "explanation": "...", "confidence": 0.9}}
```

**Common Examples to Add:**

```python
# Date filtering
Question: "Show schools founded after 2000"
Answer: {{"sql": "SELECT * FROM schools WHERE founded_year > 2000 LIMIT 1000", ...}}

# Multiple conditions
Question: "Schools in District 1 with more than 100 students"
Answer: {{"sql": "SELECT s.* FROM schools s JOIN enrollment_history e ON s.school_id = e.school_id WHERE s.district = 'District 1' AND e.total_students > 100 LIMIT 1000", ...}}

# Percentage calculation
Question: "What percentage of teachers teach Math?"
Answer: {{"sql": "SELECT (COUNT(CASE WHEN subject = 'Math' THEN 1 END) * 100.0 / COUNT(*)) as pct FROM teachers LIMIT 1000", ...}}
```

### 3. Change Rules

Modify the CRITICAL RULES section:

```python
CRITICAL RULES:
1. Generate ONLY valid SQLite queries
2. [ADD YOUR RULE HERE]
3. [MODIFY EXISTING RULES]
```

### 4. Adjust Temperature & Behavior

In `src/sql_generator.py`, modify:

```python
response = self.llm_client.generate(
    prompt=user_prompt,
    system_prompt=system_prompt,
    temperature=0.1  # Change this: 0.0=deterministic, 1.0=creative
)
```

## 🧪 Testing Your Changes

### Method 1: Quick Test

```bash
python prompts/test_prompts.py
```

### Method 2: Full Test

```bash
python test_improved.py
```

### Method 3: Interactive Test

```python
from prompts.sql_generation_prompts import SQLPrompts, test_prompt_with_question
from src.schema_inspector import SchemaInspector

# Load your schema
inspector = SchemaInspector("data/test_messy.db")
schema = inspector.inspect()

# Test a question
test_prompt_with_question(
    question="How many schools are there?",
    schema_info=schema
)
```

## 📝 Prompt Variations

### For Faster/Smaller Models

Use `PromptVariations.SIMPLE_PROMPT`:

```python
# In sql_generator.py
if use_simple_prompt:
    prompt = PromptVariations.SIMPLE_PROMPT.format(
        question=question,
        schema=schema_summary
    )
```

### For More Accurate Results

Use `PromptVariations.DETAILED_EXAMPLES`:

```python
# Add to SYSTEM_PROMPT_TEMPLATE
{detailed_examples_section}
```

### For Strict Control

Use `PromptVariations.STRICT_PROMPT`:

```python
# Very explicit rules
prompt = PromptVariations.STRICT_PROMPT.format(
    question=question,
    table_names=["schools", "teachers"]
)
```

## 🎯 Common Modifications

### 1. Change Response Format

Current format:
```json
{"sql": "...", "explanation": "...", "tables_used": [...], "columns_used": [...], "confidence": 0.9}
```

To change, modify:
```python
RESPONSE FORMAT (MUST BE VALID JSON):
{{"sql": "...", "your_field": "..."}}
```

Then update `_parse_llm_response()` in `sql_generator.py`.

### 2. Add Domain-Specific Knowledge

```python
DOMAIN KNOWLEDGE:
- "Enrollment" means total_students column
- "Falling" means current year < previous year
- "Teacher count" means COUNT(DISTINCT teacher_id)
```

### 3. Handle Specific Errors

```python
COMMON MISTAKES TO AVOID:
- Don't use SELECT * in production
- Always handle NULLs in aggregations
- Use table aliases for readability
```

## 📊 Export & Review

Export all prompts to text file:

```bash
python prompts/sql_generation_prompts.py
```

This creates `prompts/all_prompts.txt` with all prompts in readable format.

## 🔧 Advanced: Dynamic Prompts

Create prompts based on question type:

```python
def get_prompt_for_question_type(question: str):
    if "compare" in question.lower():
        return COMPARISON_PROMPT
    elif "average" in question.lower():
        return AGGREGATION_PROMPT
    else:
        return STANDARD_PROMPT
```

## 💡 Tips

1. **Keep Examples Relevant**: Add examples similar to your use case
2. **Test Incrementally**: Change one thing at a time
3. **Monitor Confidence**: Low confidence? Add more examples
4. **Check JSON**: Always validate JSON format
5. **Use Clear Language**: LLM responds better to clear instructions

## 🐛 Debugging Prompts

If queries fail:

1. **Print the prompt**:
```python
print(system_prompt)
print(user_prompt)
```

2. **Check LLM response**:
```python
response = llm_client.generate(...)
print(response.content)  # See raw LLM output
```

3. **Test manually**:
```bash
ollama run llama3.2:3b
>>> [paste your prompt]
```

## 📚 Resources

- SQLite Syntax: https://www.sqlite.org/lang.html
- Prompt Engineering: https://platform.openai.com/docs/guides/prompt-engineering
- Our Schema: `data/test_messy.db`

## 🤝 Contributing

Modified prompts that work well? Share them!

1. Test thoroughly
2. Document what improved
3. Add to `PromptVariations`

---

**Remember**: The best prompts come from iteration. Start simple, test, improve! 🚀
