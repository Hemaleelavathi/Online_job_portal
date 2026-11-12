# CareerConnect — Online Job Portal

**CareerConnect** is a responsive full-stack web application built with **Python**, **Django**, **SQLite**, **HTML5/CSS3**, **JavaScript**, and **Bootstrap 5** that connects Job Seekers, Employers, and Platform Administrators through dedicated role-based workflows. The portal supports user registration and login, responsive job discovery and filtering, **Saved Jobs** bookmarking, job applications with duplicate prevention, private PDF resume validation and authorized downloads, application status tracking with audit history, an in-portal Admin Dashboard, Django Admin customization, and environment-based secret management.

---

## Table of Contents

- [Main Features](#main-features)
- [Role-Based Features](#role-based-features)
  - [Job Seeker Features](#job-seeker-features)
  - [Employer Features](#employer-features)
  - [Admin Features](#admin-features)
- [Secure Resume Handling & Environment Configuration](#secure-resume-handling--environment-configuration)
- [Technologies Used](#technologies-used)
- [Project Folder Structure](#project-folder-structure)
- [Installation & Setup (Windows PowerShell)](#installation--setup-windows-powershell)
- [Configuring `.env` Safely](#configuring-env-safely)
- [Database Migration & Server Commands](#database-migration--server-commands)
- [GitHub Repository Information](#github-repository-information)
- [Future Enhancements](#future-enhancements)
- [Author](#author)

---

## Main Features

- **Role-Based Authentication & Access Control**
  - Registration with Full Name, Email, Password, Confirm Password, and Role selection (`Job Seeker` or `Employer`).
  - Case-insensitive duplicate email checks, Django password hashing/validation, and automatic `UserProfile` creation.
  - Email-and-password authentication with role-based dashboard routing (`/accounts/dashboard/`).
  - POST-only logout, CSRF protection on all state-changing forms, and custom `403 Access Denied` handling via `@role_required` and `@staff_required`.
- **Responsive Frontend & Job Discovery**
  - High-contrast dark blue/indigo hero section with keyword and location search, quick filter tags, live platform counts, and role-aware call-to-action buttons (`Home` `/`).
  - Responsive navigation bar (`navbar-expand-md`) displaying horizontal links on desktop/tablet screens and an interactive hamburger menu on mobile viewports, backed by progressive JavaScript enhancements (`static/js/main.js`).
  - Dedicated **Find Jobs** page (`/jobs/`) with keyword search (`q` across title, company, description, job type, skills, and experience) plus `location` and `job_type` (`Full-Time`, `Part-Time`, `Remote`, `Hybrid`, `Contract`) filters.
  - Pre-seeded sample job postings loaded via Django data migrations (`jobs/migrations/0002_seed_sample_jobs.py` and `0004_populate_job_experience.py`).
- **Saved Jobs Bookmarking**
  - Bookmark active jobs and manage saved opportunities on `/jobs/saved/` via the `SavedJob` model.
  - Duplicate bookmark prevention enforced both in view logic (`get_or_create`) and at the database level (`UniqueConstraint` on `(user, job)`).
- **Application Tracking & Chronological History**
  - Four application statuses: **Applied**, **Shortlisted**, **Rejected**, and **Selected**.
  - Automatic transition history recorded in `ApplicationStatusHistory` (capturing status, timestamp, and author of each change).

---

## Role-Based Features

### Job Seeker Features

- Protected **Job Seeker Dashboard** (`/accounts/dashboard/job-seeker/`) with live counters for Available Jobs, Saved Jobs, and Applied Jobs.
- View and update profile information: Full Name, Phone, Location, Highest Qualification, Comma-separated Skills, and PDF Resume (with client-side file extension/size hints and server-side validation).
- Securely preview (`?inline=1`) or download your own profile resume via `/accounts/profile/resume/`.
- Save and unsave active jobs directly from job cards, job detail pages, or `/jobs/saved/`.
- Submit applications (`/jobs/<job_id>/apply/`) with an optional cover note and custom PDF resume (or automatically reuse your uploaded profile resume), with duplicate application prevention (`UniqueConstraint` on `(job, applicant)`).
- View application statuses, status filter pills, and timeline history on both the dashboard and **My Applied Jobs** (`/jobs/applied/`).

### Employer Features

- Protected **Employer Dashboard** (`/accounts/dashboard/employer/`) for managing company profile details (Employer Name, Company Name, Company Description, Location, and Phone).
- Create, edit, activate/deactivate, and delete job postings (`/jobs/create/`, `/jobs/<job_id>/edit/`, `/jobs/<job_id>/delete/`), strictly scoped to jobs owned by the logged-in Employer.
- Review applicants for your own jobs, filter by job posting or application status, view applicant qualifications/skills/cover notes, view or download applicant PDF resumes (`/jobs/applications/<application_id>/resume/`), and update application statuses.

### Admin Features

- **In-Portal Admin Dashboard (`/accounts/dashboard/admin/`)** *(restricted to `is_staff` / superusers)*:
  - Platform summary metrics: **Total Users** (with staff count), **Employers**, **Job Seekers**, **Total Jobs** (active vs. inactive), and **Applications**.
  - Recent Registered Users and Recent Job Postings overview cards.
  - Cross-employer **Application Management** with search (applicant name, email, job title, company), job/status filters, timeline inspection, resume download/preview, and status updates.
- **Django Admin Panel (`/admin/`)**:
  - `UserProfileAdmin`, `JobAdmin`, `JobApplicationAdmin` (clickable resume links, search, status/date filters, inline status updates, bulk actions, and `ApplicationStatusHistoryInline`), and `SavedJobAdmin`.

---

## Secure Resume Handling & Environment Configuration

- **Private Resume Access Control**
  - Direct unauthenticated requests under `/media/` are disabled in [CareerConnect/urls.py](CareerConnect/urls.py) (`404` even when `DEBUG=True`).
  - Uploaded PDFs are validated by `validate_pdf_resume` (`accounts/validators.py`) for `.pdf` extension, `%PDF-` header bytes, and a 5 MB maximum file size.
  - Resumes are served exclusively through [accounts/files.py](accounts/files.py) with `Content-Type: application/pdf` and `X-Content-Type-Options: nosniff`:
    - `/accounts/profile/resume/` serves only the authenticated user's own profile resume.
    - `/jobs/applications/<application_id>/resume/` restricts access to the hiring Employer, the applicant, or staff/admin users (`403 Forbidden` otherwise).
  - Public job detail views do not expose private employer email addresses.
- **Environment Variable Hardening**
  - [CareerConnect/settings.py](CareerConnect/settings.py) loads configuration from a local `.env` file (or OS environment variables) and contains **no hardcoded `SECRET_KEY` fallback**.
  - HTTP-only session/CSRF cookies, `X_FRAME_OPTIONS = 'DENY'`, `SECURE_CONTENT_TYPE_NOSNIFF = True`, and automatic HTTPS/HSTS hardening when `DJANGO_DEBUG=False`.
  - Django `MAILERS` and SMTP credentials are configurable via environment variables (`DJANGO_EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`).

---

## Technologies Used

| Layer | Technology |
| --- | --- |
| **Backend** | Python 3, Django `6.1.1` |
| **Database** | SQLite (`db.sqlite3`) |
| **Frontend** | HTML5, CSS3 (`static/css/style.css`), JavaScript (`static/js/main.js`), Bootstrap `5.3.3`, Bootstrap Icons `1.11.3`, Google Fonts (`Inter`) |
| **Python Packages** | `Django==6.1.1`, `asgiref==3.12.1`, `sqlparse==0.6.0`, `tzdata==2026.3` |

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
├── .env.example
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```

*(Runtime artifacts such as `.env`, `db.sqlite3`, `media/`, `staticfiles/`, and `backups/` are excluded from Git tracking via `.gitignore`.)*

---

## Installation & Setup (Windows PowerShell)

1. **Clone the repository and open the project directory:**

   ```powershell
   git clone https://github.com/Hemaleelavathi/Online_job_portal.git
   cd Online_job_portal
   ```

   *(If you already have the local `job_portal_online` workspace folder, `cd` directly into it.)*

2. **Create and activate a Python virtual environment:**

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   *(If PowerShell blocks script activation, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once.)*

3. **Install dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

---

## Configuring `.env` Safely

`CareerConnect/settings.py` requires `DJANGO_SECRET_KEY` (or `SECRET_KEY`) from `.env` or OS environment variables and refuses to start with empty or placeholder keys.

1. **Copy the placeholder template to a local `.env` file:**

   ```powershell
   Copy-Item .env.example .env
   ```

2. **Generate a unique cryptographic secret key:**

   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. **Update `.env` locally (never commit or share this file):**
   - Replace the placeholder value of `DJANGO_SECRET_KEY` in `.env` with the newly generated key.
   - Keep `DJANGO_DEBUG=True` and `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost` for local development.
   - Set `DJANGO_DEBUG=False` and configure real `DJANGO_ALLOWED_HOSTS` and SMTP settings (`DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`) before deploying to production.
   - Verify `.env` is ignored before any commit:

   ```powershell
   git check-ignore -v .env
   ```

---

## Database Migration & Server Commands

1. **Apply migrations and load seeded sample jobs:**

   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Verify Django configuration and migration status:**

   ```powershell
   python manage.py showmigrations
   python manage.py check
   ```

3. **Create an administrator account *(optional, for `/accounts/dashboard/admin/` and `/admin/`)*:**

   ```powershell
   python manage.py createsuperuser
   ```

4. **Run the development server:**

   ```powershell
   python manage.py runserver
   ```

5. **Run the full automated test suite (63 tests):**

   ```powershell
   python manage.py test -v 2
   ```

6. **Key portal URLs:**
   - **Home:** `http://127.0.0.1:8000/`
   - **Find Jobs:** `http://127.0.0.1:8000/jobs/`
   - **Saved Jobs (Job Seeker):** `http://127.0.0.1:8000/jobs/saved/`
   - **Applied Jobs (Job Seeker):** `http://127.0.0.1:8000/jobs/applied/`
   - **Register / Login:** `http://127.0.0.1:8000/accounts/register/` | `http://127.0.0.1:8000/accounts/login/`
   - **Role Dashboard:** `http://127.0.0.1:8000/accounts/dashboard/`
   - **Admin Dashboard / Django Admin:** `http://127.0.0.1:8000/accounts/dashboard/admin/` | `http://127.0.0.1:8000/admin/`

---

## GitHub Repository Information

- **Repository URL:** `https://github.com/Hemaleelavathi/Online_job_portal.git`
- **Default Branch:** `main`
- **Safe Commit Checklist:**
  - Confirm `git status` does not list `.env` or `db.sqlite3`.
  - Commit `.env.example` (contains placeholder settings only) and `.gitignore`, never `.env`.

---

## Future Enhancements

Planned roadmap features not yet implemented in the current release:

- Pagination (`Paginator`) for `/jobs/` and large dashboard lists.
- Admin moderation workflow (`Pending` / `Approved` / `Rejected`) for submitted job postings.
- Advanced search filters for job category, salary range, and structured experience levels.
- Extended Job Seeker profile completion with structured education records, work experience entries, and a completion progress indicator.
- Interview scheduling between Employers and shortlisted candidates.
- Automated email notifications on job applications and status updates (SMTP / `MAILERS` environment configuration is already in place).
- Interactive dashboard charts and hiring analytics.

---

## Author

- **Hema Leelavathi** — [hemaleelavathi2257@gmail.com](mailto:hemaleelavathi2257@gmail.com)
