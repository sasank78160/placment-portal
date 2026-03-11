import sqlite3

conn = sqlite3.connect("placement.db")
cursor = conn.cursor()

cursor.execute("UPDATE placement_drives SET status='Pending'")
conn.commit()

cursor.execute("SELECT id, job_title, status FROM placement_drives")
print(cursor.fetchall())

conn.close()