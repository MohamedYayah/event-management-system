import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta
import calendar
import re
import hashlib
import ml_utils
import face_utils

class LoginWindow:
    @staticmethod
    def validate_password_strength(password):
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):
            return False
        if not re.search(r"[a-z]", password):
            return False
        if not re.search(r"\d", password):
            return False
        if not re.search(r"[^A-Za-z0-9]", password):
            return False
        return True

    def __init__(self, master, on_success):
        self.master = master
        self.on_success = on_success
        self.master.title("Login")
        self.master.geometry("300x200")
        self.frame = ttk.Frame(master)
        self.frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        ttk.Label(self.frame, text="Username:").pack(pady=5)
        self.username_entry = ttk.Entry(self.frame)
        self.username_entry.pack(pady=5)

        ttk.Label(self.frame, text="Password:").pack(pady=5)
        self.password_entry = ttk.Entry(self.frame, show="*")
        self.password_entry.pack(pady=5)

        self.login_btn = ttk.Button(self.frame, text="Login", command=self.login)
        self.login_btn.pack(pady=5)
        self.register_btn = ttk.Button(self.frame, text="Register", command=self.open_register)
        self.register_btn.pack(pady=5)

        self.forgot_btn = ttk.Button(self.frame, text="Forgot Password?", command=self.forgot_password)
        self.forgot_btn.pack(pady=5)

    # Track failed login attempts per session
    login_attempts = {}
    LOCKOUT_THRESHOLD = 5
    LOCKOUT_TIME = 300  # seconds

    def toggle_password_visibility(self):
        if self.show_pw_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    def login(self):
        import time
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Login Error", "Please enter username and password.")
            return
        # Brute-force lockout protection
        now = time.time()
        attempts = LoginWindow.login_attempts.get(username, {"count": 0, "last": 0, "locked": 0})
        if attempts.get("locked", 0) > now:
            mins = int((attempts["locked"]-now)//60)+1
            messagebox.showerror("Locked Out", f"Too many failed attempts. Try again in {mins} minute(s).")
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and row[0] == hashlib.sha256(password.encode()).hexdigest():
            conn.close()
            LoginWindow.login_attempts[username] = {"count": 0, "last": now, "locked": 0}
            self.master.destroy()
            self.on_success(username)
        else:
            conn.close()
            attempts["count"] += 1
            attempts["last"] = now
            # Lockout after threshold
            if attempts["count"] >= LoginWindow.LOCKOUT_THRESHOLD:
                attempts["locked"] = now + LoginWindow.LOCKOUT_TIME
                attempts["count"] = 0
                messagebox.showerror("Locked Out", f"Too many failed attempts. Account locked for {LoginWindow.LOCKOUT_TIME//60} minutes.")
            else:
                messagebox.showerror("Login Error", f"Invalid username or password. Attempts left: {LoginWindow.LOCKOUT_THRESHOLD - attempts['count']}")
            LoginWindow.login_attempts[username] = attempts

    def open_register(self):
        RegisterWindow(self.master)

    def forgot_password(self):
        username = simpledialog.askstring("Forgot Password", "Enter your username:")
        if not username:
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            messagebox.showerror("Reset Error", "Username not found.")
            return
        new_pw = simpledialog.askstring("Reset Password", "Enter new password:", show='*')
        if not new_pw:
            conn.close()
            return
        confirm_pw = simpledialog.askstring("Reset Password", "Confirm new password:", show='*')
        if new_pw != confirm_pw:
            conn.close()
            messagebox.showerror("Reset Error", "Passwords do not match.")
            return
        hashed = hashlib.sha256(new_pw.encode()).hexdigest()
        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, username))
        conn.commit()
        conn.close()
        messagebox.showinfo("Reset Password", "Password reset successful!")

class RegisterWindow:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Register")
        self.top.geometry("300x320")
        self.frame = ttk.Frame(self.top)
        self.frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        ttk.Label(self.frame, text="Username:").pack(pady=5)
        self.username_entry = ttk.Entry(self.frame)
        self.username_entry.pack(pady=5)

        ttk.Label(self.frame, text="Password:").pack(pady=5)
        self.password_entry = ttk.Entry(self.frame, show="*")
        self.password_entry.pack(pady=5)

        ttk.Label(self.frame, text="Confirm Password:").pack(pady=5)
        self.confirm_entry = ttk.Entry(self.frame, show="*")
        self.confirm_entry.pack(pady=5)

        self.register_btn = tk.Button(self.frame, text="Register", command=self.register, width=20)
        self.register_btn.pack(pady=10, fill=tk.X, expand=True)

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm = self.confirm_entry.get().strip()
        if not username or not password or not confirm:
            messagebox.showerror("Register Error", "Please fill all fields.")
            return
        if password != confirm:
            messagebox.showerror("Register Error", "Passwords do not match.")
            return
        # Password strength validation
        if not LoginWindow.validate_password_strength(password):
            messagebox.showerror("Weak Password", "Password must be at least 8 characters, include uppercase, lowercase, number, and special character.")
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            messagebox.showerror("Register Error", "Username already exists.")
            conn.close()
            return
        hashed = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        conn.close()
        messagebox.showinfo("Register", "Registration successful! You can now log in.")
        self.top.destroy()


class EventManagementSystem:
    def __init__(self, root, username=None):
        print("EventManagementSystem __init__ called")  # DEBUG
        self.username = username
        self.root = root
        self.root.title("Event Management System")
        self.root.geometry("1000x600")
        self.root.resizable(True, True)

        # --- FUTURISTIC STYLE ---
        style = ttk.Style()
        style.theme_use('clam')
        # Base colors
        dark_bg = '#181a23'
        neon_blue = '#00fff7'
        neon_purple = '#8f00ff'
        neon_green = '#39ff14'
        text_fg = '#e0e0e0'
        accent = neon_blue
        # General
        style.configure('.', background=dark_bg, foreground=text_fg, font=('Segoe UI', 11))
        style.configure('TFrame', background=dark_bg)
        style.configure('TLabel', background=dark_bg, foreground=neon_blue, font=('Segoe UI', 11, 'bold'))
        style.configure('TButton', background=neon_purple, foreground='#fff', font=('Segoe UI', 11, 'bold'), borderwidth=0, focusthickness=3)
        style.map('TButton', background=[('active', neon_blue)], foreground=[('active', neon_green)])
        style.configure('TLabelframe', background=dark_bg, foreground=neon_blue, font=('Segoe UI', 11, 'bold'))
        style.configure('TLabelframe.Label', background=dark_bg, foreground=neon_green)
        style.configure('Treeview', background='#23263a', foreground=neon_green, fieldbackground=dark_bg, borderwidth=0, font=('Segoe UI', 10))
        style.map('Treeview', background=[('selected', neon_purple)])
        style.configure('TNotebook', background=dark_bg, borderwidth=0)
        style.configure('TNotebook.Tab', background=dark_bg, foreground=neon_blue, font=('Segoe UI', 11, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', neon_purple)], foreground=[('selected', neon_green)])
        # Entry widget
        style.configure('TEntry', fieldbackground='#23263a', foreground=neon_blue, borderwidth=0)
        # Scrollbar
        style.configure('Vertical.TScrollbar', background=neon_blue, troughcolor=dark_bg, borderwidth=0)
        # Highlight root background
        self.root.configure(bg=dark_bg)

        # Create and pack main notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Dashboard tab
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")

        # Calendar tab
        self.calendar_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.calendar_frame, text="Calendar")

        # Events tab
        self.events_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.events_frame, text="Events")

        # Initialize database connection
        self.init_database()

        # Setup UI components for all tabs
        self.setup_dashboard()
        self.setup_events_tab()
        self.setup_calendar()

        # Variables
        self.current_date = datetime.now()
        self.selected_event_id = None

        # Initial data loading
        self.update_calendar()
        self.load_events()
        self.update_dashboard()

    def predict_attendance(self):
        """Predict attendance for the current event using ML."""
        title = self.event_title_var.get().strip()
        date = self.event_date_var.get().strip()
        location = self.event_location_var.get().strip()
        status = self.event_status_var.get().strip()
        event_features = {
            'date': date,
            'location': location,
            'status': status
        }
        model, feature_columns = ml_utils.train_attendance_model()
        if model is None:
            self.prediction_label.config(text="Not enough data for prediction.")
            return
        prediction = ml_utils.predict_attendance(event_features, model, feature_columns)
        self.prediction_label.config(text=f"Predicted Attendance: {prediction}")

    def face_check_in_callback(self):
        """Callback for face detection attendance. Provides user feedback before and after running face detection."""
        messagebox.showinfo("Face Check-In", "Face detection will start. Please look at the camera. Press 'q' to quit.")
        try:
            face_utils.launch_face_detection()
            messagebox.showinfo("Face Check-In", "Face detection completed.")
        except Exception as e:
            messagebox.showerror("Face Check-In Error", f"An error occurred during face detection: {e}")

        # Gather current event details
        title = self.event_title_var.get().strip()
        date = self.event_date_var.get().strip()
        location = self.event_location_var.get().strip()
        status = self.event_status_var.get().strip()
        event_features = {
            'date': date,
            'location': location,
            'status': status
        }
        model, feature_columns = ml_utils.train_attendance_model()
        if model is None:
            self.prediction_label.config(text="Not enough data for prediction.")
            return
        prediction = ml_utils.predict_attendance(event_features, model, feature_columns)
        self.prediction_label.config(text=f"Predicted Attendance: {prediction}")


    def init_database(self):
        """Initialize the SQLite database and create tables if they don't exist"""
        try:
            self.conn = sqlite3.connect('event_management.db')
            self.cursor = self.conn.cursor()
            # Create users table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
            # Create events table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    date TEXT NOT NULL,
                    time TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'Upcoming'
                )
            ''')
            
            # Create attendees table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    name TEXT NOT NULL,
                    email TEXT,
                    status TEXT DEFAULT 'Invited',
                    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error initializing database: {e}")


            columns = ("id", "title", "date", "time", "location", "status")
            self.upcoming_tree = ttk.Treeview(upcoming_frame, columns=columns, show="headings", selectmode="browse", height=10)
            self.upcoming_tree.heading("id", text="ID")
            self.upcoming_tree.heading("title", text="Title")
            self.upcoming_tree.heading("date", text="Date")
            self.upcoming_tree.heading("time", text="Time")
            self.upcoming_tree.heading("location", text="Location")
            self.upcoming_tree.heading("status", text="Status")
            self.upcoming_tree.column("id", width=50, anchor=tk.CENTER)
            self.upcoming_tree.column("title", width=200, anchor=tk.W)
            self.upcoming_tree.column("date", width=100, anchor=tk.CENTER)
            self.upcoming_tree.column("time", width=100, anchor=tk.CENTER)
            self.upcoming_tree.column("location", width=150, anchor=tk.W)
            self.upcoming_tree.column("status", width=100, anchor=tk.CENTER)

            # Scrollbar
            scrollbar = ttk.Scrollbar(upcoming_frame, orient=tk.VERTICAL, command=self.upcoming_tree.yview)
            self.upcoming_tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.upcoming_tree.pack(fill=tk.BOTH, expand=True)

            # Double-click to view event details
            self.upcoming_tree.bind("<Double-1>", self.view_event_details)
            
            # Info label for user guidance
            info_label = ttk.Label(upcoming_frame, text="Double-click an event to view details.", foreground="#39ff14")
            info_label.pack(anchor=tk.W, pady=(8, 0), padx=5)

        columns = ("id", "title", "date", "time", "location", "status")
        self.dashboard_events_tree = ttk.Treeview(all_events_frame, columns=columns, show="headings", selectmode="browse", height=10)
        self.dashboard_events_tree.heading("id", text="ID")
        self.dashboard_events_tree.heading("title", text="Title")
        self.dashboard_events_tree.heading("date", text="Date")
        self.dashboard_events_tree.heading("time", text="Time")
        self.dashboard_events_tree.heading("location", text="Location")
        self.dashboard_events_tree.heading("status", text="Status")
        self.dashboard_events_tree.column("id", width=50, anchor=tk.CENTER)
        self.dashboard_events_tree.column("title", width=200, anchor=tk.W)
        self.dashboard_events_tree.column("date", width=100, anchor=tk.CENTER)
        self.dashboard_events_tree.column("time", width=100, anchor=tk.CENTER)
        self.dashboard_events_tree.column("location", width=150, anchor=tk.W)
        self.dashboard_events_tree.column("status", width=100, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(all_events_frame, orient=tk.VERTICAL, command=self.dashboard_events_tree.yview)
        self.dashboard_events_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.dashboard_events_tree.pack(fill=tk.BOTH, expand=True)

        # Double-click to view event details
        self.dashboard_events_tree.bind("<Double-1>", self._dashboard_event_double_click)

        # Search bar for events (optional, modern UX)
        search_frame = ttk.Frame(all_events_frame)
        search_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_date_var = tk.StringVar()
        self.search_location_var = tk.StringVar()
        self.search_status_var = tk.StringVar()
        self.sort_by_var = tk.StringVar(value='date')
        self.sort_order_var = tk.StringVar(value='asc')
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        date_entry = ttk.Entry(search_frame, textvariable=self.search_date_var, width=10)
        date_entry.pack(side=tk.LEFT, padx=(0, 5))
        location_entry = ttk.Entry(search_frame, textvariable=self.search_location_var, width=15)
        location_entry.pack(side=tk.LEFT, padx=(0, 5))
        status_combo = ttk.Combobox(search_frame, textvariable=self.search_status_var, values=["", "Upcoming", "In Progress", "Completed", "Cancelled"], width=12)
        status_combo.pack(side=tk.LEFT, padx=(0, 5))
        sort_by_combo = ttk.Combobox(search_frame, textvariable=self.sort_by_var, values=["date", "title", "location", "status"], width=10)
        sort_by_combo.pack(side=tk.LEFT, padx=(0, 5))
        sort_order_combo = ttk.Combobox(search_frame, textvariable=self.sort_order_var, values=["asc", "desc"], width=7)
        sort_order_combo.pack(side=tk.LEFT, padx=(0, 5))
        search_btn = ttk.Button(search_frame, text="Search", command=self.search_events)
        search_btn.pack(side=tk.LEFT)
        clear_btn = ttk.Button(search_frame, text="Clear", command=self.clear_search_fields)
        clear_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.results_count_label = ttk.Label(search_frame, text="")
        self.results_count_label.pack(side=tk.LEFT, padx=10)

    def clear_search_fields(self):
        self.search_var.set("")
        self.search_date_var.set("")
        self.search_location_var.set("")
        self.search_status_var.set("")
        self.sort_by_var.set("date")
        self.sort_order_var.set("asc")
        self.results_count_label.config(text="")
        self.load_events()

        # Info label for user guidance
        # Set up the dashboard tab with overview of upcoming events
        try:
            # --- Modern Dashboard Header ---
            header = ttk.Label(self.dashboard_frame, text="Event Management Dashboard", font=("Segoe UI", 20, "bold"), foreground="#1e90ff")
            header.pack(pady=(20, 10))
            
            # Attendee section
            attendee_section_frame = ttk.Frame(self.dashboard_frame)
            attendee_section_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Attendee buttons frame
            attendee_buttons_frame = ttk.Frame(attendee_section_frame)
            attendee_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
            
            self.add_attendee_btn = ttk.Button(attendee_buttons_frame, text="Add Attendee", command=self.add_attendee)
            self.add_attendee_btn.pack(side=tk.LEFT, padx=5, pady=5)
            self.add_attendee_btn['state'] = 'normal'
            self.edit_attendee_btn = ttk.Button(attendee_buttons_frame, text="Edit Attendee", command=self.edit_attendee)
            self.edit_attendee_btn.pack(side=tk.LEFT, padx=5, pady=5)
            self.edit_attendee_btn['state'] = 'normal'
            self.remove_attendee_btn = ttk.Button(attendee_buttons_frame, text="Remove Attendee", command=self.remove_attendee)
            self.remove_attendee_btn.pack(side=tk.LEFT, padx=5, pady=5)
            self.remove_attendee_btn['state'] = 'normal'
        except sqlite3.Error as e:
            messagebox.showerror("Calendar Error", f"Failed to load events for calendar: {e}")

    def prev_month(self):
        """Navigate to previous month"""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year-1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month-1)
        self.update_calendar()

    def next_month(self):
        """Navigate to next month"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.update_calendar()

    def go_to_today(self):
        """Navigate to today's date"""
        self.current_date = datetime.now()
        self.update_calendar()

    def load_events(self):
        """Load all events into the events tree. IMPORTANT: self.events_tree must be created in setup_events_tab before calling this method. If you refactor, ensure this order is preserved!"""
        if not hasattr(self, 'events_tree'):
            messagebox.showerror("Critical Error", "Events tree widget is missing. Please report this bug.")
            return
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        try:
            self.cursor.execute("SELECT id, title, date, time, location, status FROM events ORDER BY date, time")
            events = self.cursor.fetchall()
            for event in events:
                self.events_tree.insert('', tk.END, values=event)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to load events: {e}")

    def update_dashboard(self):
        """Update dashboard statistics and upcoming events"""
        try:
            today = datetime.now().date().isoformat()
            for item in self.upcoming_tree.get_children():
                self.upcoming_tree.delete(item)
            self.cursor.execute("SELECT id, title, date, time, location, status FROM events WHERE date >= ? ORDER BY date, time LIMIT 10", (today,))
            upcoming_events = self.cursor.fetchall()
            for event in upcoming_events:
                self.upcoming_tree.insert('', tk.END, values=event)
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE date > ? AND status = 'Upcoming'", (today,))
            upcoming_count = self.cursor.fetchone()[0]
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE date = ? AND status != 'Cancelled'", (today,))
            today_count = self.cursor.fetchone()[0]
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'Completed'")
            completed_count = self.cursor.fetchone()[0]
            self.stats_upcoming.config(text=f"Upcoming Events: {upcoming_count}")
            self.stats_today.config(text=f"Today's Events: {today_count}")
            self.stats_completed.config(text=f"Completed Events: {completed_count}")
            self.load_dashboard_events()
        except sqlite3.Error as e:
            messagebox.showerror("Dashboard Error", f"Failed to update dashboard: {e}")

    def search_events(self):
        """Search events based on search text"""
        search_text = self.search_var.get().strip()
        if not search_text:
            self.load_events()
            return
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        try:
            search_pattern = f"%{search_text}%"
            self.cursor.execute("""
                SELECT id, title, date, time, location, status FROM events 
                WHERE title LIKE ? OR description LIKE ? OR location LIKE ?
                ORDER BY date, time
            """, (search_pattern, search_pattern, search_pattern))
            events = self.cursor.fetchall()
            for event in events:
                self.events_tree.insert('', tk.END, values=event)
            messagebox.showinfo("Search Results", f"Found {len(events)} events matching '{search_text}'")
        except sqlite3.Error as e:
            messagebox.showerror("Search Error", f"Failed to search events: {e}")

    def view_event_details_by_id(self, event_id):
        """View event details by ID and switch to events tab"""
        try:
            self.notebook.select(2)  # Events tab is at index 2
            for item in self.events_tree.get_children():
                if self.events_tree.item(item, 'values')[0] == str(event_id):
                    self.events_tree.selection_set(item)
                    self.events_tree.focus(item)
                    self.events_tree.see(item)
                    self.on_event_select(None)
                    break
        except Exception as e:
            messagebox.showerror("Event View Error", f"Failed to view event details: {e}")

    def next_month(self):
        """Navigate to next month"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.update_calendar()

    def go_to_today(self):
        """Navigate to today's date"""
        self.current_date = datetime.now()
        self.update_calendar()

    def update_dashboard(self):
        """Update dashboard statistics and upcoming events"""
        try:
            today = datetime.now().date().isoformat()
            for item in self.upcoming_tree.get_children():
                self.upcoming_tree.delete(item)
            self.cursor.execute("SELECT id, title, date, time, location, status FROM events WHERE date >= ? ORDER BY date, time LIMIT 10", (today,))
            upcoming_events = self.cursor.fetchall()
            for event in upcoming_events:
                self.upcoming_tree.insert('', tk.END, values=event)
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE date > ? AND status = 'Upcoming'", (today,))
            upcoming_count = self.cursor.fetchone()[0]
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE date = ? AND status != 'Cancelled'", (today,))
            today_count = self.cursor.fetchone()[0]
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'Completed'")
            completed_count = self.cursor.fetchone()[0]
            self.stats_upcoming.config(text=f"Upcoming Events: {upcoming_count}")
            self.stats_today.config(text=f"Today's Events: {today_count}")
            self.stats_completed.config(text=f"Completed Events: {completed_count}")
        except sqlite3.Error as e:
            messagebox.showerror("Dashboard Error", f"Failed to update dashboard: {e}")

    def search_events(self):
        """Search events based on search text"""
        search_text = self.search_var.get().strip()
        if not search_text:
            self.load_events()
            return
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        try:
            search_pattern = f"%{search_text}%"
            self.cursor.execute("""
                SELECT id, title, date, time, location, status FROM events 
                WHERE title LIKE ? OR description LIKE ? OR location LIKE ?
                ORDER BY date, time
            """, (search_pattern, search_pattern, search_pattern))
            events = self.cursor.fetchall()
            for event in events:
                self.events_tree.insert('', tk.END, values=event)
            messagebox.showinfo("Search Results", f"Found {len(events)} events matching '{search_text}'")
        except sqlite3.Error as e:
            messagebox.showerror("Search Error", f"Failed to search events: {e}")

    def view_event_details(self, event=None):
        """View details of the selected event from the dashboard"""
        selected_item = self.upcoming_tree.selection()
        if not selected_item:
            messagebox.showinfo("Selection", "Please select an event to view")
            return
        event_id = self.upcoming_tree.item(selected_item[0], 'values')[0]
        self.view_event_details_by_id(event_id)

    def view_event_details_by_id(self, event_id):
        """View event details by ID and switch to events tab"""
        try:
            self.notebook.select(2)  # Events tab is at index 2
            for item in self.events_tree.get_children():
                if self.events_tree.item(item, 'values')[0] == str(event_id):
                    self.events_tree.selection_set(item)
                    self.events_tree.focus(item)
                    self.events_tree.see(item)
                    self.on_event_select(None)
                    break
        except Exception as e:
            messagebox.showerror("Event View Error", f"Failed to view event details: {e}")

def on_event_select(self, event=None):
    """Handle event selection in the events tree"""
    selected_item = self.events_tree.selection()
    if not selected_item:
        return
    event_id = self.events_tree.item(selected_item[0], 'values')[0]
    self.selected_event_id = event_id
    try:
        self.cursor.execute("SELECT title, description, date, time, location, status FROM events WHERE id = ?", (event_id,))
        event = self.cursor.fetchone()
        if event:
            title, description, date, time, location, status = event
            self.event_title_var.set(title)
            self.event_date_var.set(date)
            self.event_time_var.set(time if time else "")
            self.event_location_var.set(location if location else "")
            self.event_status_var.set(status)
            self.event_description_text.delete(1.0, tk.END)
            if description:
                self.event_description_text.insert(tk.END, description)
            self.load_attendees(event_id)
    except sqlite3.Error as e:
        messagebox.showerror("Event Selection Error", f"Failed to load event details: {e}")

def load_attendees(self, event_id):
    """Load attendees for the selected event"""
    for item in self.attendees_tree.get_children():
        self.attendees_tree.delete(item)
    try:
        self.cursor.execute("SELECT id, name, email, status FROM attendees WHERE event_id = ?", (event_id,))
        attendees = self.cursor.fetchall()
        for attendee in attendees:
            self.attendees_tree.insert('', tk.END, values=attendee)
    except sqlite3.Error as e:
        messagebox.showerror("Attendee Error", f"Failed to load attendees: {e}")

    def add_event(self):
        """Add a new event (reset form for new event entry)"""
        self.selected_event_id = None
        self.event_title_var.set("")
        self.event_date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.event_time_var.set("")
        self.event_location_var.set("")
        self.event_status_var.set("Upcoming")
        self.event_description_text.delete(1.0, tk.END)
        # Clear attendees list
        for item in self.attendees_tree.get_children():
            self.attendees_tree.delete(item)
        # Disable Save Event button until attendee is added
        if hasattr(self, 'save_event_btn'):
            self.save_event_btn.config(state='disabled')
        if hasattr(self, 'add_attendee_btn'):
            self.add_attendee_btn.config(state='normal')
        if hasattr(self, 'edit_attendee_btn'):
            self.edit_attendee_btn.config(state='normal')
        if hasattr(self, 'remove_attendee_btn'):
            self.remove_attendee_btn.config(state='normal')
        self.attendees_tree.bind('<<TreeviewSelect>>', lambda e: self.update_save_event_button_state())

def edit_event(self):
    """Edit the selected event: populate form with event data for editing"""
    selected_item = self.events_tree.selection()
    if not selected_item:
        messagebox.showinfo("Edit Event", "Please select an event to edit.")
        return
    event_id = self.events_tree.item(selected_item[0], 'values')[0]
    self.selected_event_id = event_id
    try:
        self.cursor.execute("SELECT title, description, date, time, location, status FROM events WHERE id = ?", (event_id,))
        event = self.cursor.fetchone()
        if event:
            title, description, date, time, location, status = event
            self.event_title_var.set(title)
            self.event_date_var.set(date)
            self.event_time_var.set(time if time else "")
            self.event_location_var.set(location if location else "")
            self.event_status_var.set(status)
            self.event_description_text.delete(1.0, tk.END)
            if description:
                self.event_description_text.insert(tk.END, description)
            self.load_attendees(event_id)
            # Enable/disable Save Event button based on attendees
            self.update_save_event_button_state()
            if hasattr(self, 'add_attendee_btn'):
                self.add_attendee_btn.config(state='normal')
            if hasattr(self, 'edit_attendee_btn'):
                self.edit_attendee_btn.config(state='normal')
            if hasattr(self, 'remove_attendee_btn'):
                self.remove_attendee_btn.config(state='normal')
    except sqlite3.Error as e:
        messagebox.showerror("Edit Event Error", f"Failed to load event: {e}")

    def update_save_event_button_state(self):
        """Enable Save Event button only if at least one attendee exists"""
        if hasattr(self, 'save_event_btn'):
            if len(self.attendees_tree.get_children()) > 0:
                self.save_event_btn.config(state='normal')
            else:
                self.save_event_btn.config(state='disabled')

    def delete_event(self):
        """Delete the selected event and its attendees from the database"""
        selected_item = self.events_tree.selection()
        if not selected_item:
            messagebox.showinfo("Delete Event", "Please select an event to delete.")
            return
        event_id = self.events_tree.item(selected_item[0], 'values')[0]
        confirm = messagebox.askyesno("Delete Event", "Are you sure you want to delete this event?")
        if not confirm:
            return
        try:
            self.cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            self.conn.commit()
            self.load_events()
            self.update_dashboard()
            self.update_calendar()
            messagebox.showinfo("Delete Event", "Event deleted successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Delete Event Error", f"Failed to delete event: {e}")

    def add_attendee(self):
        """Add a new attendee to the selected event (or event being created/edited)"""
        print("Add Attendee button clicked", id(self))  # DEBUG
        name = simpledialog.askstring("Add Attendee", "Enter attendee name:")
        if not name:
            return
        email = simpledialog.askstring("Add Attendee", "Enter attendee email (optional):")
        status = simpledialog.askstring("Add Attendee", "Enter status (Invited/Confirmed/Declined):", initialvalue="Invited")
        if not status:
            status = "Invited"
        self.attendees_tree.insert('', tk.END, values=("", name, email, status))
        self.update_save_event_button_state()

    def edit_attendee(self):
        print("Edit Attendee button clicked", id(self))  # DEBUG
        """Edit the selected attendee in the attendee list"""
        selected_item = self.attendees_tree.selection()
        if not selected_item:
            messagebox.showinfo("Edit Attendee", "Please select an attendee to edit.")
            return
        values = self.attendees_tree.item(selected_item[0], 'values')
        name = simpledialog.askstring("Edit Attendee", "Edit attendee name:", initialvalue=values[1])
        if not name:
            return
        email = simpledialog.askstring("Edit Attendee", "Edit attendee email:", initialvalue=values[2])
        status = simpledialog.askstring("Edit Attendee", "Edit status (Invited/Confirmed/Declined):", initialvalue=values[3])
        if not status:
            status = "Invited"
        self.attendees_tree.item(selected_item[0], values=(values[0], name, email, status))

    def remove_attendee(self):
        """Remove the selected attendee from the attendee list"""
        selected_item = self.attendees_tree.selection()
        if not selected_item:
            messagebox.showinfo("Remove Attendee", "Please select an attendee to remove.")
            return
        self.attendees_tree.delete(selected_item[0])
        self.update_save_event_button_state()

    def save_event(self):
        """Save a new or edited event and its attendees to the database"""
        # Validate event form
        if not self.validate_event_form():
            messagebox.showerror("Validation Error", "Event form is invalid. Please check all required fields.")
            return
        # Require at least one attendee
        if len(self.attendees_tree.get_children()) == 0:
            messagebox.showerror("Validation Error", "You must add at least one attendee to save the event.")
            return
        title = self.event_title_var.get().strip()
        date = self.event_date_var.get().strip()
        time_val = self.event_time_var.get().strip()
        location = self.event_location_var.get().strip()
        status = self.event_status_var.get().strip()
        description = self.event_description_text.get(1.0, tk.END).strip()
        try:
            if self.selected_event_id:
                # Update existing event
                self.cursor.execute("""
                    UPDATE events SET title=?, description=?, date=?, time=?, location=?, status=? WHERE id=?
                """, (title, description, date, time_val, location, status, self.selected_event_id))
                event_id = self.selected_event_id
            else:
                # Insert new event
                self.cursor.execute("""
                    INSERT INTO events (title, description, date, time, location, status) VALUES (?, ?, ?, ?, ?, ?)
                """, (title, description, date, time_val, location, status))
                event_id = self.cursor.lastrowid
            # Save attendees
            self.cursor.execute("DELETE FROM attendees WHERE event_id = ?", (event_id,))
            for item in self.attendees_tree.get_children():
                values = self.attendees_tree.item(item, 'values')
                if len(values) == 4:
                    _id, name, email, att_status = values
                    self.cursor.execute(
                        "INSERT INTO attendees (event_id, name, email, status) VALUES (?, ?, ?, ?)",
                        (event_id, name, email, att_status)
                    )
            self.conn.commit()
            self.load_events()
            self.update_dashboard()
            self.update_calendar()
            messagebox.showinfo("Save Event", "Event saved successfully.")
            self.selected_event_id = None
            self.add_event()
        except sqlite3.Error as e:
            messagebox.showerror("Save Event Error", f"Failed to save event: {e}")

def init_database():
    import sqlite3
    conn = sqlite3.connect('event_management.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            time TEXT,
            location TEXT,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            name TEXT,
            email TEXT,
            status TEXT,
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    def start_app(username):
        root = tk.Tk()
        app = EventManagementSystem(root, username=username)
        root.mainloop()

    init_database()
    login_root = tk.Tk()
    LoginWindow(login_root, on_success=start_app)
    login_root.mainloop()
    
    def update_calendar(self):
        """Update the calendar with the current month's days and events"""
        # Clear existing day frames
        for row in self.day_frames:
            for frame, day_label, events_frame in row:
                day_label.config(text="")
                for widget in events_frame.winfo_children():
                    widget.destroy()
        
        # Get current month's calendar
        year = self.current_date.year
        month = self.current_date.month
        cal = calendar.monthcalendar(year, month)
        
        # Update month/year label
        month_name = calendar.month_name[month]
        self.month_year_label.config(text=f"{month_name} {year}")
        # Update number of days in month label
        import calendar as _calendar
        days_in_month = _calendar.monthrange(year, month)[1]
        self.days_in_month_label.config(text=f"Number of days this month: {days_in_month}")
        
        # Get events for the current month
        try:
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1}-01-01"
            else:
                end_date = f"{year}-{month+1:02d}-01"
            
            self.cursor.execute("SELECT id, title, date, time FROM events WHERE date >= ? AND date < ?", (start_date, end_date))
            month_events = self.cursor.fetchall()
            
            # Group events by date
            events_by_date = {}
            for event_id, title, date, time in month_events:
                if date not in events_by_date:
                    events_by_date[date] = []
                events_by_date[date].append((event_id, title, time))
            
            # Fill in the calendar
            today = datetime.now().date()
            
            for week_idx, week in enumerate(cal):
                for day_idx, day in enumerate(week):
                    if day != 0:
                        day_frame, day_label, events_frame = self.day_frames[week_idx][day_idx]
                        
                        # Set day number
                        day_label.config(text=str(day))
                        
                        # Highlight today
                        if year == today.year and month == today.month and day == today.day:
                            day_label.config(font=("Arial", 10, "bold"), foreground="red")
                        else:
                            day_label.config(font=("Arial", 10), foreground="black")
                        
                        # Add events for this day
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        if date_str in events_by_date:
                            for idx, (event_id, title, time) in enumerate(events_by_date[date_str]):
                                if idx < 3:  # Limit to 3 events per day to avoid clutter
                                    event_label = ttk.Label(events_frame, text=f"{time} {title}", anchor=tk.W,
                                                           background="#e1f5fe", padding=2)
                                    event_label.pack(fill=tk.X, padx=2, pady=1)
                                    
                                    # Bind click event to view event details
                                    event_label.bind("<Button-1>", lambda e, eid=event_id: self.view_event_details_by_id(eid))
                                elif idx == 3:
                                    more_label = ttk.Label(events_frame, text=f"+ {len(events_by_date[date_str]) - 3} more", anchor=tk.W,
                                                         foreground="blue")
                                    more_label.pack(fill=tk.X, padx=2, pady=1)
                                    break
        except sqlite3.Error as e:
            messagebox.showerror("Calendar Error", f"Failed to load events for calendar: {e}")
    
    def prev_month(self):
        """Navigate to previous month"""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year-1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month-1)
        self.update_calendar()
    
    def next_month(self):
        """Navigate to next month"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.update_calendar()
    
    def go_to_today(self):
        """Navigate to today's date"""
        self.current_date = datetime.now()
        self.update_calendar()
    
    def load_events(self):
        """Load all events into the events tree"""
        # Clear existing items
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        
        try:
            self.cursor.execute("SELECT id, title, date, time, location, status FROM events ORDER BY date, time")
            events = self.cursor.fetchall()
            
            for event in events:
                self.events_tree.insert('', tk.END, values=event)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to load events: {e}")
    
    def update_dashboard(self):
        """Update dashboard statistics and upcoming events"""
        try:
            # Get today's date
            today = datetime.now().date().isoformat()
            
            # Clear existing items in upcoming events
            for item in self.upcoming_tree.get_children():
                self.upcoming_tree.delete(item)
            
            # Get upcoming events (from today onwards)
            self.cursor.execute("SELECT id, title, date, time, location, status FROM events WHERE date >= ? ORDER BY date, time LIMIT 10", (today,))
            upcoming_events = self.cursor.fetchall()
            
            for event in upcoming_events:
                self.upcoming_tree.insert('', tk.END, values=event)
            
            # Update statistics
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE date > ? AND status = 'Upcoming'", (today,))
            upcoming_count = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE date = ? AND status != 'Cancelled'", (today,))
            today_count = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM events WHERE status = 'Completed'")
            completed_count = self.cursor.fetchone()[0]
            
            self.stats_upcoming.config(text=f"Upcoming Events: {upcoming_count}")
            self.stats_today.config(text=f"Today's Events: {today_count}")
            self.stats_completed.config(text=f"Completed Events: {completed_count}")
            
            # Update all events table
            self.load_dashboard_events()
        except sqlite3.Error as e:
            messagebox.showerror("Dashboard Error", f"Failed to update dashboard: {e}")
    
    def search_events(self):
        """Advanced search: filter and sort events by multiple fields"""
        search_text = self.search_var.get().strip()
        date = self.search_date_var.get().strip()
        location = self.search_location_var.get().strip()
        status = self.search_status_var.get().strip()
        sort_by = self.sort_by_var.get().strip() or 'date'
        sort_order = self.sort_order_var.get().strip() or 'asc'
        query = "SELECT id, title, date, time, location, status FROM events WHERE 1=1"
        params = []
        if search_text:
            query += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
            pattern = f"%{search_text}%"
            params.extend([pattern, pattern, pattern])
        if date:
            query += " AND date = ?"
            params.append(date)
        if location:
            query += " AND location LIKE ?"
            params.append(f"%{location}%")
        if status:
            query += " AND status = ?"
            params.append(status)
        if sort_by not in ["date", "title", "location", "status"]:
            sort_by = "date"
        if sort_order not in ["asc", "desc"]:
            sort_order = "asc"
        query += f" ORDER BY {sort_by} {sort_order.upper()}"
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        try:
            self.cursor.execute(query, params)
            events = self.cursor.fetchall()
            for event in events:
                self.events_tree.insert('', tk.END, values=event)
            self.results_count_label.config(text=f"{len(events)} event{'s' if len(events)!=1 else ''} found")
        except sqlite3.Error as e:
            messagebox.showerror("Search Error", f"Failed to search events: {e}")
    
    def view_event_details(self, event=None):
        """View details of the selected event from the dashboard"""
        selected_item = self.upcoming_tree.selection()
        if not selected_item:
            messagebox.showinfo("Selection", "Please select an event to view")
            return
        
        event_id = self.upcoming_tree.item(selected_item[0], 'values')[0]
        self.view_event_details_by_id(event_id)
    
    def view_event_details_by_id(self, event_id):
        """View event details by ID and switch to events tab"""
        try:
            # Switch to events tab
            self.notebook.select(2)  # Events tab is at index 2
            
            # Find and select the event in the events tree
            for item in self.events_tree.get_children():
                if self.events_tree.item(item, 'values')[0] == str(event_id):
                    self.events_tree.selection_set(item)
                    self.events_tree.focus(item)
                    self.events_tree.see(item)
                    self.on_event_select(None)
                    break
        except Exception as e:
            messagebox.showerror("Event View Error", f"Failed to view event details: {e}")
    
    def on_event_select(self, event=None):
        """Handle event selection in the events tree"""
        selected_item = self.events_tree.selection()
        if not selected_item:
            return
        
        event_id = self.events_tree.item(selected_item[0], 'values')[0]
        self.selected_event_id = event_id
        
        try:
            # Get event details
            self.cursor.execute("SELECT title, description, date, time, location, status FROM events WHERE id = ?", (event_id,))
            event = self.cursor.fetchone()
            
            if event:
                title, description, date, time, location, status = event
                
                # Update form fields
                self.event_title_var.set(title)
                self.event_date_var.set(date)
                self.event_time_var.set(time if time else "")
                self.event_location_var.set(location if location else "")
                self.event_status_var.set(status)
                
                # Update description text
                self.event_description_text.delete(1.0, tk.END)
                if description:
                    self.event_description_text.insert(tk.END, description)
                
                # Load attendees
                self.load_attendees(event_id)
        except sqlite3.Error as e:
            messagebox.showerror("Event Selection Error", f"Failed to load event details: {e}")
    
    def load_attendees(self, event_id):
        """Load attendees for the selected event"""
        # Clear existing items
        for item in self.attendees_tree.get_children():
            self.attendees_tree.delete(item)
        
        try:
            self.cursor.execute("SELECT id, name, email, status FROM attendees WHERE event_id = ?", (event_id,))
            attendees = self.cursor.fetchall()
            
            for attendee in attendees:
                self.attendees_tree.insert('', tk.END, values=attendee)
        except sqlite3.Error as e:
            messagebox.showerror("Attendee Error", f"Failed to load attendees: {e}")
    
    def add_event(self):
        """Add a new event"""
        print("Add Event button clicked", id(self))  # DEBUG
        self.selected_event_id = None
        self.event_title_var.set("")
        self.event_date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.event_time_var.set("")
        self.event_location_var.set("")
        self.event_status_var.set("Upcoming")
        self.event_description_text.delete(1.0, tk.END)
        # Clear attendees list
        for item in self.attendees_tree.get_children():
            self.attendees_tree.delete(item)
        # Disable Save Event button until attendee is added
        if hasattr(self, 'save_event_btn'):
            self.save_event_btn.config(state='disabled')
        # Enable attendee controls
        if hasattr(self, 'add_attendee_btn'):
            self.add_attendee_btn.config(state='normal')
        if hasattr(self, 'edit_attendee_btn'):
            self.edit_attendee_btn.config(state='normal')
        if hasattr(self, 'remove_attendee_btn'):
            self.remove_attendee_btn.config(state='normal')

    def delete_event(self):
        """Delete the selected event and its attendees from the database"""
        selected_item = self.events_tree.selection()
        if not selected_item:
            messagebox.showinfo("Delete Event", "Please select an event to delete.")
            return
        event_id = self.events_tree.item(selected_item[0], 'values')[0]
        confirm = messagebox.askyesno("Delete Event", "Are you sure you want to delete this event?")
        if not confirm:
            return
        try:
            self.cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            self.conn.commit()
            self.load_events()
            self.update_dashboard()
            self.update_calendar()
            messagebox.showinfo("Delete Event", "Event deleted successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Delete Event Error", f"Failed to delete event: {e}")

    def add_attendee(self):
        """Add a new attendee to the selected event (or event being created/edited)"""
        print("Add Attendee button clicked", id(self))  # DEBUG
        name = simpledialog.askstring("Add Attendee", "Enter attendee name:")
        if not name:
            return
        email = simpledialog.askstring("Add Attendee", "Enter attendee email (optional):")
        status = simpledialog.askstring("Add Attendee", "Enter status (Invited/Confirmed/Declined):", initialvalue="Invited")
        if not status:
            status = "Invited"
        self.attendees_tree.insert('', tk.END, values=("", name, email, status))
        self.update_save_event_button_state()

    def edit_attendee(self):
        print("Edit Attendee button clicked", id(self))  # DEBUG
        """Edit the selected attendee in the attendee list"""
        selected_item = self.attendees_tree.selection()
        if not selected_item:
            messagebox.showinfo("Edit Attendee", "Please select an attendee to edit.")
            return
        values = self.attendees_tree.item(selected_item[0], 'values')
        name = simpledialog.askstring("Edit Attendee", "Edit attendee name:", initialvalue=values[1])
        if not name:
            return
        email = simpledialog.askstring("Edit Attendee", "Edit attendee email:", initialvalue=values[2])
        status = simpledialog.askstring("Edit Attendee", "Edit status (Invited/Confirmed/Declined):", initialvalue=values[3])
        if not status:
            status = "Invited"
        self.attendees_tree.item(selected_item[0], values=(values[0], name, email, status))

    def remove_attendee(self):
        """Remove the selected attendee from the attendee list"""
        selected_item = self.attendees_tree.selection()
        if not selected_item:
            messagebox.showinfo("Remove Attendee", "Please select an attendee to remove.")
            return
        self.attendees_tree.delete(selected_item[0])
        self.update_save_event_button_state()

    def save_event(self):
        """Save a new or edited event and its attendees to the database"""
        # Validate event form
        if not self.validate_event_form():
            messagebox.showerror("Validation Error", "Event form is invalid. Please check all required fields.")
            return
        # Require at least one attendee
        if len(self.attendees_tree.get_children()) == 0:
            messagebox.showerror("Validation Error", "You must add at least one attendee to save the event.")
            return
        title = self.event_title_var.get().strip()
        date = self.event_date_var.get().strip()
        
        if not title:
            messagebox.showerror("Validation Error", "Event title is required")
            return False
        
        