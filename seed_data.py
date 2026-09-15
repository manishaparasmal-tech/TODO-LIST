from datetime import date, timedelta
from pathlib import Path
import sqlite3

from werkzeug.security import generate_password_hash

from app import DATABASE, init_db

DEMO_EMAIL = "demo@taskflow.local"
DEMO_PASSWORD = "demo123"


def seed():
    init_db()
    database = sqlite3.connect(DATABASE)
    database.row_factory = sqlite3.Row
    user = database.execute("SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)).fetchone()
    if user is None:
        cursor = database.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", ("Demo User", DEMO_EMAIL, generate_password_hash(DEMO_PASSWORD)))
        user_id = cursor.lastrowid
    else:
        user_id = user["id"]
    if database.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
        today = date.today()
        tasks = [
            ("Complete Python Assignment", "Finish the functions and run the tests.", "College", "High", today.isoformat(), "18:00", "pending"),
            ("Prepare for DSA Exam", "Review trees, graphs, and dynamic programming notes.", "College", "Medium", (today + timedelta(days=3)).isoformat(), "10:00", "pending"),
            ("Submit Mini Project", "Upload the final report and presentation.", "Work", "High", (today + timedelta(days=1)).isoformat(), "16:30", "pending"),
            ("Buy groceries", "Fruit, coffee, pasta, and something green.", "Shopping", "Low", (today + timedelta(days=2)).isoformat(), "12:30", "pending"),
            ("Attend team meeting", "Bring the weekly progress update.", "Work", "Medium", (today - timedelta(days=1)).isoformat(), "09:30", "completed"),
            ("Complete Flask tutorial", "Build the final CRUD example.", "Personal", "Low", (today - timedelta(days=2)).isoformat(), None, "completed"),
        ]
        database.executemany("INSERT INTO tasks (user_id, title, description, category, priority, due_date, due_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [(user_id, *task) for task in tasks])
    database.commit()
    database.close()
    print(f"Seed complete. Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
