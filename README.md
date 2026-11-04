# Students Management Portal

A responsive, role-based student and attendance management portal built with
Django, Neon PostgreSQL, HTML, Bootstrap, CSS, and JavaScript.

## What is implemented

- **Admin:** dashboard metrics, course and batch management in Django admin,
  student/staff registration and profile management, deactivation, attendance
  marking, monthly/daily reports, and audit history.
- **Staff:** assigned batch and student views, student registration and
  authorized profile updates, student attendance marking for assigned
  batches, attendance reports, own profile/history.
- **Student:** private dashboard, own profile and course/batch details,
  attendance history, monthly reports, attendance percentage, password reset.
- Shared authentication with role checks on the server, hashed passwords,
  CSRF-protected forms, duplicate username/email checks (including case),
  transactional profile/account registration, and unique per-person daily
  attendance records.
- Admin-managed accounts, courses, batches, assignments, and attendance are
  available at `/admin/`.

## Architecture and data relationships

| Django app | Responsibility |
| --- | --- |
| `accounts` | Custom user model, roles, authentication, and authorization helpers |
| `students` | Student profiles, registration, updates, and profile audit history |
| `staff` | Staff profiles, batch assignments, and profile audit history |
| `academics` | Courses and batches |
| `attendance` | Student/staff attendance, reports, and change audit history |
| `dashboard` | Role-specific dashboards and database health check |

`accounts.User` is the identity for the `ADMIN`, `STAFF`, and `STUDENT` roles.
Students and staff each have one profile linked one-to-one to a user. A course
has many batches; each batch belongs to one course. Students belong to one
batch. Staff and batches are many-to-many. Student and staff attendance each
have a unique constraint on person/date. Attendance records store the marker
and last modifier; append-only audit records retain status changes. Profile
audit entries record the actor, action, changed field names, and timestamp
without duplicating sensitive profile values.

## Run locally on Windows

Open the project folder in VS Code, then use **Terminal → New Terminal**:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The app loads settings from the project's `.env` file automatically; values
already set in the process environment take precedence. Put your Neon
connection URL in `.env` as `DATABASE_URL=...`; Neon is the required database
for all portal reads and updates. Keep `.env` private and never commit or share
its contents.

Visit:

- Portal dashboard/login: `http://127.0.0.1:8000/`
- Django admin: `http://127.0.0.1:8000/admin/`

There is no SQLite fallback. If `DATABASE_URL` is missing or blank, Django
stops with a configuration error instead of silently saving data to a local
database.

Student registration accepts a
typed course name and offers Batch 22 through Batch 27; for Admin registrations,
the portal creates the course and selected batch if they do not already exist.
To give Staff access to a batch, first create the course and batch in Django
admin (`Academics → Courses`, then `Academics → Batches`) and assign that batch
when adding staff or editing the staff profile. Staff can only register
students in their assigned course and batch.

### Main portal routes

| Route | Purpose |
| --- | --- |
| `/` | Role-aware dashboard |
| `/students/` | Student directory (Admin/Staff) |
| `/students/register/` | Student registration (Admin/Staff) |
| `/staff/` | Staff directory (Admin) |
| `/staff/add/` | Create staff account (Admin) |
| `/attendance/batch/<id>/mark/` | Mark/edit student attendance |
| `/attendance/staff/mark/` | Mark/edit staff attendance (Admin) |
| `/attendance/daily/` | Daily attendance report |
| `/attendance/reports/` | Monthly student attendance report |
| `/attendance/staff/history/` | Monthly staff attendance history |
| `/accounts/password_reset/` | Password reset request |
| `/health/` | Database-backed health check |

## Neon PostgreSQL

Set `DATABASE_URL` in the ignored `.env` file to the Neon connection string.
Include `sslmode=require`; never put credentials in frontend files or commit
them. The command-line override remains available if needed:

```powershell
$env:DATABASE_URL = "paste-your-full-Neon-connection-string-here"
python manage.py migrate
python manage.py runserver
```

Copy the full connection string from Neon (including its `postgresql://` prefix)
and keep it secret. `DJANGO_DEBUG`
should be false in production; production also requires an explicit,
high-entropy `DJANGO_SECRET_KEY`.

## Deploy to Render

The repository includes `render.yaml` and `build.sh`. Create a Render web
service from the repository, provide the Neon `DATABASE_URL`, and set the
SMTP variables (`EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and
`DEFAULT_FROM_EMAIL`) so password reset links can be delivered. Render
generates the Django secret key and provides the public hostname. The build
installs dependencies, collects static assets, and runs migrations; Gunicorn
serves Django over Render's HTTPS endpoint.

Keep the Neon URL, SMTP credentials, and all production secrets in Render's
environment-variable settings, not in Git.

## Deploy to Vercel

The project uses Vercel's native Django detection and sets the WSGI entry point
in `pyproject.toml`. Import the GitHub repository into Vercel and set these
environment variables for Production:

- `DATABASE_URL`: Neon PostgreSQL connection URL.
- `DJANGO_SECRET_KEY`: a long, unique secret.
- `DJANGO_DEBUG`: `False`.
- `DJANGO_ALLOWED_HOSTS`: the production Vercel hostname.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: the HTTPS production URL.

Vercel collects and serves Django static assets during its build. If the schema
needs updates, run `python manage.py migrate` against the same Neon database
before deploying. Never commit `.env` or paste database credentials into Git.

## Checks and tests

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Tests cover password hashing/login, dashboards, student registration,
role/batch authorization, profile privacy, attendance marking and editing,
audit history, and reports.
