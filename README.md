# CareerConnect — Online Job Portal

**CareerConnect** is a full-stack web application built with **Django**, **SQLite**, **HTML5/CSS3**, **JavaScript**, and **Bootstrap 5** that connects Job Seekers, Employers, and Platform Administrators in a role-based hiring portal. It provides authenticated user registration and login, dedicated role dashboards, job posting management, job search and filtering, job bookmarking (**Saved Jobs**), private PDF resume upload and authorized downloads, application status tracking with chronological audit history, environment-based configuration, and an in-portal Admin Dashboard alongside Django Admin.

---

## Table of Contents

- [Main Features](#main-features)
- [Role-Based Features](#role-based-features)
  - [Job Seeker Features](#job-seeker-features)
  - [Employer Features](#employer-features)
  - [Admin Features](#admin-features)
- [Technologies Used](#technologies-used)
- [Project Folder Structure](#project-folder-structure)
- [Installation Instructions](#installation-instructions)
- [Environment Configuration](#environment-configuration)
- [Database Migration Commands](#database-migration-commands)
- [How to Run the Project](#how-to-run-the-project)
- [Future Enhancements](#future-enhancements)
- [Author](#author)

---

## Main Features

- **Role-Based Authentication & Access Control**
  - User registration with Full Name, Email, Password, Confirm Password, and Role selection (`Job Seeker` or `Employer`).
  - Case-insensitive duplicate email checks, Django password validation/hashing, and `UserProfile` creation.
  - Email-and-password authentication with role-aware dashboard routing (`/accounts/dashboard/`) and HTTP-only session and CSRF cookies.
  - POST-only logout and custom `403 Access Denied` handling via `@role_required` and `@staff_required` decorators.
- **Public Job Directory, Search & Bookmarking**
  - Responsive Home page (`/`) and Find Jobs directory (`/jobs/`) displaying active job listings with company initials avatars and skill tags.
  - Keyword search across job title, company name, description, job type, required skills, and experience, combined with Location and Job Type (`Full-Time`, `Part-Time`, `Remote`, `Hybrid`, `Contract`) filters.
  - Pre-seeded sample job listings included via Django data migrations (`jobs/migrations/0002_seed_sample_jobs.py` and `0004_populate_job_experience.py`).
  - Saved Jobs (`SavedJob`) model with database-level uniqueness per `(user, job)` for Job Seekers.
- **Private PDF Resume Handling & Validation**
  - Strict PDF validation enforcing `.pdf` extension, `%PDF-` file header signature, and a 5 MB maximum upload size (`accounts/validators.py`).
  - No unauthenticated `/media/` static exposure (`CareerConnect/urls.py`).
  - Authorized download (`attachment`) and inline browser preview (`?inline=1`) endpoints returning `Content-Type: application/pdf` and `X-Content-Type-Options: nosniff` (`accounts/files.py`).
- **Application Status Tracking & History**
  - Four application workflow stages: **Applied**, **Shortlisted**, **Rejected**, and **Selected**.
  - Automatic chronological transition tracking via `ApplicationStatusHistory` (recording status, timestamp, and the user who made the change).
- **Security & Privacy Hardening**
  - Secret keys, debug mode, allowed hosts, and SMTP/email settings loaded from environment variables / `.env` (`.env.example` template provided; `.env` excluded by `.gitignore`).
  - Strict cross-user isolation, ownership checks on employer job/applicant management, CSRF protection on all state-changing forms, and employer login emails hidden from public job detail pages.

---

## Role-Based Features

### Job Seeker Features

- Register and log in as a Job Seeker to access the protected **Job Seeker Dashboard** (`/accounts/dashboard/job-seeker/`).
- View and update profile information: Full Name, Phone, Location, Qualification, Comma-separated Skills, and PDF Resume (with live client-side file hint and server-side PDF verification).
- Securely view (`?inline=1`) or download your own profile resume via `/accounts/profile/resume/`.
- Browse available open positions and inspect full job details (`/jobs/<job_id>/`).
- Bookmark active listings and manage bookmarked roles on the **Saved Jobs** page (`/jobs/saved/`).
- Submit job applications (`/jobs/<job_id>/apply/`) with an optional cover note and an optional application-specific PDF resume (or automatically reuse your saved profile PDF resume).
- Prevent duplicate applications per job (`UniqueConstraint` on `(job, applicant)`).
- Track application history and filter submissions by status on both the dashboard and the dedicated **Applied Jobs** page (`/jobs/applied/`).

### Employer Features

- Register and log in as an Employer to access the protected **Employer Dashboard** (`/accounts/dashboard/employer/`).
- Manage company profile details (Employer Name, Company Name, Company Description, Location, and Phone).
- Create, edit, toggle active status, and delete job postings (`/jobs/create/`, `/jobs/<job_id>/edit/`, `/jobs/<job_id>/delete/`), with ownership checks ensuring employers can only manage their own listings.
- Review applicants scoped strictly to the employer's own jobs, filter by job posting or application status, view qualification/skills/cover notes, view or download applicant PDF resumes (`/jobs/applications/<application_id>/resume/`), and update application statuses (`Applied`, `Shortlisted`, `Rejected`, `Selected`).

### Admin Features

- **In-Portal Admin Dashboard (`/accounts/dashboard/admin/`)** *(restricted to authenticated `is_staff` / superuser accounts)*:
  - Platform summary metrics: **Total Users** (with staff count), **Employers**, **Job Seekers**, **Total Jobs** (with active/inactive breakdown), and **Applications**.
  - Recent Registered Users and Recent Job Postings overview panels (with links to inspect both active and inactive jobs or filter applications by job).
  - Full **Application Management** across all employers: search by applicant name, email, job title, or company; filter by job posting or status pills; view/download applicant PDF resumes; inspect timeline history; and update application statuses.
- **Django Admin Panel (`/admin/`)**:
  - `UserProfileAdmin`: search and filter profiles by role and registration date.
  - `JobAdmin`: filter jobs by type, active status, and posted date.
  - `JobApplicationAdmin`: view applicant name, email, job title, company, application date, status, and authorized `View Resume` / `Download` links; search by applicant name/email or job title/company; filter by status and application date hierarchy; inline status editing, bulk status actions, and read-only `ApplicationStatusHistoryInline`.
  - `SavedJobAdmin`: search and filter saved job bookmarks by user, job title, company, and saved timestamp.

---

## Technologies Used

| Layer | Technology |
| --- | --- |
| **Backend Framework** | Python 3, Django `6.1.1` |
| **Database** | SQLite (`db.sqlite3`) |
| **Frontend & Styling** | HTML5, CSS3 (`static/css/style.css`), JavaScript (`static/js/main.js`), Bootstrap `5.3.3`, Bootstrap Icons `1.11.3`, Google Fonts (`Inter`) |
| **Dependencies** | `Django==6.1.1`, `asgiref==3.12.1`, `sqlparse==0.6.0`, `tzdata==2026.3` |

---

## Project Folder Structure

```text
job_portal_online/
├── CareerConnect/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_userprofile_location_userprofile_phone_and_more.py
│   │   └── 0003_userprofile_company_description_and_more.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── decorators.py
│   ├── files.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   ├── validators.py
│   └── views.py
├── jobs/
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_seed_sample_jobs.py
│   │   ├── 0003_job_experience_rename_created_at_posted_date.py
│   │   ├── 0004_populate_job_experience.py
│   │   ├── 0005_jobapplication_cover_note_jobapplication_resume.py
│   │   ├── 0006_jobapplication_status_updated_at_and_more.py
│   │   └── 0007_savedjob.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── templates/
│   ├── accounts/
│   │   ├── access_denied.html
│   │   ├── admin_dashboard.html
│   │   ├── employer_dashboard.html
│   │   ├── job_seeker_dashboard.html
│   │   ├── login.html
│   │   └── register.html
│   ├── jobs/
│   │   ├── _job_card.html
│   │   ├── _status_history.html
│   │   ├── applied_jobs.html
│   │   ├── apply_job.html
│   │   ├── job_confirm_delete.html
│   │   ├── job_detail.html
│   │   ├── job_form.html
│   │   ├── job_list.html
│   │   └── saved_jobs.html
│   ├── base.html
│   └── home.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── media/
│   ├── application_resumes/
│   └── resumes/
├── .env.example
├── .gitignore
├── db.sqlite3
├── manage.py
├── README.md
└── requirements.txt
```

---

## Installation Instructions

1. **Navigate to the project root directory:**

   ```bash
   cd job_portal_online
   ```

2. **Create and activate a virtual environment:**

   - **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt):**
     ```cmd
     python -m venv venv
     venv\Scripts\activate.bat
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

---

## Environment Configuration

1. **Create your local `.env` file from the template** (`.env` is ignored by Git):

   - **Windows (PowerShell):**
     ```powershell
     Copy-Item .env.example .env
     ```
   - **macOS / Linux:**
     ```bash
     cp .env.example .env
     ```

2. **Generate a strong `DJANGO_SECRET_KEY`** and paste it into `.env`:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. Review `.env.example` for optional `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, and HTTPS security settings (`DJANGO_DEBUG=False` requires `DJANGO_SECRET_KEY` and enforces secure cookies, SSL redirect, and HSTS).

---

## Database Migration Commands

Run migrations to initialize or update the SQLite schema and load the seeded sample jobs:

```bash
python manage.py makemigrations
python manage.py migrate
```

To inspect migration status or validate Django configuration:

```bash
python manage.py showmigrations
python manage.py check
```

---

## How to Run the Project

1. **Create an administrator (superuser) account** *(to access `/accounts/dashboard/admin/` and `/admin/`)*:

   ```bash
   python manage.py createsuperuser
   ```

2. **Start the Django development server:**

   ```bash
   python manage.py runserver
   ```

3. **Access the portal in your browser:**

   - **Home Page:** `http://127.0.0.1:8000/`
   - **Browse Active Jobs:** `http://127.0.0.1:8000/jobs/`
   - **Saved Jobs (Job Seeker):** `http://127.0.0.1:8000/jobs/saved/`
   - **Applied Jobs (Job Seeker):** `http://127.0.0.1:8000/jobs/applied/`
   - **User Registration:** `http://127.0.0.1:8000/accounts/register/`
   - **User Login:** `http://127.0.0.1:8000/accounts/login/`
   - **Role-Based Dashboard Redirect:** `http://127.0.0.1:8000/accounts/dashboard/`
   - **In-Portal Admin Dashboard:** `http://127.0.0.1:8000/accounts/dashboard/admin/`
   - **Django Admin Interface:** `http://127.0.0.1:8000/admin/`

4. **Run checks and the automated test suite:**

   ```bash
   python manage.py check
   python manage.py test -v 2
   ```

---

## Future Enhancements

Planned roadmap features for upcoming development phases (not yet implemented in the current release):

- Pagination (`Paginator`) for `/jobs/` and large dashboard tables.
- Admin job posting approval and rejection workflow (`Pending` / `Approved` / `Rejected` moderation states).
- Advanced job search filters for job category, salary range, and structured experience levels.
- Extended Job Seeker profile completion with structured education records, work experience entries, and a completion progress meter.
- Interview scheduling between Employers and shortlisted applicants.
- Automated email notification triggers for new job applications and application status updates (environment-backed `MAILERS` / SMTP settings scaffolding is already configured).
- Interactive dashboard charts and hiring analytics.

---

## Author

- **Hema Leelavathi** — [hemaleelavathi2257@gmail.com](mailto:hemaleelavathi2257@gmail.com)
