import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE_PATH = 'database/tracker.db'
    USER_DATA_PATH = 'user_data'
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000