# TaskFlow

TaskFlow is a simple, modern smart to-do list application built with Flask, SQLite, Jinja templates, Bootstrap, and Chart.js. It is designed for a college mini-project demonstration and supports account-based task management.

## Features

- Registration and login with Werkzeug password hashing
- Guest/demo workspace
- Add, edit, delete, and complete tasks
- Pending/completed status toggle
- High, medium, and low priority
- Categories, due dates, and due times
- Search and status, priority, and category filters
- Dashboard summary cards and Chart.js statistics
- Due-today, overdue, and completed-today reminders
- Light/dark mode with browser persistence
- User-scoped tasks and parameterized SQLite queries
- JSON APIs for task lists, statistics, and task creation

## Run on Windows

Prerequisite: Python 3.10 or newer.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed_data.py
python app.py
```

Open <http://127.0.0.1:5000> in your browser.

The database is created automatically as `taskflow.db` on the first application start. The seed script is optional, but it creates useful demonstration content:

- Email: `demo@taskflow.local`
- Password: `demo123`

To use a clean database, stop the app and remove `taskflow.db`, then run `python seed_data.py` again.

## Routes

- `GET /` public landing/login page
- `GET|POST /login` login
- `GET|POST /register` account registration
- `GET /logout` logout
- `GET /guest` open the seeded demo workspace
- `GET /dashboard` authenticated dashboard
- `GET /tasks` dashboard alias
- `GET|POST /tasks/add` create a task
- `GET|POST /tasks/edit/<id>` edit a task
- `POST /tasks/delete/<id>` delete a task
- `POST /tasks/complete/<id>` toggle completion

## JSON APIs

All APIs require an authenticated session.

- `GET /api/tasks` supports `search`, `status`, `priority`, and `category` query parameters.
- `GET /api/statistics` returns dashboard counts and chart data.
- `POST /api/tasks` accepts JSON fields: `title`, `description`, `category`, `priority`, `due_date`, and `due_time`.

Example API payload:

```json
{
  "title": "Read SQLite documentation",
  "description": "Review indexes and foreign keys",
  "category": "College",
  "priority": "Low",
  "due_date": "2026-09-20",
  "due_time": "14:00"
}
```

## Project structure

```text
TaskFlow/
├── app.py
├── requirements.txt
├── README.md
├── seed_data.py
├── taskflow.db          # generated at runtime
├── data/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_task.html
│   └── edit_task.html
└── static/
    ├── css/style.css
    └── js/app.js
```

For local development, Flask uses a development secret key fallback. Set `TASKFLOW_SECRET_KEY` to a long random value before deploying anywhere beyond a local demo. SQLite is appropriate for this small single-process project; a production deployment would need stronger CSRF protection, secure cookie settings, and a managed database.
