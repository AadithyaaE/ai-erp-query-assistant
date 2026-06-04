from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import mysql.connector

from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI

st.set_page_config(page_title="ERP SQL Assistant", page_icon="🎓", layout="centered")

st.title("🎓 ERP SQL Assistant")
st.caption("Ask questions about the College ERP database")

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="college_erp",
    )
    cursor = conn.cursor()
except mysql.connector.Error:
    st.error("Database Connection Failed")
    st.stop()

db = SQLDatabase.from_uri("mysql+pymysql://root:root@localhost/college_erp")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

schema = db.get_table_info()

question = st.text_input("Ask a question")

if st.button("Generate Answer") and question:
    dangerous_words = [
        "delete",
        "drop",
        "update",
        "insert",
        "remove",
        "truncate",
        "alter",
        "modify",
    ]

    if any(word in question.lower() for word in dangerous_words):
        st.error("Only SELECT queries are allowed.")
        st.stop()

    # Check for duplicate student names in DB
    cursor.execute(
        """
        SELECT name
        FROM students
        GROUP BY name
        HAVING COUNT(*) > 1
        """
    )

    duplicate_names = [row[0] for row in cursor.fetchall()]

    duplicate_found = False
    for name in duplicate_names:
        if name.lower() in question.lower():
            cursor.execute(
                """
                SELECT student_id, name, department
                FROM students
                WHERE name = %s
                """,
                (name,),
            )
            students = cursor.fetchall()

            st.warning(f"Multiple students named {name} found. Please provide Student ID.")
            st.write(students)

            duplicate_found = True
            break

    if not duplicate_found:
        prompt = f"""
You are an expert MySQL developer.

Database Schema:
{schema}

Your task is to convert the question into a SQL query.

Rules:
- Output ONLY SQL.
- No explanations.
- No markdown.
- No code fences.
- Only SELECT queries.

Question:
{question}
"""

        try:
            response = llm.invoke(prompt)
        except Exception as e:
            if "429" in str(e):
                st.error("Gemini quota exceeded. Try again later.")
            else:
                st.error("Gemini Error")
                st.write(e)
            st.stop()

        # Extract SQL text from response
        sql_query = getattr(response, "content", None) or (response.get("content") if hasattr(response, "get") else None) or str(response)
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        st.subheader("Generated SQL")
        st.code(sql_query, language="sql")

        if not sql_query.upper().startswith("SELECT"):
            st.error("Only SELECT queries are allowed.")
        else:
            try:
                result = db.run(sql_query)
                st.subheader("Result")

                if not result:
                    st.warning("No matching records found.")
                else:
                    if "None" in str(result):
                        st.warning("Some records contain missing values.")
                    st.write(result)

            except Exception as e:
                st.error("Invalid SQL generated.")
                st.write(e)
