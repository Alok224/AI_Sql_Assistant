import sqlite3

# conn = sqlite3.connect("Student.db")

conn = sqlite3.connect(r"F:\Desktop\Chatsql_agentic\Chatsql\database\Student.db")

cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cursor.fetchall())

cursor.execute("SELECT COUNT(*) FROM Students")
print("Rows:", cursor.fetchone())

cursor.execute("SELECT * FROM Students")
print(cursor.fetchall())

conn.close()

print("Connected Successfully")

conn.close()