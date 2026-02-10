# =========================
# Imports
# =========================
import pandas as pd
from google import genai
from google.genai import types
import json
import os
import re
import sqlite3

from flask import Flask, render_template, request, session

# =========================
# Database connection
# =========================
client = genai.Client(api_key="AIzaSyDf5Qxq-MhDyknal2xXMM3L93nfkVk5OA4")
conn = sqlite3.connect("health.db", check_same_thread=False)


# load raw data
health_df = pd.read_csv("Health_dataset_1.csv")
lifestyle_df = pd.read_csv("Health_dataset_2.csv")

def clean_columns(df):
    df.columns = (
        df.columns
        .str.strip() # Removes trailing spaces
        .str.lower() # All column names are now lowercase
        .str.replace(" ","_")
    )
    return df

def clean_categories(df):
    for col in df.select_dtypes(exclude = "number"):
        df[col]=df[col].str.lower().str.strip()
    return df

# preprocessing
health_df = clean_columns(health_df)
lifestyle_df = clean_columns(lifestyle_df)

health_df = clean_categories(health_df)
lifestyle_df = clean_categories(lifestyle_df)

# validation
assert health_df["patient_number"].is_unique

# write to SQLite
conn = sqlite3.connect("health.db", check_same_thread=False)
health_df.to_sql("health", conn, if_exists="replace", index=False)
lifestyle_df.to_sql("lifestyle", conn, if_exists="replace", index=False)

def sql_schema(conn):
    query = """
    SELECT name, sql
    FROM sqlite_master
    WHERE type = 'table';
    """
    return pd.read_sql(query,conn)

schema_df = sql_schema(conn)

def format_schema_for_llm(schema_df):
    return "\n\n".join(schema_df["sql"].tolist())

schema_text = format_schema_for_llm(schema_df)

def is_personal_or_out_of_scope(question: str, schema_text: str) -> bool:
    q = question.lower()

    # Personal pronouns → personal prediction
    personal_markers = ["i ", "my ", "me ", "will i", "should i"]

    if any(p in q for p in personal_markers):
        return True

    # Concepts NOT present in dataset
    out_of_schema_terms = [
        "steps",
        "calories",
        "diet plan",
        "exercise plan",
        "weight loss",
        "gain weight",
        "should",
        "recommend"
    ]

    if any(term in q for term in out_of_schema_terms):
        return True

    return False

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
You are a data assistant.

Given a user question and a database schema, decide the correct execution method
and generate either a SQL query or Python code.

RULES:
- Use ONLY tables and columns present in the schema
- Join tables ONLY using patient_number
- Do NOT assume missing columns
- Do NOT explain anything
- Do NOT add comments
- The database engine is SQLite

EXECUTION DECISION:
- If the task can be solved using SQLite-compatible SQL, generate SQL
- If the task requires correlation or statistical computation that SQLite does NOT support,
  generate Python instead

If language = "python", you MUST also provide a SQL query to construct the DataFrame `df`.

OUTPUT FORMAT (STRICT JSON ONLY):

For SQL:
{
  "language": "sql",
  "query": "SQL QUERY HERE"
}

For Python:
{
  "language": "python",
  "query": "SQL QUERY TO BUILD df",
  "code": "PYTHON CODE TO EXECUTE ON df"
}
"""

# =========================
# Helper utilities
# =========================
def safe_json_parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("No JSON found in LLM output")
    return json.loads(match.group())

def build_llm_input(SYSTEM_PROMPT,schema_text,user_question):
    return f"""
{SYSTEM_PROMPT}

DATABASE SCHEMA:
{schema_text}

USER QUESTION:
{user_question}

"""

def generate_plan_llm(llm_input:str)-> dict:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=llm_input
    )
    return safe_json_parse(response.text)


def run_sql(query, conn):
    return pd.read_sql(query, conn)

def validate_sql(query: str):
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate"]
    q = query.lower()
    assert q.startswith("select")
    for word in forbidden:
        assert word not in q

def validate_python(code: str):
    forbidden = ["import", "__", "open(", "exec(", "eval(", "os.", "sys.", "while", "for"]
    for token in forbidden:
        assert token not in code.lower()

def run_python(code: str, df: pd.DataFrame):
    safe_globals = {"__builtins__": { "print": print}, "df": df}
    safe_locals = {}
    exec(code, safe_globals, safe_locals)
    return safe_locals

# =========================
# INSIGHT PROMPTS
# =========================
def build_sql_insight_prompt(user_question, result_df):
    return f"""
You are a health analytics assistant.

User question:
{user_question}

Computed results:
{result_df.to_dict(orient="records")}

Rules:
- Base conclusions ONLY on the provided results
- Do NOT introduce new data
- Avoid medical diagnosis
- Provide descriptive insights only
- Frame answers as population-level insights, not personal outcomes
"""

def build_python_insight_prompt(user_question, python_result):
    return f"""
You are a health analytics assistant.

User question:
{user_question}

Computed result:
{python_result}

Rules:
- Explain the result in simple, user-friendly language
- Clearly state whether the relationship is strong, weak, or negligible
- Avoid statistical jargon unless necessary
- Do NOT mention exact coefficient values unless helpful
- Do NOT provide medical diagnosis or advice

Response style:
- Greet the user first.
- Explain in plain english within hundred words in paragraph.
- Include percentages if required.
- Do not explain the relationships, just answer in comaprison terms.
- Focus on practical interpretation
- Recommend the user to Consult the Doctor for professional advice.
- Frame answers as population-level insights, not personal outcomes.
"""

def generate_insight_llm(insight_prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=insight_prompt
    )
    return response.text

# =========================
# Flask App
# =========================
app = Flask("Health assistant")
app.secret_key = "simple-secret-key"

@app.route("/", methods=["GET", "POST"])
def index():

    if "chat" not in session:
        session["chat"] = []

    if request.method == "POST":

        raw_question = request.form["question"]

        # Case 1: Personal / out-of-scope
        if is_personal_or_out_of_scope(raw_question, schema_text):
            answer = (
                "I can’t provide personal health predictions or advice. "
                "However, I can share population-level insights based on the dataset, "
                "such as whether physical activity is generally associated with BMI."
            )

        # Case 2: Dataset-based
        else:
            user_question = raw_question

            llm_input = build_llm_input(
                SYSTEM_PROMPT,
                schema_text,
                user_question
            )
            llm_output = generate_plan_llm(llm_input)

            if llm_output["language"] == "sql":
                validate_sql(llm_output["query"])
                df = run_sql(llm_output["query"], conn)
                insight_prompt = build_sql_insight_prompt(user_question, df)

            elif llm_output["language"] == "python":
                validate_sql(llm_output["query"])
                df = run_sql(llm_output["query"], conn)

                validate_python(llm_output["code"])
                python_result = run_python(llm_output["code"], df)
                insight_prompt = build_python_insight_prompt(
                    user_question,
                    python_result
                )

            
            answer = generate_insight_llm(insight_prompt)

        # Always append
        session["chat"].append({
            "question": raw_question,
            "answer": answer
        })
        session.modified = True

    return render_template("index.html", chat=session["chat"])


if __name__ == "__main__":
    app.run(debug=True)
