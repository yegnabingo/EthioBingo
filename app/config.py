# app/config.py
# Configuration settings placeholder

import os

class Settings:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    DATABASE_URL = os.getenv('DATABASE_URL')

settings = Settings()
