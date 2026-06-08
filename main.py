from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
import mysql.connector
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# DATABASE CONNECTION

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

print("\n===== LOGIN =====")

username = input("Username: ").strip()
password = input("Password: ").strip()

#LOGIN LOGIC
cursor.execute("""
SELECT password,
       role,
       student_id,
       faculty_id
FROM users
WHERE username = %s
""", (username,))

user = cursor.fetchone()

if user is None:
    print("Invalid username or password.")
    exit()

stored_hash = user[0]

if not bcrypt.checkpw(
    password.encode(),
    stored_hash.encode()
):
    print("Invalid username or password.")
    exit()

role = user[1]
student_id = user[2]
faculty_id = user[3]

print("\nLogin Successful!")
print("Role:", role)

if student_id:
    print("Student ID:", student_id)

if faculty_id:
    print("Faculty ID:", faculty_id)

# MAIN LOOP
while True:
    question = input(
        "\nAsk a question (type 'exit' to quit): "
    ).strip()

    if question.lower() == "exit":
        print("Goodbye!")
        break

        # ==========================
    # ADMIN QUERY HISTORY
    # ==========================

    if role == "admin" and question.lower() == "show recent activity":

        cursor.execute("""
        SELECT username,
               question,
               created_at
        FROM query_logs
        ORDER BY created_at DESC
        LIMIT 20
        """)

        logs = cursor.fetchall()

        print("\nRecent Activity:")

        for row in logs:
            print(row)

        continue

    #TO FIND MOST ACTIVE USERS
    if role == "admin" and question.lower() == "show most active users":

        cursor.execute("""
        SELECT username,
            COUNT(*) AS total_queries
        FROM query_logs
        GROUP BY username
        ORDER BY total_queries DESC
        LIMIT 10
        """)

        results = cursor.fetchall()

        print("\nMost Active Users:")

        for row in results:
            print(row)

        continue

    #TO FIND FAILED QUERIES
    if role == "admin" and question.lower() == "show failed queries":

        cursor.execute("""
        SELECT username,
            question,
            created_at
        FROM query_logs
        WHERE status = 'FAILED'
        ORDER BY created_at DESC
        LIMIT 20
        """)

        results = cursor.fetchall()

        print("\nFailed Queries:")

        for row in results:
            print(row)

        continue

    #QUERY COUNT BY ROLE
    if role == "admin" and question.lower() == "show query statistics":

        cursor.execute("""
        SELECT role,
            COUNT(*)
        FROM query_logs
        GROUP BY role
        """)

        results = cursor.fetchall()

        print("\nQuery Statistics:")

        for row in results:
            print(row)

        continue

    #TOTAL QUERIES TODAY   
    if role == "admin" and question.lower() == "show total queries today":

        cursor.execute("""
        SELECT COUNT(*)
        FROM query_logs
        WHERE DATE(created_at) = CURDATE()
        """)

        result = cursor.fetchone()

        print(
            f"\nTotal Queries Today: {result[0]}"
        )

        continue

    # ==========================
    # USER QUERY HISTORY
    # ==========================

    if question.lower() == "show my query history":

        cursor.execute("""
        SELECT question,
               created_at
        FROM query_logs
        WHERE username = %s
        ORDER BY created_at DESC
        LIMIT 10
        """, (username,))

        history = cursor.fetchall()

        print("\nRecent Queries:")

        for i, row in enumerate(history, start=1):

            print(
                f"{i}. {row[0]} | {row[1]}"
            )

        continue

    # BLOCK DANGEROUS REQUESTS
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

    # DUPLICATE NAME CHECK
    cursor.execute("""
    SELECT name
    FROM students
    GROUP BY name
    HAVING COUNT(*) > 1
    """)

    duplicate_names = [row[0] for row in cursor.fetchall()]

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

            print(f"Multiple students named {name} found. Please provide student ID.")
            for student in students:
                print(student)

            duplicate_found = True
            break

    if duplicate_found:
        continue

    prompt = f"""
You are an expert MySQL developer.

Database Schema:
{schema}

Logged In User Information:
- Role: {role}
- Student ID: {student_id}
- Faculty ID: {faculty_id}

Your task is to convert the user's question into a SQL query.

General Rules:
- Output ONLY SQL.
- No explanations.
- No markdown.
- No code fences.
- Only SELECT queries.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or REPLACE statements.
- Use only tables and columns present in the schema.
- Generate syntactically correct MySQL queries.
IMPORTANT:

Before generating SQL, determine whether the user's question can be answered using ONLY the provided database schema.

If the question:
- References topics unrelated to the ERP database
- Mentions entities not present in the schema
- Asks about sports, weather, politics, celebrities, history, current events, or general knowledge
- References tables or columns that do not exist

Then output exactly:

INVALID_QUERY

Do not attempt to guess.
Do not attempt to find a similar table.
Do not generate a "closest" query.
Do not generate any SQL except INVALID_QUERY.

- Never guess.
- Never assume table names, column names, or values.
- If a requested table, column, or entity does not exist in the schema, output:

INVALID_QUERY

Fee Rules:
- fees.payment_status can contain:
  'PAID', 'PENDING', or 'PARTIAL'
- When a question refers to pending fees, unpaid fees, dues, outstanding fees, or fee defaulters, always filter using:
  payment_status = 'PENDING'

Subject Aliases:
- OS = Operating Systems
- Operating System = Operating Systems
- DBMS = Database Management Systems
- OOPS = Object Oriented Programming
- OOP = Object Oriented Programming
- CN = Computer Networks
- ML = Machine Learning
- AI = Artificial Intelligence
- DS = Data Structures
- COA = Computer Organization and Architecture

When a user uses an abbreviation, map it to the correct subject name before generating SQL.

Role-Based Rules:

Admin:
- Full access to all tables and records.

Teacher:
- Can access students, subjects, marks, attendance, departments, faculty, placements, scholarships, and academic information.
- Cannot access fee information.
- Never generate queries on the fees table.

Student:
- Can access ONLY their own records.
- Never access records belonging to other students.
- Never generate queries that return information about all students.
- Never generate queries about another student's records.
- For questions containing:
  "my", "me", "mine", "I"
  always filter using the logged-in student ID.
- For marks, attendance, fees, scholarships, placements, CGPA, and profile information:
  always include:
    student_id = {student_id}

Examples:

Question:
What are my marks?

SQL:
SELECT *
FROM marks
WHERE student_id = {student_id};

Question:
Show my attendance

SQL:
SELECT *
FROM attendance
WHERE student_id = {student_id};

Question:
Do I have pending fees?

SQL:
SELECT *
FROM fees
WHERE student_id = {student_id}
AND payment_status = 'PENDING';

Question:
Show my attendance in OOPS

SQL:
SELECT a.*
FROM attendance a
JOIN subjects s
ON a.subject_id = s.subject_id
WHERE a.student_id = {student_id}
AND s.subject_name = 'Object Oriented Programming';

Question:
Show my marks in DBMS

SQL:
SELECT m.*
FROM marks m
JOIN subjects s
ON m.subject_id = s.subject_id
WHERE m.student_id = {student_id}
AND s.subject_name = 'Database Management Systems';

Question:
Show all students

For a student user, do not generate a query returning all students.
Instead restrict the query to the logged-in student's records.

Question:
{question}
"""

    # Check for gemini quota exceeded
    try:
        response = llm.invoke(prompt)
    except Exception as e:
        if "429" in str(e):
            print("Gemini quota exceeded. Try again later.")
        else:
            print("Gemini Error")
            print(e)
        continue

    print("\nGenerated SQL:")
    print(response.content)

    # CLEAN SQL
    sql_query = response.content
    sql_query = sql_query.replace("```sql", "")
    sql_query = sql_query.replace("```", "")
    sql_query = sql_query.strip()

    if sql_query == "INVALID_QUERY":

        print(
            "The question cannot be answered using the available database schema."
        )

        continue

    sql_lower = sql_query.lower()
    if role == "teacher":
        if "fees" in sql_lower:
            print("Access Denied. Teachers cannot access fee information.")
            continue

    if role == "student":
        blocked_tables = [
            "faculty",
            "users"
        ]

        access_denied = False
        for table in blocked_tables:
            if table in sql_lower:
                print("Access Denied. Students cannot access this information.")
                access_denied = True
                break

        if access_denied:
            continue

        student_filter_1 = f"student_id = {student_id}".lower()
        student_filter_2 = f"student_id={student_id}".lower()

        if student_filter_1 not in sql_lower and student_filter_2 not in sql_lower:
            print("Access Denied. Students can only access their own records.")
            continue

    # ALLOW ONLY SELECT
    if not sql_query.upper().startswith("SELECT"):
        print("Only SELECT queries are allowed.")
        continue

    # EXECUTE QUERY
    try:
        result = db.run(sql_query)

        cursor.execute("""
        INSERT INTO query_logs
        (username, role, question, generated_sql, status)
        VALUES (%s, %s, %s, %s, %s)
        """, (
            username,
            role,
            question,
            sql_query,
            "SUCCESS"
        ))

        conn.commit()

        

        if not result:
            print("No matching records found.")
            continue

        if "None" in str(result):
            print("Some records contain missing values.")

        print("\nResult:")
        print(result)

    except Exception as e:

        cursor.execute("""
        INSERT INTO query_logs
        (username, role, question, generated_sql, status)
        VALUES (%s, %s, %s, %s, %s)
        """, (
            username,
            role,
            question,
            sql_query,
            "FAILED"
        ))

        conn.commit()

        print("Invalid SQL generated.")
        print(e)

        continue

    summary_prompt = f"""
Question:
{question}

Result:
{result}

Answer naturally in one or two sentences.
"""

    try:
        summary_response = llm.invoke(summary_prompt)
        print("\nAnswer:")
        print(summary_response.content)
    except Exception as e:
        print("Summary generation failed:", e)

  


cursor.close()
conn.close()
print("Database connection closed.")
