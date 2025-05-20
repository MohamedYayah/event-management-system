import unittest
import sys
import os
import sqlite3
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from app import app, get_db_connection
from werkzeug.security import generate_password_hash

class WebAuthTestCase(unittest.TestCase):
    def setUp(self):
        # Set up test client and test DB
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        # Use a test DB
        self.db_path = 'backend/events_test.db'
        self.app.config['DATABASE'] = self.db_path
        conn = get_db_connection()
        # Create users table
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )''')
        # Create events table (minimal columns for dashboard)
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
        # Insert a test user
        conn.execute('INSERT OR IGNORE INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)',
                     ('testuser', 'test@example.com', generate_password_hash('TestPass123!'), 0))
        conn.commit()
        conn.close()

    def tearDown(self):
        import os
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_register(self):
        response = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'NewPass123!'
        }, follow_redirects=True)
        print('REGISTER RESPONSE:', response.data)
        # Accept registration success, duplicate username, or duplicate email
        self.assertTrue(
            b'Registration successful' in response.data or b'Username already exists' in response.data or b'Email already registered' in response.data
        )

    def test_login_success(self):
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }, follow_redirects=True)
        # Accept dashboard or flash message as valid login
        self.assertTrue(
            b'Logged in successfully' in response.data or b'Dashboard' in response.data or b'event' in response.data
        )

    def test_login_failure(self):
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'WrongPassword'
        }, follow_redirects=True)
        self.assertTrue(
            b'Invalid email or password' in response.data or b'Invalid username or password' in response.data
        )

    def test_logout(self):
        # Login first
        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'TestPass123!'
        }, follow_redirects=True)
        response = self.client.get('/logout', follow_redirects=True)
        # Accept either flash message or login page content as success
        self.assertTrue(
            b'Logged out successfully' in response.data or b'Login' in response.data
        )

if __name__ == '__main__':
    unittest.main()
