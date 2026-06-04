import mysql.connector
import random
from faker import Faker

fake = Faker()

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="college_erp_v2"
)

cursor = conn.cursor()


subject_department = {
    "DBMS": 1,
    "Operating Systems": 1,
    "Computer Networks": 1,
    "Data Structures": 1,
    "Algorithms": 1,
    "Artificial Intelligence": 1,
    "Machine Learning": 1,
    "Cloud Computing": 1,
    "Cyber Security": 1,
    "Compiler Design": 1,

    "Web Development": 3,
    "Data Science": 3,
    "Big Data": 3,
    "Deep Learning": 3,
    "IoT": 3,

    "Digital Electronics": 2,
    "Microprocessors": 2,
    "Embedded Systems": 2,

    "Thermodynamics": 4,
    "Fluid Mechanics": 4,
    "Manufacturing": 4,

    "Structural Engineering": 5,
    "Surveying": 5
}




#Generate Faculty(50)
faculty_ids = []

for dept_id in range(1, 6):

    for _ in range(10):

        cursor.execute("""
        INSERT INTO faculty
        (faculty_name,email,department_id)
        VALUES (%s,%s,%s)
        """, (
            fake.name(),
            fake.unique.email(),
            dept_id
        ))

        faculty_ids.append(
            cursor.lastrowid
        )




#generate subjects
subject_ids = []

for subject, dept_id in subject_department.items():

    cursor.execute("""
    INSERT INTO subjects
    (subject_name,faculty_id,department_id)
    VALUES (%s,%s,%s)
    """, (
        subject,
        random.choice(faculty_ids),
        dept_id
    ))

    subject_ids.append(
        cursor.lastrowid
    )

#GENERATE STUDENTS
student_ids = []

for _ in range(2000):

    dept_id = random.randint(1, 5)

    cursor.execute("""
    INSERT INTO students
    (name,email,department_id,year,cgpa)
    VALUES (%s,%s,%s,%s,%s)
    """, (
        fake.name(),
        fake.unique.email(),
        dept_id,
        random.randint(1, 4),
        round(
            random.uniform(6.0, 9.9),
            2
        )
    ))

    student_ids.append(
        cursor.lastrowid
    )

#GENERATE FEES
for student_id in student_ids:

    status = random.choice(
        ["PAID", "PENDING", "PARTIAL"]
    )

    amount = (
        0 if status == "PAID"
        else random.randint(
            5000,
            85000
        )
    )

    cursor.execute("""
    INSERT INTO fees
    (student_id,amount_due,payment_status)
    VALUES (%s,%s,%s)
    """, (
        student_id,
        amount,
        status
    ))


#generate marks
for student_id in student_ids:

    for subject_id in subject_ids:

        cursor.execute("""
        INSERT INTO marks
        (student_id,subject_id,marks)
        VALUES (%s,%s,%s)
        """, (
            student_id,
            subject_id,
            random.randint(35,100)
        ))

#Generate Attendance
for student_id in student_ids:

    for subject_id in subject_ids:

        cursor.execute("""
        INSERT INTO attendance
        (student_id,subject_id,attendance_percentage)
        VALUES (%s,%s,%s)
        """, (
            student_id,
            subject_id,
            round(
                random.uniform(
                    50,
                    100
                ),
                2
            )
        ))

#Generate Placements

companies = [
    "Google",
    "Microsoft",
    "Amazon",
    "Zoho",
    "Freshworks",
    "TCS",
    "Infosys",
    "Accenture"
]

for student_id in random.sample(
    student_ids,
    800
):

    cursor.execute("""
    INSERT INTO placements
    (student_id,company_name,package_lpa,status)
    VALUES (%s,%s,%s,%s)
    """, (
        student_id,
        random.choice(companies),
        round(
            random.uniform(
                3,
                30
            ),
            2
        ),
        "PLACED"
    ))


#Generate Scholarships
for student_id in random.sample(
    student_ids,
    400
):

    cursor.execute("""
    INSERT INTO scholarships
    (student_id,scholarship_name,amount)
    VALUES (%s,%s,%s)
    """, (
        student_id,
        "Merit Scholarship",
        random.randint(
            10000,
            50000
        )
    ))

#Generate Exams
for subject_id in subject_ids:

    cursor.execute("""
    INSERT INTO exams
    (subject_id,exam_date,max_marks)
    VALUES (%s,%s,%s)
    """, (
        subject_id,
        fake.date_between(
            start_date="+1d",
            end_date="+180d"
        ),
        100
    ))

#Genearte users
#admin
cursor.execute("""
INSERT INTO users
(username,password,role)
VALUES
('admin','admin123','admin')
""")

#Faculty users
cursor.execute("""
SELECT faculty_id
FROM faculty
""")

for row in cursor.fetchall():

    cursor.execute("""
    INSERT INTO users
    (username,password,role,faculty_id)
    VALUES (%s,%s,%s,%s)
    """, (
        f"faculty{row[0]}",
        "faculty123",
        "teacher",
        row[0]
    ))

#student users
cursor.execute("""
SELECT student_id
FROM students
""")

for row in cursor.fetchall():

    cursor.execute("""
    INSERT INTO users
    (username,password,role,student_id)
    VALUES (%s,%s,%s,%s)
    """, (
        f"student{row[0]}",
        "student123",
        "student",
        row[0]
    ))


conn.commit()

print("ERP Database Populated Successfully!")

cursor.close()
conn.close()