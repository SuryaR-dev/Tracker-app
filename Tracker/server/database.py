import sqlite3
import bcrypt
from datetime import datetime
import os

def init_database():
    """Initialize database with required tables"""
    # Create database directory if it doesn't exist
    os.makedirs('database', exist_ok=True)
    
    conn = sqlite3.connect('database/tracker.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active DATE,
            is_active BOOLEAN DEFAULT 0
        )
    ''')
    
    # Create admins table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin (username: admin, password: admin123)
    default_admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
    try:
        cursor.execute('''
            INSERT INTO admins (username, name, phone, email, password)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'Administrator', '1234567890', 'admin@bla.com', default_admin_password))
    except sqlite3.IntegrityError:
        pass  # Admin already exists
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('database/tracker.db')
    conn.row_factory = sqlite3.Row
    return conn