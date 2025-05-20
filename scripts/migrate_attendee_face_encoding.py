import sqlite3

conn = sqlite3.connect('events.db')
c = conn.cursor()
try:
    c.execute('ALTER TABLE attendees ADD COLUMN face_encoding BLOB')
    print('face_encoding column added to attendees table.')
except sqlite3.OperationalError:
    print('face_encoding column already exists.')
conn.commit()
conn.close()
