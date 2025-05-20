# ml_utils.py
# Utilities for machine learning features in Event Management System
# Requirements: scikit-learn, pandas, numpy

import pandas as pd
import numpy as np
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'events.db')

def extract_ml_data():
    """
    Extract features (X) and labels (y) for ML training/prediction from the events database.
    Returns:
        X (np.ndarray or pd.DataFrame): Feature matrix
        y (np.ndarray or pd.Series): Labels (e.g., attendance)
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM events", conn)
    conn.close()
    # Example: Use date, time, location, status as features, attendance as label
    if df.empty:
        return np.array([]), np.array([])
    # Convert categorical features to numeric (simple example)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['dayofweek'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['hour'] = df['time'].str.split(':').str[0].astype(float)
    X = df[['dayofweek', 'month', 'hour']].fillna(0)
    y = df['attendance'].fillna(0).astype(int)
    return X, y

# Add more ML utility functions as needed
