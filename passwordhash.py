import mysql.connector
import bcrypt

try:

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="college_erp_v2"
    )

    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id, password
    FROM users
    """)

    users = cursor.fetchall()

    print(f"Fetched {len(users)} users")

    for i, (user_id, password) in enumerate(users, start=1):

        hashed = bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt()
        ).decode()

        cursor.execute("""
        UPDATE users
        SET password = %s
        WHERE user_id = %s
        """, (hashed, user_id))

        if i % 100 == 0:
            print(f"{i} users processed...")

    conn.commit()

    print("All passwords hashed successfully!")

except Exception as e:

    print("Error:")
    print(e)

finally:

    cursor.close()
    conn.close()