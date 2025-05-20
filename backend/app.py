import os
print("PATH at Flask startup:", os.environ["PATH"])
try:
    import mediapipe as mp
    print("mediapipe imported successfully at Flask startup!")
except Exception as e:
    print("mediapipe import failed at Flask startup:", e)
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
import requests
import io
import csv
from ml import ml_utils
from forms import LoginForm
import sqlite3
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production
DATABASE = os.path.join(os.path.dirname(__file__), 'events.db')

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    @staticmethod
    def get_by_email(email):
        """Load user by email from the database."""
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user:
            if not isinstance(user, dict):
                user = dict(user)
            return User(user['id'], user['email'], user['password_hash'], user.get('is_admin', 0))
        return None
    """
    User model for Flask-Login integration.
    Provides static methods for loading users from the database.
    """
    def __init__(self, id, email, password_hash, is_admin=0):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin

    @staticmethod
    def get(user_id):
        """Load user by user_id from the database."""
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if user:
            if not isinstance(user, dict):
                user = dict(user)
            return User(user['id'], user['email'], user['password_hash'], user.get('is_admin', 0))
        return None

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return User.get(user_id)

def get_db_connection():
    """Create and return a new database connection (rows as dicts)."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
@login_required
def dashboard():
    if hasattr(current_user, 'is_admin') and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    stats = {
        'upcoming': conn.execute("SELECT COUNT(*) FROM events WHERE status = 'Upcoming'").fetchone()[0],
        'today': conn.execute("SELECT COUNT(*) FROM events WHERE date = date('now')").fetchone()[0],
        'completed': conn.execute("SELECT COUNT(*) FROM events WHERE status = 'Completed'").fetchone()[0],
        'total': conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        'cancelled': conn.execute("SELECT COUNT(*) FROM events WHERE status = 'Cancelled'").fetchone()[0]
    }
    q = request.args.get('q', '').strip()
    date = request.args.get('date', '').strip()
    location = request.args.get('location', '').strip()
    status = request.args.get('status', '').strip()
    query = 'SELECT * FROM events WHERE 1=1'
    params = []
    if q:
        query += ' AND LOWER(title) LIKE ?'
        params.append(f'%{q.lower()}%')
    if date:
        query += ' AND date = ?'
        params.append(date)
    if location:
        query += ' AND LOWER(location) LIKE ?'
        params.append(f'%{location.lower()}%')
    if status:
        query += ' AND status = ?'
        params.append(status)
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'asc')
    valid_sort_by = ['date', 'title', 'location', 'status']
    valid_sort_order = ['asc', 'desc']
    if sort_by not in valid_sort_by:
        sort_by = 'date'
    if sort_order not in valid_sort_order:
        sort_order = 'asc'
    query += f' ORDER BY {sort_by} {sort_order.upper()}'
    events = conn.execute(query, params).fetchall()
    results_count = len(events)
    print(f"[DEBUG] Dashboard fetched {results_count} events with query: {query} and params: {params}")
    if results_count > 0:
        print(f"[DEBUG] First event object: {events[0]}")
        print(f"[DEBUG] First event keys: {list(events[0].keys())}")
    from collections import Counter
    # Compute status counts for chart
    status_counts = Counter(event['status'] for event in events)
    # Ensure all expected keys exist
    for key in ['Upcoming', 'In Progress', 'Completed', 'Cancelled']:
        status_counts.setdefault(key, 0)
    conn.close()
    return render_template('dashboard.html', stats=stats, events=events, request=request, results_count=results_count, status_counts=status_counts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if not username or not email or not password:
            flash('Please fill all fields!')
            return render_template('register.html')
        conn = get_db_connection()
        if conn.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone():
            conn.close()
            flash('Username already exists!')
            return render_template('register.html')
        if User.get_by_email(email):
            conn.close()
            flash('Email already registered!')
            return render_template('register.html')
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 0)',
                     (username, email, password_hash))
        conn.commit()
        conn.close()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    # Only allow if no admin exists
    conn = get_db_connection()
    admin_exists = conn.execute('SELECT 1 FROM users WHERE is_admin = 1').fetchone()
    conn.close()
    if admin_exists:
        flash('Admin registration is disabled: an admin already exists.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if not username or not email or not password:
            flash('Please fill all fields!')
            return render_template('admin_register.html')
        conn = get_db_connection()
        if conn.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone():
            conn.close()
            flash('Username already exists!')
            return render_template('admin_register.html')
        if User.get_by_email(email):
            conn.close()
            flash('Email already registered!')
            return render_template('admin_register.html')
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 1)',
                     (username, email, password_hash))
        conn.commit()
        conn.close()
        flash('Admin account created! Please log in.')
        return redirect(url_for('login'))
    return render_template('admin_register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        form = LoginForm()
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        admin_exists = conn.execute('SELECT 1 FROM users WHERE is_admin = 1').fetchone() is not None
        conn.close()
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data
            user = User.get_by_email(email)
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash('Logged in successfully!')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password!')
        return render_template('login.html', admin_exists=admin_exists, form=form)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        flash('An error occurred during login.')
        return render_template('login.html', admin_exists=True, form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user:
            flash('A password reset link has been sent to your email address. (Demo: No real email sent)')
        else:
            flash('No account found with that email address.')
    return render_template('forgot_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!')
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_event():
    import datetime
    if request.method == 'POST':
        title = request.form['title'].strip()
        date = request.form['date'].strip()
        time = request.form['time'].strip()
        location = request.form['location'].strip()
        status = request.form['status'].strip()
        description = request.form['description'].strip()
        attendance = request.form.get('attendance', 0)

        # Strict validation rules
        errors = []
        # Required fields
        if not title or not date or not time or not location or not status:
            errors.append('All fields except description are required.')
        # Validate date (not in the past)
        try:
            event_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            today = datetime.date.today()
            if event_date < today:
                errors.append('Event date cannot be in the past.')
        except ValueError:
            errors.append('Invalid date format.')
        # Validate time
        try:
            datetime.datetime.strptime(time, '%H:%M')
        except ValueError:
            errors.append('Invalid time format. Use HH:MM (24-hour).')
        # Validate attendance
        try:
            attendance = int(attendance)
            if attendance < 0:
                errors.append('Attendance must be a positive integer.')
        except ValueError:
            errors.append('Attendance must be a positive integer.')
        # Check for duplicate event (same date, time, location)
        conn = get_db_connection()
        duplicate = conn.execute('SELECT 1 FROM events WHERE date = ? AND time = ? AND LOWER(location) = ?',
                                (date, time, location.lower())).fetchone()
        if duplicate:
            errors.append('An event at this date, time, and location already exists.')
        if errors:
            for error in errors:
                flash(error, 'danger')
            conn.close()
            return render_template('add_event.html')
        # Insert event if all validations pass
        conn.execute('INSERT INTO events (title, date, time, location, status, description, attendance, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     (title, date, time, location, 'Pending Approval', description, attendance, current_user.id))
        conn.commit()
        conn.close()
        flash('Event added successfully! Notification: New event created.')
        return redirect(url_for('dashboard'))
    return render_template('add_event.html')

@app.route('/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    import sqlite3
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event:
        conn.close()
        flash('Event not found.')
        return redirect(url_for('dashboard'))
    # Block editing if event is completed
    editing_blocked = event['status'] == 'Completed'
    if request.method == 'POST' and not ('approve_event' in request.form):
        if editing_blocked:
            flash('Editing is not allowed for completed events.')
            conn.close()
            return redirect(url_for('edit_event', event_id=event_id))
    # Only admin can approve events
    if request.method == 'POST' and 'approve_event' in request.form:
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            flash('Only admins can approve events!')
            conn.close()
            return redirect(url_for('edit_event', event_id=event_id))
        conn.execute('UPDATE events SET status = ? WHERE id = ?', ('Upcoming', event_id))
        conn.commit()
        conn.close()
        flash('Event approved and set to Upcoming!')
        return redirect(url_for('edit_event', event_id=event_id))
        flash('Event approved!')
        return redirect(url_for('edit_event', event_id=event_id))
    from datetime import datetime, timedelta
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    attendees = conn.execute('SELECT * FROM attendees WHERE event_id = ?', (event_id,)).fetchall()
    creator_email = None
    if event and 'created_by' in event.keys():
        creator = conn.execute('SELECT email FROM users WHERE id = ?', (event['created_by'],)).fetchone()
        if creator:
            creator_email = creator['email']
    prediction = None
    now = datetime.now()
    event_date = datetime.strptime(event['date'] + ' ' + event['time'], '%Y-%m-%d %H:%M')
    # Block editing for completed or in-progress (after start) events
    if event['status'] == 'Completed':
        conn.close()
        flash('Cannot edit a completed event.')
        return redirect(url_for('dashboard'))
    if event['status'] == 'In Progress' and now >= event_date:
        conn.close()
        flash('Cannot edit an event that is in progress and already started.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        time = request.form['time']
        location = request.form['location']
        status = request.form['status']
        description = request.form['description']
        attendance = request.form.get('attendance', 0)
        # Validate: if status is Upcoming, date/time must be in the future
        try:
            new_event_dt = datetime.strptime(date + ' ' + time, '%Y-%m-%d %H:%M')
        except Exception:
            conn.close()
            flash('Invalid date or time format.')
            return redirect(request.url)
        if status == 'Upcoming' and new_event_dt <= now:
            conn.close()
            flash('For upcoming events, date and time must be in the future.')
            return redirect(request.url)
        if status == 'Completed':
            conn.close()
            flash('Cannot set status to Completed from edit page.')
            return redirect(request.url)
        if status == 'In Progress' and new_event_dt <= now:
            conn.close()
            flash('Cannot set event to In Progress if start time has passed.')
            return redirect(request.url)
        if status == 'Approved' and not (hasattr(current_user, 'is_admin') and current_user.is_admin):
            conn.close()
            flash('Only admins can approve events!')
            return redirect(request.url)
        conn.execute('UPDATE events SET title=?, date=?, time=?, location=?, status=?, description=?, attendance=? WHERE id=?',
                     (title, date, time, location, status, description, attendance, event_id))
        conn.commit()
        conn.close()
        flash(f"Event updated! Notification: Status is now '{status}'.")
        return redirect(url_for('dashboard'))
    # ML prediction logic
    model, feature_columns = ml_utils.train_attendance_model()
    if model is not None and feature_columns is not None:
        event_features = {
            'date': event['date'],
            'location': event['location'],
            'status': event['status']
        }
        prediction = ml_utils.predict_attendance(event_features, model, feature_columns)
    conn.close()
    from datetime import datetime
    now = datetime.now()
    return render_template('edit_event.html', event=event, attendees=attendees, prediction=prediction, now=now, creator_email=creator_email)

@app.route('/edit/<int:event_id>/add_attendee', methods=['POST'])
@login_required
def add_attendee(event_id):
    import mediapipe as mp
    import cv2
    import numpy as np
    import tempfile
    import base64
    import json
    name = request.form['name']
    email = request.form['email']
    role = request.form['role']
    file = request.files.get('photo')
    img = None
    if not file or file.filename == '':
        webcam_photo = request.form.get('webcam_photo')
        if webcam_photo and webcam_photo.startswith('data:image'):
            header, encoded = webcam_photo.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            img_array = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp:
            file.save(temp.name)
            img = cv2.imread(temp.name)
    face_landmarks = None
    if img is not None:
        mp_face = mp.solutions.face_mesh
        with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
            results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if results.multi_face_landmarks:
                face_landmarks = json.dumps([[lm.x, lm.y, lm.z] for lm in results.multi_face_landmarks[0].landmark])
    conn = get_db_connection()
    conn.execute("INSERT INTO attendees (event_id, name, email, status, role, previous_attendance_rate, face_landmarks) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (event_id, name, email, 'Registered', role, 0.0, face_landmarks))
    conn.commit()
    conn.close()
    flash('Attendee added!')
    return redirect(url_for('edit_event', event_id=event_id))

@app.route('/edit/<int:event_id>/edit_attendee/<int:attendee_id>', methods=['POST'])
@login_required
def edit_attendee(event_id, attendee_id):
    name = request.form['edit_name']
    email = request.form['edit_email']
    role = request.form['edit_role']
    conn = get_db_connection()
    conn.execute("UPDATE attendees SET name=?, email=?, role=? WHERE id=?", (name, email, role, attendee_id))
    conn.commit()
    conn.close()
    flash('Attendee updated!')
    return redirect(url_for('edit_event', event_id=event_id))

@app.route('/edit/<int:event_id>/delete_attendee/<int:attendee_id>', methods=['POST'])
@login_required
def delete_attendee(event_id, attendee_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM attendees WHERE id=?", (attendee_id,))
    conn.commit()
    conn.close()
    flash('Attendee deleted!')
    return redirect(url_for('edit_event', event_id=event_id))


@app.route('/face_checkin/<int:event_id>', methods=['GET', 'POST'])
@login_required
def face_checkin(event_id):
    from flask import session, request
    # Support attendee change via query param
    if request.method == 'GET' and request.args.get('change_attendee') == '1':
        session.pop('face_checkin_attendee_id', None)
    """
    Step 1: Attendee selects their name from the list (POST or session)
    Step 2: Only allow face check-in for the selected attendee
    """
    import mediapipe as mp
    import cv2
    import numpy as np
    import tempfile
    import base64
    import json
    from scipy.spatial import distance
    from flask import session
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    attendees = conn.execute('SELECT * FROM attendees WHERE event_id = ?', (event_id,)).fetchall()
    conn.close()
    attendee_id = session.get('face_checkin_attendee_id')
    if request.method == 'POST':
        # Step 1: If attendee_id not in session or POST, show selection form
        if 'attendee_id' in request.form:
            attendee_id = int(request.form['attendee_id'])
            session['face_checkin_attendee_id'] = attendee_id
        elif not attendee_id:
            return render_template('face_select_attendee.html', event=event, attendees=attendees)
        # Step 2: Handle face check-in for selected attendee
        if 'photo' in request.files or request.form.get('webcam_photo'):
            file = request.files.get('photo')
            img = None
            if not file or file.filename == '':
                webcam_photo = request.form.get('webcam_photo')
                if webcam_photo and webcam_photo.startswith('data:image'):
                    header, encoded = webcam_photo.split(',', 1)
                    img_bytes = base64.b64decode(encoded)
                    img_array = np.frombuffer(img_bytes, np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp:
                    file.save(temp.name)
                    img = cv2.imread(temp.name)
            if img is not None and attendee_id:
                mp_face = mp.solutions.face_mesh
                with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
                    results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                    if not results.multi_face_landmarks:
                        flash('No face detected in the submitted photo. Please try again.')
                        return redirect(request.url)
                    input_landmarks = np.array([[lm.x, lm.y, lm.z] for lm in results.multi_face_landmarks[0].landmark])
                    # Only compare to selected attendee
                    conn = get_db_connection()
                    attendee = conn.execute('SELECT * FROM attendees WHERE id = ?', (attendee_id,)).fetchone()
                    db_landmarks = attendee['face_landmarks']
                    match_info = ''
                    if db_landmarks:
                        db_landmarks_np = np.array(json.loads(db_landmarks))
                        if db_landmarks_np.shape == input_landmarks.shape:
                            dist = np.mean(np.linalg.norm(db_landmarks_np - input_landmarks, axis=1))
                            if dist < 0.03:
                                conn.execute('UPDATE attendees SET status = ? WHERE id = ?', ('Checked In', attendee_id))
                                conn.commit()
                                match_info = f"Face matched! {attendee['name']} has been checked in. (Similarity: {1-dist/0.03:.2f})"
                            else:
                                match_info = 'Face did not match the registered reference. Please try again.'
                        else:
                            match_info = 'Reference photo is invalid. Please contact admin.'
                    else:
                        match_info = 'No reference photo found for this attendee. Please register your reference photo.'
                    conn.close()
                    return render_template('face_checkin.html', event=event, attendees=attendees, match_info=match_info)
        # If not a photo POST, show check-in form
        return render_template('face_checkin.html', event=event, attendees=attendees)
    # GET: If attendee_id not set, show selection form
    if not attendee_id:
        return render_template('face_select_attendee.html', event=event, attendees=attendees)
    return render_template('face_checkin.html', event=event, attendees=attendees)

@app.route('/predict_attendance/<int:event_id>')
@login_required
def predict_attendance_page(event_id):

    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    model, feature_columns = ml_utils.train_attendance_model()
    prediction = None
    if model is not None and feature_columns is not None:
        event_features = {
            'date': event['date'],
            'location': event['location'],
            'status': event['status']
        }
        prediction = ml_utils.predict_attendance(event_features, model, feature_columns)
    return render_template('predict_attendance.html', event=event, prediction=prediction)

@app.route('/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    flash('Event deleted successfully!')
    return redirect(url_for('dashboard'))

@app.route('/cancel/<int:event_id>', methods=['POST'])
@login_required
def cancel_event(event_id):
    conn = get_db_connection()
    conn.execute("UPDATE events SET status = 'Cancelled' WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    flash('Event cancelled! Notification: Event status set to Cancelled.')
    return redirect(url_for('dashboard'))

# --- Attendee Management ---
@app.route('/event/<int:event_id>/attendees')
@login_required
def view_attendees(event_id):
    # If admin, show face images
    show_faces = hasattr(current_user, 'is_admin') and current_user.is_admin
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    attendees = conn.execute('SELECT * FROM attendees WHERE event_id = ?', (event_id,)).fetchall()
    conn.close()
    return render_template('attendees.html', event=event, attendees=attendees, show_faces=show_faces)

@app.route('/admin/attendees')
@login_required
def admin_view_attendees():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied: Admins only!')
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    attendees = conn.execute('SELECT * FROM attendees').fetchall()
    conn.close()
    return render_template('admin_attendees.html', attendees=attendees)

@app.route('/attendees/<int:attendee_id>/update_photo', methods=['GET', 'POST'])
@login_required
def update_attendee_photo(attendee_id):
    import mediapipe as mp
    import cv2
    import numpy as np
    import tempfile
    import base64
    import json
    conn = get_db_connection()
    attendee = conn.execute('SELECT * FROM attendees WHERE id = ?', (attendee_id,)).fetchone()
    if request.method == 'POST':
        file = request.files.get('photo')
        face_landmarks = None
        img = None
        if not file or file.filename == '':
            webcam_photo = request.form.get('webcam_photo')
            if webcam_photo:
                header, encoded = webcam_photo.split(',', 1)
                img_bytes = base64.b64decode(encoded)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        else:
            temp = tempfile.NamedTemporaryFile(delete=False)
            file.save(temp.name)
            img = cv2.imread(temp.name)
            temp.close()
        if img is not None:
            mp_face_mesh = mp.solutions.face_mesh
            with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
                results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                if results.multi_face_landmarks:
                    face_landmarks = json.dumps([
                        [lm.x, lm.y, lm.z] for lm in results.multi_face_landmarks[0].landmark
                    ])
                else:
                    flash('No face detected in the provided photo. Please try again.')
                    return redirect(request.url)
            conn.execute('UPDATE attendees SET face_landmarks = ? WHERE id = ?', (face_landmarks, attendee_id))
            conn.commit()
            flash('Reference photo updated successfully!')
            event_id = attendee['event_id']
            conn.close()
            return redirect(url_for('view_attendees', event_id=event_id))
    conn.close()
    return render_template('update_attendee_photo.html', attendee=attendee)

@app.route('/calendar')
def calendar_view():
    return render_template('calendar.html')

@app.route('/api/upcoming_events')
def api_upcoming_events():
    conn = get_db_connection()
    # Assuming your 'events' table has a 'date' column and stores future events
    events = conn.execute(
        "SELECT id, title, date FROM events WHERE date >= DATE('now') ORDER BY date ASC"
    ).fetchall()
    conn.close()
    event_list = []
    for event in events:
        event_list.append({
            'id': event['id'],
            'title': event['title'],
            'date': event['date']
        })
    return jsonify({'events': event_list})

@app.route('/api/events')
def api_events():
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    # Convert events to FullCalendar format
    event_list = []
    for event in events:
        event_list.append({
            'id': event['id'],
            'title': event['title'],
            'start': event['date'],
            'url': url_for('edit_event', event_id=event['id'])
        })
    return jsonify(event_list)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied: Admins only!')
        return redirect(url_for('dashboard'))
    import datetime
    today = datetime.date.today().isoformat()
    conn = get_db_connection()
    # Auto-complete events whose date has passed
    conn.execute("UPDATE events SET status = 'Completed' WHERE (status = 'Upcoming' OR status = 'In Progress') AND date <= ?", (today,))
    conn.commit()
    users = conn.execute('SELECT id, email, is_admin FROM users').fetchall()
    events = conn.execute('SELECT * FROM events').fetchall()
    # Calculate dashboard stats
    stats = {
        'total_events': conn.execute('SELECT COUNT(*) FROM events').fetchone()[0],
        'upcoming_events': conn.execute("SELECT COUNT(*) FROM events WHERE status = 'Upcoming'").fetchone()[0],
        'completed_events': conn.execute("SELECT COUNT(*) FROM events WHERE status = 'Completed'").fetchone()[0],
        'cancelled_events': conn.execute("SELECT COUNT(*) FROM events WHERE status = 'Cancelled'").fetchone()[0],
        'pending_approval_events': conn.execute("SELECT COUNT(*) FROM events WHERE status = 'Pending Approval'").fetchone()[0],
        'total_users': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
    }
    conn.close()
    model_accuracy = session.get('model_accuracy')
    model_metrics = session.get('model_metrics')
    cm_img = session.get('cm_img')
    roc_img = session.get('roc_img')
    # Load ML model and feature importances
    model, feature_columns = ml_utils.train_attendance_model()
    feature_importances = []
    if model is not None and feature_columns is not None:
        feature_importances = ml_utils.get_feature_importances(model, feature_columns)
    return render_template('admin_dashboard.html', users=users, events=events, stats=stats, model_accuracy=model_accuracy, model_metrics=model_metrics, cm_img=cm_img, roc_img=roc_img, feature_importances=feature_importances)

@app.route('/admin/user_action', methods=['POST'])
@login_required
def admin_user_action():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied: Admins only!')
        return redirect(url_for('dashboard'))
    user_id = request.form.get('user_id')
    action = request.form.get('action')
    if not user_id or not action:
        flash('Invalid request.')
        return redirect(url_for('admin_dashboard'))
    conn = get_db_connection()
    if action == 'promote':
        conn.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
        flash('User promoted to admin.')
    elif action == 'demote':
        conn.execute('UPDATE users SET is_admin = 0 WHERE id = ?', (user_id,))
        flash('User demoted from admin.')
    elif action == 'delete':
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        flash('User deleted.')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_message = request.json.get('message', '').lower()
    # Simple rule-based AI assistant
    if any(greet in user_message for greet in ['hello', 'hi', 'hey']):
        reply = "Hello! How can I help you with your event management today?"
    elif 'help' in user_message:
        reply = "You can ask me about events, attendance, registration, or anything related to this system. For example, try: 'How do I add an event?' or 'Show me upcoming events.'"
    elif 'event' in user_message and 'add' in user_message:
        reply = "To add an event, click the 'Add Event' button on your dashboard and fill in the details."
    elif 'attendance' in user_message:
        reply = "You can predict attendance or manage attendees from the dashboard. Would you like steps for a specific feature?"
    elif 'register' in user_message:
        reply = "To register, click the 'Register' link in the navigation bar and fill out the form."
    elif 'thank' in user_message:
        reply = "You're welcome! Let me know if you have any more questions."
    elif user_message.strip() == '':
        reply = "Please type a message."
    else:
        reply = "I'm your event assistant bot. You can ask me about events, attendance, or using the system. Type 'help' to see what I can do!"
    return jsonify({"response": reply})

@app.route('/admin/event_action', methods=['POST'])
@login_required
def admin_event_action():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied: Admins only!')
        return redirect(url_for('dashboard'))
    event_id = request.form.get('event_id')
    action = request.form.get('action')
    if not event_id or not action:
        flash('Invalid request.')
        return redirect(url_for('admin_dashboard'))
    conn = get_db_connection()
    if action == 'delete':
        conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
        flash('Event deleted.')
    elif action == 'cancel':
        conn.execute("UPDATE events SET status = 'Cancelled' WHERE id = ?", (event_id,))
        flash('Event cancelled! Notification: Event status set to Cancelled.')
    elif action == 'approve':
        conn.execute("UPDATE events SET status = 'Upcoming' WHERE id = ?", (event_id,))
        flash('Event approved! Notification: Event status set to Upcoming.')
    else:
        flash('Unknown action.')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/retrain_model', methods=['POST'])
@login_required
def retrain_model():
    flash('Retrain route called (debug).')
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import confusion_matrix, roc_curve, auc
    X, y = ml_utils.extract_ml_data()
    if X.shape[0] < 10:
        flash('Not enough data to train model. Add more attendee/event records.')
        return redirect(url_for('admin_dashboard'))
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    acc, report = ml_utils.train_and_evaluate_model(X_train, y_train, X_test, y_test)
    # Save confusion matrix and ROC curve as base64
    y_pred = ml_utils.load_model().predict(X_test)
    y_score = getattr(ml_utils.load_model(), "predict_proba", lambda x: None)(X_test)
    cm_img = ml_visuals.plot_confusion_matrix(y_test, y_pred, labels=[0,1])
    roc_img = None
    if y_score is not None:
        roc_img = ml_visuals.plot_roc_curve(y_test, y_score[:,1])
    session['model_accuracy'] = f'{acc:.2%}'
    session['model_metrics'] = report
    session['cm_img'] = cm_img
    session['roc_img'] = roc_img
    flash(f'Model retrained on real data. Accuracy: {acc:.2%}')
    return redirect(url_for('admin_dashboard'))

@app.route('/predict_attendance', methods=['POST'])
@login_required
def predict_attendance():
    event_id = request.form.get('event_id')
    if not event_id:
        return jsonify({'error':'Missing event_id'}), 400
    preds = ml_utils.predict_attendance_for_event(event_id)
    # Fetch attendee names
    conn = get_db_connection()
    attendees = conn.execute('SELECT id, name FROM attendees WHERE event_id = ?', (event_id,)).fetchall()
    conn.close()
    id_to_name = {a['id']: a['name'] for a in attendees}
    pred_table = [(id_to_name.get(att_id, att_id), 'Present' if status==1 else 'Absent') for att_id, status in preds]
    return jsonify({'predictions': pred_table})

@app.route('/download_metrics')
@login_required
def download_metrics():
    metrics = session.get('model_metrics')
    if not metrics:
        return 'No metrics available', 400
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Label','Precision','Recall','F1'])
    for label, m in metrics.items():
        if label in ['accuracy','macro avg','weighted avg']:
            continue
        writer.writerow([label, m['precision'], m['recall'], m['f1-score']])
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=model_metrics.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/download_predictions/<int:event_id>')
@login_required
def download_predictions(event_id):
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Only admins can download predictions!')
        return redirect(url_for('dashboard'))
    print(f"[DEBUG] download_predictions called for event_id={event_id}")
    try:
        preds = ml_utils.predict_attendance_for_event(event_id)
        print(f"[DEBUG] Predictions: {preds}")
        conn = get_db_connection()
        attendees = conn.execute('SELECT id, name FROM attendees WHERE event_id = ?', (event_id,)).fetchall()
        conn.close()
        id_to_name = {a['id']: a['name'] for a in attendees}
        print(f"[DEBUG] id_to_name mapping: {id_to_name}")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Attendee','Predicted Status'])
        for att_id, status in preds:
            print(f"[DEBUG] Writing row: {att_id}, {status}")
            writer.writerow([id_to_name.get(att_id, att_id), 'Present' if status==1 else 'Absent'])
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=predictions_event_{event_id}.csv'
        response.headers['Content-Type'] = 'text/csv'
        print("[DEBUG] Returning CSV response")
        return response
    except Exception as e:
        print(f"[ERROR] Exception in download_predictions: {e}")
        return f"Error in download_predictions: {e}", 500

@app.route('/ml_vis/<imgtype>')
@login_required
def ml_vis(imgtype):
    img = session.get(f'{imgtype}_img')
    if not img:
        return 'No image available', 404
    return f'<img src="data:image/png;base64,{img}" />'

if __name__ == '__main__':
    app.run(debug=True)
