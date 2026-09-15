import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "taskflow.db"
ALLOWED_PRIORITIES = {"High", "Medium", "Low"}
ALLOWED_CATEGORIES = {"College", "Work", "Personal", "Shopping", "Other"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("TASKFLOW_SECRET_KEY", "taskflow-development-key")
app.config["DATABASE"] = str(DATABASE)


def get_db():
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    database = get_db()
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT NOT NULL DEFAULT 'Other',
            priority TEXT NOT NULL DEFAULT 'Medium',
            due_date TEXT,
            due_time TEXT,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'completed')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_tasks_user_due_date ON tasks(user_id, due_date);
        """)
    database.commit()
    database.close()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    database = get_db()
    user = database.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    database.close()
    return user


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def validate_task_form(form):
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    category = form.get("category", "Other").strip()
    priority = form.get("priority", "Medium").strip()
    due_date = form.get("due_date", "").strip() or None
    due_time = form.get("due_time", "").strip() or None
    errors = []

    if not title:
        errors.append("Task title is required.")
    elif len(title) > 120:
        errors.append("Task title must be 120 characters or fewer.")
    if len(description) > 500:
        errors.append("Description must be 500 characters or fewer.")
    if category not in ALLOWED_CATEGORIES:
        errors.append("Choose a valid category.")
    if priority not in ALLOWED_PRIORITIES:
        errors.append("Choose a valid priority.")
    if due_date:
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            errors.append("Enter a valid due date.")
    if due_time:
        try:
            datetime.strptime(due_time, "%H:%M")
        except ValueError:
            errors.append("Enter a valid due time.")

    return {
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "due_date": due_date,
        "due_time": due_time,
    }, errors


def task_query(filters=None):
    filters = filters or {}
    clauses = ["user_id = ?"]
    values = [session["user_id"]]
    search = filters.get("search", "").strip()
    status = filters.get("status", "all")
    priority = filters.get("priority", "all")
    category = filters.get("category", "all")
    if search:
        clauses.append("(title LIKE ? OR description LIKE ?)")
        values.extend([f"%{search}%", f"%{search}%"])
    if status in {"pending", "completed"}:
        clauses.append("status = ?")
        values.append(status)
    if priority in ALLOWED_PRIORITIES:
        clauses.append("priority = ?")
        values.append(priority)
    if category in ALLOWED_CATEGORIES:
        clauses.append("category = ?")
        values.append(category)
    query = f"SELECT * FROM tasks WHERE {' AND '.join(clauses)} ORDER BY status ASC, due_date IS NULL, due_date ASC, due_time ASC, created_at DESC"
    database = get_db()
    tasks = database.execute(query, values).fetchall()
    database.close()
    return tasks


def get_statistics():
    database = get_db()
    user_id = session["user_id"]
    totals = database.execute(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                  SUM(CASE WHEN priority = 'High' AND status = 'pending' THEN 1 ELSE 0 END) AS high_priority,
                  SUM(CASE WHEN due_date = ? AND status = 'pending' THEN 1 ELSE 0 END) AS due_today,
                  SUM(CASE WHEN due_date < ? AND status = 'pending' THEN 1 ELSE 0 END) AS overdue
           FROM tasks WHERE user_id = ?""",
        (date.today().isoformat(), date.today().isoformat(), user_id),
    ).fetchone()
    completed_today = database.execute(
        "SELECT COUNT(*) AS count FROM tasks WHERE user_id = ? AND status = 'completed' AND date(updated_at) = date('now', 'localtime')",
        (user_id,),
    ).fetchone()["count"]
    categories = database.execute("SELECT category AS label, COUNT(*) AS count FROM tasks WHERE user_id = ? GROUP BY category ORDER BY count DESC", (user_id,)).fetchall()
    priorities = database.execute("SELECT priority AS label, COUNT(*) AS count FROM tasks WHERE user_id = ? GROUP BY priority ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END", (user_id,)).fetchall()
    database.close()
    return {
        "total": totals["total"] or 0,
        "pending": totals["pending"] or 0,
        "completed": totals["completed"] or 0,
        "high_priority": totals["high_priority"] or 0,
        "due_today": totals["due_today"] or 0,
        "overdue": totals["overdue"] or 0,
        "completed_today": completed_today,
        "categories": [dict(row) for row in categories],
        "priorities": [dict(row) for row in priorities],
    }


def task_to_dict(task):
    return {key: task[key] for key in task.keys()}


@app.context_processor
def inject_user():
    return {"current_user": current_user(), "today": date.today().isoformat()}


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        database = get_db()
        user = database.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        database.close()
        if not user or not check_password_hash(user["password"], password):
            flash("We could not match that email and password.", "danger")
            return render_template("login.html", email=email), 401
        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name'].split()[0]}.", "success")
        destination = request.args.get("next") or url_for("dashboard")
        return redirect(destination if destination.startswith("/") else url_for("dashboard"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []
        if len(name) < 2:
            errors.append("Enter your name.")
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            errors.append("Enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("register.html", name=name, email=email), 400
        database = get_db()
        try:
            cursor = database.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, generate_password_hash(password)))
            database.commit()
        except sqlite3.IntegrityError:
            database.close()
            flash("An account with that email already exists.", "danger")
            return render_template("register.html", name=name, email=email), 409
        database.close()
        session.clear()
        session["user_id"] = cursor.lastrowid
        flash("Your TaskFlow account is ready.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/guest")
def guest():
    database = get_db()
    user = database.execute("SELECT id FROM users WHERE email = ?", ("demo@taskflow.local",)).fetchone()
    database.close()
    if not user:
        flash("Demo access is not seeded yet. Run seed_data.py first.", "warning")
        return redirect(url_for("login"))
    session.clear()
    session["user_id"] = user["id"]
    flash("You are exploring the demo workspace.", "info")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    filters = {key: request.args.get(key, "") for key in ("search", "status", "priority", "category")}
    return render_template("dashboard.html", tasks=task_query(filters), stats=get_statistics(), filters=filters, categories=sorted(ALLOWED_CATEGORIES))


@app.route("/tasks")
@login_required
def tasks():
    return redirect(url_for("dashboard", **request.args))


@app.route("/tasks/add", methods=["GET", "POST"])
@login_required
def add_task():
    if request.method == "POST":
        task, errors = validate_task_form(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("add_task.html", task=task), 400
        database = get_db()
        database.execute("INSERT INTO tasks (user_id, title, description, category, priority, due_date, due_time) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], task["title"], task["description"], task["category"], task["priority"], task["due_date"], task["due_time"]))
        database.commit()
        database.close()
        flash("Task added to your flow.", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_task.html", task={"category": "Personal", "priority": "Medium"})


@app.route("/tasks/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    database = get_db()
    task = database.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, session["user_id"])).fetchone()
    if not task:
        database.close()
        flash("That task could not be found.", "warning")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        values, errors = validate_task_form(request.form)
        if errors:
            database.close()
            for error in errors:
                flash(error, "danger")
            return render_template("edit_task.html", task={**dict(task), **values}), 400
        database.execute("UPDATE tasks SET title = ?, description = ?, category = ?, priority = ?, due_date = ?, due_time = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?", (values["title"], values["description"], values["category"], values["priority"], values["due_date"], values["due_time"], task_id, session["user_id"]))
        database.commit()
        database.close()
        flash("Task updated.", "success")
        return redirect(url_for("dashboard"))
    database.close()
    return render_template("edit_task.html", task=task)


@app.post("/tasks/delete/<int:task_id>")
@login_required
def delete_task(task_id):
    database = get_db()
    cursor = database.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, session["user_id"]))
    database.commit()
    database.close()
    flash("Task deleted." if cursor.rowcount else "That task could not be found.", "info" if cursor.rowcount else "warning")
    return redirect(url_for("dashboard"))


@app.post("/tasks/complete/<int:task_id>")
@login_required
def complete_task(task_id):
    database = get_db()
    task = database.execute("SELECT status FROM tasks WHERE id = ? AND user_id = ?", (task_id, session["user_id"])).fetchone()
    if task:
        new_status = "pending" if task["status"] == "completed" else "completed"
        database.execute("UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?", (new_status, task_id, session["user_id"]))
        database.commit()
    database.close()
    flash("Task status updated." if task else "That task could not be found.", "success" if task else "warning")
    return redirect(url_for("dashboard"))


@app.get("/api/tasks")
@login_required
def api_tasks():
    filters = {key: request.args.get(key, "") for key in ("search", "status", "priority", "category")}
    return jsonify({"tasks": [task_to_dict(task) for task in task_query(filters)]})


@app.post("/api/tasks")
@login_required
def api_add_task():
    task, errors = validate_task_form(request.get_json(silent=True) or {})
    if errors:
        return jsonify({"errors": errors}), 400
    database = get_db()
    cursor = database.execute("INSERT INTO tasks (user_id, title, description, category, priority, due_date, due_time) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], task["title"], task["description"], task["category"], task["priority"], task["due_date"], task["due_time"]))
    database.commit()
    created = database.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
    database.close()
    return jsonify({"task": task_to_dict(created)}), 201


@app.get("/api/statistics")
@login_required
def api_statistics():
    return jsonify(get_statistics())


init_db()

if __name__ == "__main__":
    app.run(debug=True)
