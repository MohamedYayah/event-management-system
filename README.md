# Event Management System

**Note: This project now supports only the web-based version. The desktop (Tkinter) version is deprecated and can be ignored or deleted.**

A modern, user-friendly Event Management System built with Python, Tkinter, SQLite, and integrated with machine learning for attendance prediction and face detection for automated attendance tracking.

## Features

- **User Authentication:** Register and log in securely (passwords hashed).
- **Event Management:** Add, edit, delete, and view events with a clean UI.
- **Calendar View:** Interactive calendar with navigation and event display.
- **Attendance Prediction:** Predict event attendance using ML (scikit-learn, pandas, numpy).
- **Face Detection:** Automated attendance tracking using MediaPipe and OpenCV.
- **Database:** SQLite backend with auto-initialization.
- **Machine Learning Attendance Prediction:**
    - Model accuracy metrics shown to admin
    - Admin can retrain model with new data from dashboard
- **Face Detection for Attendance:**
    - Live webcam/photo preview
    - User-friendly instructions and error handling
    - Retry and success feedback for check-in

## Quickstart (Web Version)

1. **Clone or Download** this repository.
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the web application:**
   ```bash
   python app.py
   ```
4. **Open your browser and go to:**
   [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Machine Learning Attendance Prediction
- Attendance prediction is built-in to the web app!
- When editing an event, click the "Predict Attendance" button to use the ML model (scikit-learn, pandas, numpy required).
- The model is trained on your event data and predicts expected attendance for new events.

## Requirements
- Python 3.8+
- scikit-learn
- pandas
- numpy
- opencv-python
- mediapipe
- flask, flask-login, werkzeug, etc. (see requirements.txt)

## Project Structure

```
Web Dev/
│
├── backend/
│   ├── app.py                  # Main Flask app
│   ├── forms.py                # Flask-WTForms (if used)
│   ├── init_db.py              # DB initialization script
│   ├── ml/
│   │   └── ml_utils.py         # Machine learning utilities
│   ├── utils/
│   │   ├── face_utils.py       # Face detection helpers
│   │   ├── mediapipe_demo.py   # MediaPipe hand demo
│   │   └── mediapipe_face_demo.py # MediaPipe face demo
│   ├── static/                 # Static assets (CSS/JS)
│   ├── templates/              # Jinja2 HTML templates
│   │   └── _chatbot_widget.html # Modular chatbot widget
│   └── uploads/                # Uploaded files (if any)
│
├── actions/
│   └── actions.py              # Rasa custom actions
├── data/
│   ├── nlu.yml
│   ├── rules.yml
│   └── stories.yml
├── tests/
│   └── tkinter_test.py         # Tkinter test script
├── scripts/
│   └── ... (migration/util scripts)
├── database/
│   └── ... (db backups/seeds)
├── models/
│   └── ... (ML model files)
├── .venv/                      # Virtual environment
├── .rasa/                      # Rasa config/state
├── README.md
├── requirements.txt
├── config.yml
├── credentials.yml
├── endpoints.yml
├── domain.yml
└── archive/                    # Deprecated/old files
```

- All ML code is now in `backend/ml/ml_utils.py`.
- Utility/demo scripts are in `backend/utils/`.
- Test scripts are in `tests/`.
- Chatbot widget is modular and included in all dashboards.
- No duplicate or orphaned files remain.

## Chatbot Integration
- The Event Management System features a Rasa-powered AI chatbot.
- The chatbot can answer questions about upcoming events using live data from the Flask backend.
- To enable: run Flask, Rasa server, and Rasa action server as described in Quickstart.

## Final Polish for Presentation
- All code is clean, modular, and well-commented.
- UI/UX is modern and professional.
- All known bugs and duplicate files have been eliminated.
- Project is ready for demonstration and handoff.

## Usage

### ML Attendance Model
- Admins see latest model accuracy and metrics in the dashboard.
- Click **Retrain Model** to train with new data. Metrics update instantly.

## Requirements

- Python 3.8+
- scikit-learn
- pandas
- numpy
- opencv-python
- mediapipe
- tkinter (usually included with Python)

## Demo Workflow

1. **Register a new user and log in.**
2. **Add, edit, or delete events.**
3. **Navigate the calendar and view events.**
4. **Predict attendance for an event (uses ML).**
5. **(Optional) Demonstrate face/hand detection for automated attendance.**

## Credits
- Developed by [Your Name]
- For IS Final Presentation, 2025
