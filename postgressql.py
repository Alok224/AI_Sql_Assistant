# from sqlalchemy import create_engine, text
# 
# engine = create_engine("postgresql+psycopg2://postgres:12345678@localhost:5432/student_model")
# 
# with engine.connect() as conn:
#     result = conn.execute(text("SELECT version();"))
#     print(result.fetchone())


import psycopg2


connection = psycopg2.connect(
    database="student_model",   
    user="postgres",   
    password="12345678",  
    host="localhost",
    port="5432"
)

cursor = connection.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(25),
    class VARCHAR(25),
    Section VARCHAR(25),
    Marks int
);
""")


cursor.execute('''INSERT INTO students (name, class,Section,Marks) VALUES ('Alok','MCA','A',450)''')
cursor.execute('''INSERT INTO students (name, class,Section,Marks) VALUES ('Rahul','Btech','B',400)''')
cursor.execute('''INSERT INTO students (name, class,Section,Marks) VALUES ('Rohit','MBA','C',350)''')
cursor.execute('''INSERT INTO students (name, class,Section,Marks) VALUES ('Sahil','MBA','A',300)''')
cursor.execute('''INSERT INTO students (name, class,Section,Marks) VALUES ('Aman','MCA','B',250)''')


# connection.commit()


cursor.execute("SELECT * FROM students")
data = cursor.fetchall()
for row in data:
    print(row)

# Commit changes
connection.commit()



cursor.close()
connection.close()


