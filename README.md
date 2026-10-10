# HR Management

A decoupled full-stack application utilizing Django for the backend API and React (Vite) for the frontend.

## Code Structure

The repository is strictly divided into two distinct environments to enforce separation of concerns:

- `backend/`
  Contains the Django application. It provides a RESTful API and manages database interactions via a remote PostgreSQL instance. Configuration is strictly managed through environment variables (`.env`) following 12-factor app principles. 

- `frontend/`
  Contains the React application built with Vite. It consumes the backend REST API via Axios. The backend API URL is injected via environment variables at build time.

## Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL database instance

## Configuration

Both the frontend and backend rely on environment variables. Do not hardcode credentials or URLs in the source code.

### Backend

Create a `.env` file in the `backend/` directory:

```env
SECRET_KEY=your_django_secret_key
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend

Create a `.env` file in the `frontend/` directory:

```env
VITE_API_URL=http://127.0.0.1:8000/api/
```

## Running the Application

### Backend Setup

Navigate to the backend directory and set up the Python virtual environment:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:
- Windows: `.\.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Install dependencies and apply database migrations:

```bash
pip install -r requirements.txt
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`.

### Seeding the Database (Initial Data)

If you are setting up the project for the first time, you can populate the database with required test users and organizational structures by running:

```bash
python manage.py seed_data
```

It creates the demo accounts (password `password123`): `admin` (system administrator), `hrmanager` (HR manager), `payroll` (payroll officer), `accountant`, `employee1`, `employee2`, plus an active contract with bank details for every employee.

The reference data of the modules (leave types, entitlement rule, public holidays, standard schedule, shifts, payroll parameters, scales, contributions and taxes, salary elements, document templates, approval circuits, permission matrix) is loaded by the migrations and is then edited from the application, never in the code.

### Daily job

Deadline alerts (end of fixed-term contracts and trial periods, expiring documents, retirement, payroll and declaration due dates) and the closing of ended contracts run with:

```bash
python manage.py send_deadline_alerts
```

Schedule it once a day (Windows Task Scheduler or cron). HR managers can also trigger it with `POST /api/notifications/run-alerts/`.

### Modules of the API

| Prefix | Module | Sprint |
|---|---|---|
| `/api/users/`, `/api/audit-logs/`, `/api/settings/` | Security, permission matrix, audit trail, settings (M-17, M-18) | 1 |
| `/api/organisation/` | Organisation and structure (M-01) | 1 |
| `/api/employees/` | Employee records, history, export (M-02) | 2 |
| `/api/contracts/` | Contracts, amendments, renewals, suspensions, terminations (M-04) | 3 |
| `/api/attendance/` | Calendars, schedules, clockings, overtime, absences (M-05, M-07) | 4, 6 |
| `/api/leave/` | Leave types, balances, requests, approvals (M-06) | 5 |
| `/api/planning/` | Shifts, timetables, conflicts, exchanges (M-07) | 6 |
| `/api/notifications/` | Notifications, approval circuits and inbox (M-16) | 5, 6 |
| `/api/payroll/` | Parameters, elements, periods, payslips, loans, simulation, declarations (M-11, M-12) | 7, 8, 9 |
| `/api/documents/` | Templates, certificates, decisions, issued documents archive (M-12) | 3, 9 |

Payroll settings marked "to validate" in `backend/payroll/reference_data.py` (minimum wage, seniority bonus, severance scale, overtime tiers) must be confirmed by the HR and payroll department before the first real payroll (open point OP-01). The bank transfer file uses a generic CSV layout until the bank format is known (OP-03).

### API Documentation (Swagger)

The project includes an automatically generated interactive OpenAPI (Swagger) documentation. Once the backend server is running, you can explore the API endpoints by navigating to:
- **Swagger UI**: `http://127.0.0.1:8000/api/docs/`
- **Raw Schema**: `http://127.0.0.1:8000/api/schema/`


### Frontend Setup

Open a new terminal session, navigate to the frontend directory, install dependencies, and start the Vite development server:

```bash
cd frontend
npm install
npm run dev
```

The frontend application will be available at `http://localhost:5173/`.

## Branching Strategy & Workflow

Please see [BRANCHING_STRATEGY.md](./BRANCHING_STRATEGY.md) for a detailed explanation of our Agile branching strategy, branch naming conventions, and the Pull Request workflow.

# hello team 
everyone should clone and we'll review it on our next spring 