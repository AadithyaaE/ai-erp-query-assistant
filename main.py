from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# ==========================
# DATABASE CONNECTION
# ==========================

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="college_erp_v2"
    )

    print("Database Connected!")

except mysql.connector.Error as e:

    print("Database Connection Failed")
    print(e)
    exit()

cursor = conn.cursor()

db = SQLDatabase.from_uri(
    "mysql+pymysql://root:root@localhost/college_erp_v2"
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash"
)

schema = db.get_table_info()

# ==========================
# MAIN LOOP
# ==========================

while True:

    question = input(
        "\nAsk a question (type 'exit' to quit): "
    ).strip()

    if question.lower() == "exit":
        print("Goodbye!")
        break

    # ==========================
    # BLOCK DANGEROUS REQUESTS
    # ==========================

    dangerous_words = [
        "delete",
        "drop",
        "update",
        "insert",
        "remove",
        "truncate",
        
        "alter",
        "modify"
    ]

    if any(word in question.lower() for word in dangerous_words):
        print("Only SELECT queries are allowed.")
        continue

    # ==========================
    # DUPLICATE NAME CHECK
    # ==========================

    cursor.execute("""
    SELECT name
    FROM students
    GROUP BY name
    HAVING COUNT(*) > 1
    """)

    duplicate_names = [
        row[0]
        for row in cursor.fetchall()
    ]

    duplicate_found = False

    for name in duplicate_names:

        if name.lower() in question.lower():

            cursor.execute("""
            SELECT student_id,
                   name,
                   department_id
            FROM students
            WHERE name = %s
            """, (name,))

            students = cursor.fetchall()

            print(
                f"Multiple students named {name} found. Please provide student ID."
            )

            for student in students:
                print(student)

            duplicate_found = True
            break

    if duplicate_found:
        continue

    # ==========================
    # PROMPT
    # ==========================

    prompt = f"""
You are an expert MySQL developer.

Database Schema:
{schema}

Your task is to convert the user's question into a SQL query.

Rules:
- Output ONLY SQL.
- No explanations.
- No markdown.
- No code fences.
- Only SELECT queries.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or CREATE statements.
- Use only tables and columns present in the schema.
- When a question refers to pending fees, unpaid fees, or dues, the query must filter using:
  WHERE payment_status = 'PENDING'
- fees.payment_status can contain:
  'PAID', 'PENDING', or 'PARTIAL'
- If the question cannot be answered using the schema, generate the closest valid SELECT query possible.

Question:
{question}
"""

    # ==========================
    # GEMINI CALL
    # ==========================

    try:

        response = llm.invoke(prompt)

    except Exception as e:

        if "429" in str(e):

            print(
                "Gemini quota exceeded. Try again later."
            )

        else:

            print("Gemini Error")
            print(e)

        continue

    print("\nGenerated SQL:")
    print(response.content)

    # ==========================
    # CLEAN SQL
    # ==========================

    sql_query = response.content

    sql_query = sql_query.replace(
        "```sql",
        ""
    )

    sql_query = sql_query.replace(
        "```",
        ""
    )

    sql_query = sql_query.strip()

    # ==========================
    # ALLOW ONLY SELECT
    # ==========================

    if not sql_query.upper().startswith(
        "SELECT"
    ):

        print(
            "Only SELECT queries are allowed."
        )

        continue

    # ==========================
    # EXECUTE QUERY
    # ==========================

    try:

        result = db.run(sql_query)

        if not result:

            print(
                "No matching records found."
            )

            continue

        if "None" in str(result):

            print(
                "Some records contain missing values."
            )

        print("\nResult:")
        print(result)

    except Exception as e:

        print(
            "Invalid SQL generated."
        )

        print(e)

        continue

    # ==========================
    # NATURAL LANGUAGE ANSWER
    # ==========================

    summary_prompt = f"""
Question:
{question}

Result:
{result}

Answer naturally in one or two sentences.
"""

    try:

        answer = llm.invoke(
            summary_prompt
        )

        print("\nAnswer:")
        print(answer.content)

    except Exception:

        pass

# ==========================
# CLOSE CONNECTIONS
# ==========================

cursor.close()
conn.close()
print("Database connection closed.")