import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta
import calendar
import re
import hashlib

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

    login_attempts = {}
    LOCKOUT_THRESHOLD = 5
    LOCKOUT_TIME = 300  # seconds

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
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and row[0] == hashlib.sha256(password.encode()).hexdigest():
            conn.close()
            LoginWindow.login_attempts[username] = {"count": 0, "last": now, "locked": 0}
            self.on_success(username)
            self.master.destroy()
        else:
            attempts["count"] += 1
            attempts["last"] = now
            if attempts["count"] >= LoginWindow.LOCKOUT_THRESHOLD:
                attempts["locked"] = now + LoginWindow.LOCKOUT_TIME
                attempts["count"] = 0
                messagebox.showerror("Locked Out", f"Too many failed attempts. Account locked for {LoginWindow.LOCKOUT_TIME//60} minutes.")
            else:
                messagebox.showerror("Login Error", f"Invalid username or password. Attempts left: {LoginWindow.LOCKOUT_THRESHOLD - attempts['count']}")
            LoginWindow.login_attempts[username] = attempts
            conn.close()

    def open_register(self):
        RegisterWindow(self.master)

    def forgot_password(self):
        username = simpledialog.askstring("Forgot Password", "Enter your username:")
        if not username:
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
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
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed, username))
        conn.commit()
        conn.close()
        messagebox.showinfo("Reset Password", "Password reset successful!")

class RegisterWindow:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Register")
        self.top.geometry("300x380")
        self.frame = ttk.Frame(self.top)
        self.frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        ttk.Label(self.frame, text="Username:").pack(pady=5)
        self.username_entry = ttk.Entry(self.frame)
        self.username_entry.pack(pady=5)

        ttk.Label(self.frame, text="Email:").pack(pady=5)
        self.email_entry = ttk.Entry(self.frame)
        self.email_entry.pack(pady=5)

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
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm = self.confirm_entry.get().strip()
        if not username or not email or not password or not confirm:
            messagebox.showerror("Register Error", "Please fill all fields.")
            return
        if password != confirm:
            messagebox.showerror("Register Error", "Passwords do not match.")
            return
        if not LoginWindow.validate_password_strength(password):
            messagebox.showerror("Register Error", "Password must be at least 8 characters, include upper and lower case letters, a number, and a special character.")
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            messagebox.showerror("Register Error", "Username already exists.")
            conn.close()
            return
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            messagebox.showerror("Register Error", "Email already registered.")
            conn.close()
            return
        hashed = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 0)", (username, email, hashed))
        conn.commit()
        conn.close()
        messagebox.showinfo("Register", "Registration successful! You can now log in.")
        self.top.destroy()

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'utils'))
from backend.utils.face_checkin import detect_face_via_webcam, detect_motion_via_webcam, log_attendance

class DashboardWindow:
    def __init__(self, parent, username):
        self.top = tk.Toplevel(parent)
        self.top.title("Event Management Dashboard - MAIN")
        print("DEBUG: DashboardWindow shown")
        self.top.geometry("800x520")
        self.frame = ttk.Frame(self.top)
        self.frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        self.username = username

        # Welcome label
        ttk.Label(self.frame, text=f"Welcome, {username}!", font=("Arial", 16)).pack(pady=10)

        # Admin event management
        if self.username == 'admin':
            admin_event_frame = ttk.LabelFrame(self.frame, text="Event Management")
            admin_event_frame.pack(pady=8, fill=tk.X)
            self.event_table = ttk.Treeview(admin_event_frame, columns=("id", "title", "date", "time", "location"), show="headings", height=4)
            for col in ["id", "title", "date", "time", "location"]:
                self.event_table.heading(col, text=col.capitalize())
                self.event_table.column(col, width=90 if col=="id" else 120)
            self.event_table.pack(side=tk.LEFT, padx=5, pady=5)
            self.load_event_table()
            event_btns = ttk.Frame(admin_event_frame)
            event_btns.pack(side=tk.LEFT, padx=5)
            ttk.Button(event_btns, text="Add Event", command=self.add_event_dialog).pack(pady=2, fill=tk.X)
            ttk.Button(event_btns, text="Edit Selected", command=self.edit_selected_event).pack(pady=2, fill=tk.X)
            ttk.Button(event_btns, text="Delete Selected", command=self.delete_selected_event).pack(pady=2, fill=tk.X)
            # Admin user management and analytics
            admin_util_frame = ttk.LabelFrame(self.frame, text="Admin Tools")
            admin_util_frame.pack(pady=8, fill=tk.X)
            ttk.Button(admin_util_frame, text="Manage Users", command=self.open_user_management).pack(side=tk.LEFT, padx=8, pady=2)
            ttk.Button(admin_util_frame, text="Analytics", command=self.open_analytics).pack(side=tk.LEFT, padx=8, pady=2)

        event_frame = ttk.Frame(self.frame)
        event_frame.pack(pady=5)
        ttk.Label(event_frame, text="Select Event:", font=("Arial", 12)).grid(row=0, column=0, padx=5)
        self.event_var = tk.StringVar()
        self.event_combo = ttk.Combobox(event_frame, textvariable=self.event_var, state="readonly", width=40)
        self.event_combo.grid(row=0, column=1, padx=5)
        self.event_combo.bind("<<ComboboxSelected>>", self.update_attendance_history)
        self.events = self.fetch_events()
        self.event_combo['values'] = [f"{e[1]} ({e[2]} {e[3]})" for e in self.events]
        if self.events:
            self.event_combo.current(0)
        
        # Check-in method label
        ttk.Label(self.frame, text="Select your check-in method:", font=("Arial", 12)).pack(pady=10)
        btn_frame = ttk.Frame(self.frame, borderwidth=2, relief="solid")
        btn_frame.pack(pady=5)
        btn_frame.tkraise()
        self.face_checkin_btn = ttk.Button(btn_frame, text="Face Check-In", command=lambda: self.handle_checkin('face'))
        self.face_checkin_btn.pack(side=tk.LEFT, padx=10)
        self.motion_checkin_btn = ttk.Button(btn_frame, text="Motion Check-In", command=lambda: self.handle_checkin('motion'))
        self.motion_checkin_btn.pack(side=tk.LEFT, padx=10)
        self.add_attendee_btn = ttk.Button(btn_frame, text="Add Attendee", command=self.add_attendee_dialog)
        self.add_attendee_btn.pack(side=tk.LEFT, padx=10)
        print("DEBUG: Add Attendee button packed and visible")
        # Tooltip for Add Attendee
        def show_tooltip(event):
            x, y, cx, cy = self.add_attendee_btn.bbox("insert")
            x += self.add_attendee_btn.winfo_rootx() + 25
            y += self.add_attendee_btn.winfo_rooty() + 20
            self.attendee_tip = tk.Toplevel(self.add_attendee_btn)
            self.attendee_tip.wm_overrideredirect(True)
            self.attendee_tip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.attendee_tip, text="Add a new attendee to the selected event", background="#ffffe0", relief='solid', borderwidth=1, font=("Arial", 10))
            label.pack()
        def hide_tooltip(event):
            if hasattr(self, 'attendee_tip'):
                self.attendee_tip.destroy()
        self.add_attendee_btn.bind("<Enter>", show_tooltip)
        self.add_attendee_btn.bind("<Leave>", hide_tooltip)

        # Attendance history label
        ttk.Label(self.frame, text="Attendance History:", font=("Arial", 12)).pack(pady=10)
        filter_frame = ttk.Frame(self.frame)
        filter_frame.pack(pady=2)
        ttk.Label(filter_frame, text="Filter by User:").grid(row=0, column=0, padx=2)
        self.filter_user_var = tk.StringVar()
        self.filter_user_entry = ttk.Entry(filter_frame, textvariable=self.filter_user_var, width=12)
        self.filter_user_entry.grid(row=0, column=1, padx=2)
        ttk.Label(filter_frame, text="Status:").grid(row=0, column=2, padx=2)
        self.filter_status_var = tk.StringVar()
        self.filter_status_entry = ttk.Entry(filter_frame, textvariable=self.filter_status_var, width=12)
        self.filter_status_entry.grid(row=0, column=3, padx=2)
        self.filter_btn = ttk.Button(filter_frame, text="Apply", command=self.update_attendance_history)
        self.filter_btn.grid(row=0, column=4, padx=2)
        self.clear_filter_btn = ttk.Button(filter_frame, text="Clear", command=self.clear_filters)
        self.clear_filter_btn.grid(row=0, column=5, padx=2)
        
        self.attendance_tree = ttk.Treeview(self.frame, columns=("name", "status", "role", "timestamp"), show="headings", height=8)
        self.attendance_tree.heading("name", text="Name")
        self.attendance_tree.heading("status", text="Status")
        self.attendance_tree.heading("role", text="Role")
        self.attendance_tree.heading("timestamp", text="Timestamp")
        self.attendance_tree.column("name", width=120)
        self.attendance_tree.column("status", width=120)
        self.attendance_tree.column("role", width=80)
        self.attendance_tree.column("timestamp", width=180)
        self.attendance_tree.pack(pady=5)

        attendee_btns_frame = ttk.Frame(self.frame)
        attendee_btns_frame.pack(pady=2)
        self.edit_attendee_btn = ttk.Button(attendee_btns_frame, text="Edit Attendee", command=self.edit_attendee)
        self.edit_attendee_btn.pack(side=tk.LEFT, padx=4)
        self.delete_attendee_btn = ttk.Button(attendee_btns_frame, text="Delete Attendee", command=self.delete_attendee)
        self.delete_attendee_btn.pack(side=tk.LEFT, padx=4)

        btns_frame = ttk.Frame(self.frame)
        btns_frame.pack(pady=4)
        self.export_btn = ttk.Button(btns_frame, text="Export to CSV", command=self.export_attendance_csv)
        self.export_btn.grid(row=0, column=0, padx=4)
        if self.username == 'admin':
            self.delete_btn = ttk.Button(btns_frame, text="Delete Selected Record", command=self.delete_selected_record)
            self.delete_btn.grid(row=0, column=1, padx=4)

        self.logout_btn = ttk.Button(self.frame, text="Logout", command=self.logout)
        self.logout_btn.pack(pady=10)

        self.update_attendance_history()

    def fetch_events(self):
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, date, time, location FROM events ORDER BY date DESC, time DESC")
        events = cursor.fetchall()
        conn.close()
        return events

    def load_event_table(self):
        for row in getattr(self, 'event_table', []).get_children():
            self.event_table.delete(row)
        events = self.fetch_events()
        for e in events:
            self.event_table.insert('', 'end', values=(e[0], e[1], e[2], e[3], e[4]))

    def add_event_dialog(self):
        from tkinter import simpledialog
        title = simpledialog.askstring("Add Event", "Title:")
        if not title:
            return
        date = simpledialog.askstring("Add Event", "Date (YYYY-MM-DD):")
        time = simpledialog.askstring("Add Event", "Time (HH:MM):")
        location = simpledialog.askstring("Add Event", "Location:")
        if not date or not time or not location:
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO events (title, date, time, location, status, description, attendance) VALUES (?, ?, ?, ?, '', '', 0)", (title, date, time, location))
        conn.commit()
        conn.close()
        self.events = self.fetch_events()
        self.event_combo['values'] = [f"{e[1]} ({e[2]} {e[3]})" for e in self.events]
        self.load_event_table()

    def edit_selected_event(self):
        from tkinter import simpledialog
        selected = self.event_table.selection()
        if not selected:
            messagebox.showwarning("Edit Event", "No event selected.")
            return
        item = self.event_table.item(selected[0])['values']
        event_id, title, date, time, location = item
        new_title = simpledialog.askstring("Edit Event", "Title:", initialvalue=title)
        new_date = simpledialog.askstring("Edit Event", "Date (YYYY-MM-DD):", initialvalue=date)
        new_time = simpledialog.askstring("Edit Event", "Time (HH:MM):", initialvalue=time)
        new_location = simpledialog.askstring("Edit Event", "Location:", initialvalue=location)
        if not new_title or not new_date or not new_time or not new_location:
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE events SET title=?, date=?, time=?, location=? WHERE id=?", (new_title, new_date, new_time, new_location, event_id))
        conn.commit()
        conn.close()
        self.events = self.fetch_events()
        self.event_combo['values'] = [f"{e[1]} ({e[2]} {e[3]})" for e in self.events]
        self.load_event_table()

    def delete_selected_event(self):
        selected = self.event_table.selection()
        if not selected:
            messagebox.showwarning("Delete Event", "No event selected.")
            return
        item = self.event_table.item(selected[0])['values']
        event_id = item[0]
        confirm = messagebox.askyesno("Delete Event", "Are you sure you want to delete this event?")
        if not confirm:
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.commit()
        conn.close()
        self.events = self.fetch_events()
        self.event_combo['values'] = [f"{e[1]} ({e[2]} {e[3]})" for e in self.events]
        self.load_event_table()

    def get_selected_event_id(self):
        idx = self.event_combo.current()
        if idx == -1 or not self.events:
            return None
        return self.events[idx][0]

    def handle_checkin(self, method):
        event_id = self.get_selected_event_id()
        if not event_id:
            messagebox.showwarning("Check-In", "Please select an event first.")
            return
        if method == 'face':
            result = detect_face_via_webcam()
        else:
            result = detect_motion_via_webcam()
        if result:
            log_attendance(self.username, method, event_id)
            messagebox.showinfo("Check-In", f"{method.capitalize()} detected! Check-in successful.")
            self.update_attendance_history()
        else:
            messagebox.showwarning("Check-In", f"No {method} detected. Check-in failed.")

    def update_attendance_history(self, event=None):
        event_id = self.get_selected_event_id()
        for row in self.attendance_tree.get_children():
            self.attendance_tree.delete(row)
        if not event_id:
            return
        user_filter = self.filter_user_var.get().strip()
        status_filter = self.filter_status_var.get().strip()
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        query = "SELECT name, status, role, timestamp, ROWID FROM attendees WHERE event_id = ?"
        params = [event_id]
        if user_filter:
            query += " AND name LIKE ?"
            params.append(f"%{user_filter}%")
        if status_filter:
            query += " AND status LIKE ?"
            params.append(f"%{status_filter}%")
        query += " ORDER BY ROWID DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            self.attendance_tree.insert('', 'end', values=(row[0], row[1], row[2], row[3]), iid=row[4])
        conn.close()

    def clear_filters(self):
        self.filter_user_var.set("")
        self.filter_status_var.set("")
        self.update_attendance_history()

    def export_attendance_csv(self):
        import csv
        from tkinter import filedialog
        event_id = self.get_selected_event_id()
        if not event_id:
            messagebox.showwarning("Export", "Please select an event first.")
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, status, role, timestamp FROM attendees WHERE event_id = ? ORDER BY ROWID DESC", (event_id,))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            messagebox.showinfo("Export", "No attendance data to export.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Status", "Role", "Timestamp"])
            for row in rows:
                writer.writerow(row)
        messagebox.showinfo("Export", f"Attendance exported to {file_path}")

    def delete_selected_record(self):
        selected = self.attendance_tree.selection()
        if not selected:
            messagebox.showwarning("Delete", "No record selected.")
            return
        record_id = selected[0]
        confirm = messagebox.askyesno("Delete", "Are you sure you want to delete the selected record?")
        if not confirm:
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM attendees WHERE ROWID = ?", (record_id,))
        conn.commit()
        conn.close()
        self.update_attendance_history()

    def open_user_management(self):
        win = tk.Toplevel(self.top)
        win.title("User Management")
        win.geometry("500x400")
        tree = ttk.Treeview(win, columns=("id", "username", "email", "is_admin"), show="headings", height=12)
        for col in ["id", "username", "email", "is_admin"]:
            tree.heading(col, text=col.capitalize())
            tree.column(col, width=100)
        tree.pack(pady=10)
        def load_users():
            for row in tree.get_children():
                tree.delete(row)
            conn = sqlite3.connect('event_management.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, is_admin FROM users")
            for row in cursor.fetchall():
                tree.insert('', 'end', values=row)
            conn.close()
        load_users()
        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=4)
        def add_user():
            from tkinter import simpledialog
            username = simpledialog.askstring("Add User", "Username:")
            email = simpledialog.askstring("Add User", "Email:")
            password = simpledialog.askstring("Add User", "Password:")
            is_admin = simpledialog.askinteger("Add User", "Is Admin? (1=Yes, 0=No):", initialvalue=0)
            if not username or not email or not password:
                return
            hashed = hashlib.sha256(password.encode()).hexdigest()
            conn = sqlite3.connect('event_management.db')
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)", (username, email, hashed, is_admin or 0))
                conn.commit()
            except sqlite3.IntegrityError:
                messagebox.showerror("Add User", "Username or email already exists.")
            conn.close()
            load_users()
        def delete_user():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Delete User", "No user selected.")
                return
            user_id = tree.item(selected[0])['values'][0]
            confirm = messagebox.askyesno("Delete User", "Are you sure you want to delete this user?")
            if not confirm:
                return
            conn = sqlite3.connect('event_management.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            conn.close()
            load_users()
        ttk.Button(btn_frame, text="Add User", command=add_user).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Delete Selected", command=delete_user).pack(side=tk.LEFT, padx=6)

    def open_analytics(self):
        win = tk.Toplevel(self.top)
        win.title("Analytics")
        win.geometry("700x500")
        tab = ttk.Notebook(win)
        tab.pack(fill=tk.BOTH, expand=True)
        # Event summary tab
        event_tab = ttk.Frame(tab)
        tab.add(event_tab, text="Event Summary")
        tree = ttk.Treeview(event_tab, columns=("Event", "Total", "Face", "Motion"), show="headings", height=12)
        for col in ["Event", "Total", "Face", "Motion"]:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(pady=10)
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM events")
        events = cursor.fetchall()
        for eid, title in events:
            cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status LIKE 'checked_in_face%' THEN 1 ELSE 0 END), SUM(CASE WHEN status LIKE 'checked_in_motion%' THEN 1 ELSE 0 END) FROM attendees WHERE event_id=?", (eid,))
            total, face, motion = cursor.fetchone()
            tree.insert('', 'end', values=(title, total or 0, face or 0, motion or 0))
        # Export
        def export_event_summary():
            import csv
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            if not file_path:
                return
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Event", "Total", "Face", "Motion"])
                for row in tree.get_children():
                    writer.writerow(tree.item(row)['values'])
            messagebox.showinfo("Export", f"Event summary exported to {file_path}")
        ttk.Button(event_tab, text="Export to CSV", command=export_event_summary).pack(pady=4)
        # User attendance tab
        user_tab = ttk.Frame(tab)
        tab.add(user_tab, text="User Attendance Rates")
        user_tree = ttk.Treeview(user_tab, columns=("User", "Total Events", "Attendance Count", "Attendance Rate"), show="headings", height=12)
        for col in ["User", "Total Events", "Attendance Count", "Attendance Rate"]:
            user_tree.heading(col, text=col)
            user_tree.column(col, width=150)
        user_tree.pack(pady=10)
        cursor.execute("SELECT username FROM users")
        users = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM events")
        total_events = cursor.fetchone()[0] or 1
        for (uname,) in users:
            cursor.execute("SELECT COUNT(DISTINCT event_id) FROM attendees WHERE name=?", (uname,))
            attended = cursor.fetchone()[0] or 0
            rate = f"{100*attended/total_events:.1f}%"
            user_tree.insert('', 'end', values=(uname, total_events, attended, rate))
        def export_user_attendance():
            import csv
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            if not file_path:
                return
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["User", "Total Events", "Attendance Count", "Attendance Rate"])
                for row in user_tree.get_children():
                    writer.writerow(user_tree.item(row)['values'])
            messagebox.showinfo("Export", f"User attendance exported to {file_path}")
        ttk.Button(user_tab, text="Export to CSV", command=export_user_attendance).pack(pady=4)

    def add_attendee_dialog(self):
        from tkinter import simpledialog
        event_id = self.get_selected_event_id()
        if not event_id:
            messagebox.showwarning("Add Attendee", "Please select an event first.")
            return
        name = simpledialog.askstring("Add Attendee", "Attendee Name:")
        email = simpledialog.askstring("Add Attendee", "Attendee Email:")
        role = simpledialog.askstring("Add Attendee", "Role (e.g., attendee, speaker):", initialvalue="attendee")
        if not name or not email or not role:
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO attendees (event_id, name, email, status, role, previous_attendance_rate) VALUES (?, ?, ?, ?, ?, ?)", (event_id, name, email, 'registered', role, 0.0))
        conn.commit()
        conn.close()
        self.update_attendance_history()
        messagebox.showinfo("Add Attendee", f"Attendee '{name}' added to event.")

    def edit_attendee(self):
        from tkinter import simpledialog
        selected = self.attendance_tree.selection()
        if not selected:
            messagebox.showwarning("Edit Attendee", "No attendee selected.")
            return
        iid = selected[0]
        values = self.attendance_tree.item(iid)['values']
        name, status, role, timestamp = values
        new_name = simpledialog.askstring("Edit Attendee", "Name:", initialvalue=name)
        new_role = simpledialog.askstring("Edit Attendee", "Role:", initialvalue=role)
        if not new_name or not new_role:
            return
        # Email is not shown in table, fetch from DB
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM attendees WHERE ROWID=?", (iid,))
        email_row = cursor.fetchone()
        email = email_row[0] if email_row else ''
        new_email = simpledialog.askstring("Edit Attendee", "Email:", initialvalue=email)
        if not new_email:
            conn.close()
            return
        cursor.execute("UPDATE attendees SET name=?, email=?, role=? WHERE ROWID=?", (new_name, new_email, new_role, iid))
        conn.commit()
        conn.close()
        self.update_attendance_history()
        messagebox.showinfo("Edit Attendee", "Attendee updated.")

    def delete_attendee(self):
        selected = self.attendance_tree.selection()
        if not selected:
            messagebox.showwarning("Delete Attendee", "No attendee selected.")
            return
        iid = selected[0]
        confirm = messagebox.askyesno("Delete Attendee", "Are you sure you want to delete this attendee?")
        if not confirm:
            return
        conn = sqlite3.connect('event_management.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM attendees WHERE ROWID=?", (iid,))
        conn.commit()
        conn.close()
        self.update_attendance_history()
        messagebox.showinfo("Delete Attendee", "Attendee deleted.")

    def logout(self):
        self.top.destroy()
        # Optionally, re-launch login window here


def launch_dashboard(username):
    DashboardWindow(root, username)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide root window until login succeeds
    def on_login_success(username):
        root.deiconify()
        launch_dashboard(username)
    LoginWindow(root, on_success=on_login_success)
    root.mainloop()


