"""_summary: This file tells gunicorn how to run the app.
"""
from app import app

if __name__ == "__main__":
    app.run()