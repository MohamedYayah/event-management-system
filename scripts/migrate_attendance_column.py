import sqlite3

conn = sqlite3.connect('events.db')
c = conn.cursor()
try:
    c.execute('ALTER TABLE events ADD COLUMN attendance INTEGER')
    print('Attendance column added.')
except sqlite3.OperationalError:
    print('Attendance column already exists.')
conn.commit()
conn.close()
