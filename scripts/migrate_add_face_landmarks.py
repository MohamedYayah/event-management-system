import sqlite3

DB_PATH = 'events.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Check if the column already exists
c.execute("PRAGMA table_info(attendees);")
columns = [col[1] for col in c.fetchall()]

if 'face_landmarks' not in columns:
    c.execute("ALTER TABLE attendees ADD COLUMN face_landmarks TEXT;")
    print("face_landmarks column added successfully!")
else:
    print("face_landmarks column already exists.")

conn.commit()
conn.close()
