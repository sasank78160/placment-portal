import sqlite3

conn = sqlite3.connect("placement.db")
cursor = conn.cursor()

cursor.execute("ALTER TABLE placement_drives ADD COLUMN drive_code TEXT")

conn.commit()
conn.close()

print("Drive code column added successfully")