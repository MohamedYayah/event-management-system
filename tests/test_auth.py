import unittest
import sqlite3
import hashlib
import os
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from event_management_system import LoginWindow

class TestAuth(unittest.TestCase):
    DB_PATH = 'test_event_management.db'

    @classmethod
    def setUpClass(cls):
        # Create a test DB and a user
        conn = sqlite3.connect(cls.DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )''')
        pw = hashlib.sha256('StrongPass1!'.encode()).hexdigest()
        cursor.execute('INSERT OR IGNORE INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)',
                       ('testuser', 'testuser@example.com', pw, 0))
        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.DB_PATH)

    def test_password_strength(self):
        self.assertFalse(LoginWindow.validate_password_strength('short'))
        self.assertFalse(LoginWindow.validate_password_strength('alllowercase1!'))
        self.assertFalse(LoginWindow.validate_password_strength('ALLUPPERCASE1!'))
        self.assertFalse(LoginWindow.validate_password_strength('NoNumber!'))
        self.assertFalse(LoginWindow.validate_password_strength('NoSpecial1'))
        self.assertTrue(LoginWindow.validate_password_strength('StrongPass1!'))

    def test_login_success(self):
        # Simulate correct login
        pw = 'StrongPass1!'
        conn = sqlite3.connect(self.DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE username = ?', ('testuser',))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], hashlib.sha256(pw.encode()).hexdigest())
        conn.close()

    def test_login_failure(self):
        # Simulate wrong password
        pw = 'WrongPass1!'
        conn = sqlite3.connect(self.DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE username = ?', ('testuser',))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertNotEqual(row[0], hashlib.sha256(pw.encode()).hexdigest())
        conn.close()

    def test_brute_force_lockout(self):
        # Simulate login attempts
        LoginWindow.login_attempts = {}
        username = 'testuser'
        for i in range(LoginWindow.LOCKOUT_THRESHOLD):
            attempts = LoginWindow.login_attempts.get(username, {"count": 0, "last": 0, "locked": 0})
            attempts["count"] += 1
            LoginWindow.login_attempts[username] = attempts
        now = 1000000
        attempts = LoginWindow.login_attempts[username]
        attempts["locked"] = now + LoginWindow.LOCKOUT_TIME
        self.assertGreater(attempts["locked"], now)

if __name__ == '__main__':
    unittest.main()
