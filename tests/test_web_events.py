import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from app import app, get_db_connection
from werkzeug.security import generate_password_hash

class WebEventTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.db_path = 'backend/events_test.db'
        self.app.config['DATABASE'] = self.db_path
        conn = get_db_connection()
        # Create users table
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )''')
        # Create events table
        conn.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            time TEXT,
            location TEXT,
            status TEXT,
            description TEXT,
            attendance INTEGER
        )''')
        # Create attendees table (minimal columns for event edit)
        conn.execute('''CREATE TABLE IF NOT EXISTS attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            name TEXT,
            email TEXT,
            status TEXT,
            face_landmarks TEXT
        )''')
        # Insert a test user
        conn.execute('INSERT OR IGNORE INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)',
                     ('testuser', 'test@example.com', generate_password_hash('TestPass123!'), 0))
        conn.commit()
        conn.close()
        # Login for event actions
        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'TestPass123!'
        }, follow_redirects=True)

    def tearDown(self):
        import os
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_event(self):
        response = self.client.post('/add', data={
            'title': 'Test Event',
            'date': '2025-05-14',
            'time': '10:00',
            'location': 'Conference Room',
            'status': 'Upcoming',
            'description': 'Test event description',
            'attendance': 0
        }, follow_redirects=True)
        self.assertTrue(b'Event added successfully' in response.data or b'Dashboard' in response.data)

    def test_edit_event(self):
        # Add event first
        conn = get_db_connection()
        conn.execute('INSERT INTO events (title, date, time, location, status, description, attendance) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     ('Edit Event', '2025-05-15', '12:00', 'Hall', 'Upcoming', 'Edit description', 0))
        event_id = conn.execute('SELECT id FROM events WHERE title = ?', ('Edit Event',)).fetchone()['id']
        conn.commit()
        conn.close()
        response = self.client.post(f'/edit/{event_id}', data={
            'title': 'Edited Event',
            'date': '2025-05-16',
            'time': '14:00',
            'location': 'Main Hall',
            'status': 'Completed',
            'description': 'Edited event description',
            'attendance': 100
        }, follow_redirects=True)
        self.assertTrue(b'Event updated successfully' in response.data or b'Dashboard' in response.data)

    def test_delete_event(self):
        # Add event first
        conn = get_db_connection()
        conn.execute('INSERT INTO events (title, date, time, location, status, description, attendance) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     ('Delete Event', '2025-05-17', '16:00', 'Room 1', 'Upcoming', 'Delete description', 0))
        event_id = conn.execute('SELECT id FROM events WHERE title = ?', ('Delete Event',)).fetchone()['id']
        conn.commit()
        conn.close()
        response = self.client.post(f'/delete/{event_id}', follow_redirects=True)
        self.assertTrue(b'Event deleted successfully' in response.data or b'Dashboard' in response.data)

if __name__ == '__main__':
    unittest.main()
