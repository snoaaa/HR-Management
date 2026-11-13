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

It creates the demo accounts (password `password123`): `admin` (system administrator, access to everything), `hrmanager` (HR manager), `payroll` (payroll officer), `accountant`, `employee1`, `employee2`, plus an active contract with bank details for every employee.

It then runs `python manage.py seed_demo`, a complete demonstration company in a Cameroonian context ("Saint Jean Services SA", Douala). The data goes through the services of the application, so it obeys the same rules as the screens:

| Module | Demonstration data |
|---|---|
| Organisation | Company identity (RCCM, NIU, CNPS, contacts), 4 sites (Douala, Yaoundé, Garoua, Bafoussam), 5 cost centres, 8 departments with their heads, 23 positions, 9 categories (Cat. 2 → Cat. 12) |
| Employees | About 50 complete records (identity, region, ID card, CNPS, NIU, bank, family, education and experience), 28 user accounts (`firstname.surname`, password `password123`) |
| Contracts | Permanent and fixed-term contracts activated, one fixed-term contract ending within a month (deadline alert), one employee on trial |
| Payroll | Transport / housing / responsibility / representation allowances, loans and advances, payroll of the last 3 months calculated and validated (2 paid and posted), current month opened with bonuses |
| Accounting | Payroll, payment and settlement entries (CNPS, tax, CFC, FNE, council, CRTV), department budgets |
| Attendance & planning | Clockings of the previous and current months, computed days, approved overtime, missions, a published shift timetable and a draft one |
| Leave | Approved, pending (in the approval inbox) and refused requests |
| Careers | Applied promotion, salary revision waiting for approval, approved transfer, warning, draft acting position |
| Training, recruitment, evaluation | Skills, plan with 7 sessions and results, training needs; needs, 4 job offers and applications at every stage; 2025 (closed) and 2026 (open) evaluation campaigns |
| Documents | Work certificates and presence attestations issued, record corrections pending |

The demonstration seed is idempotent; one step can be re-run on a seeded database with `python manage.py seed_demo --only payroll,budgets`. Use `python manage.py seed_data --base-only` for the accounts without the demonstration data.

The reference data of the modules (leave types, entitlement rule, public holidays, standard schedule, shifts, payroll parameters, scales, contributions and taxes, salary elements, document templates, approval circuits, permission matrix) is loaded by the migrations and is then edited from the application, never in the code.

### Daily job

Deadline alerts (end of fixed-term contracts and trial periods, expiring documents, retirement, payroll and declaration due dates) and the closing of ended contracts run with:

```bash
python manage.py send_deadline_alerts
```

It also applies the career acts reaching their date, escalates unanswered requests, sends the scheduled reports and makes the daily backup (setting `AUTO_BACKUP`). Schedule it once a day (Windows Task Scheduler or cron).

Other commands: `python manage.py backup_data`, `python manage.py restore_backup <file> [--confirm]`, `python manage.py apply_retention [--dry-run]` (anonymisation of old archived records, BN-177). HR managers can also trigger it with `POST /api/notifications/run-alerts/`.

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
| `/api/accounting/` | OHADA (SYSCOHADA) payroll entries, books, mapping, financial years (M-13) | 10 |
| `/api/careers/` | Promotions, transfers, discipline, departures, structure history, org chart (M-08, BN-06/07) | 11 |
| `/api/reports/` | Dashboards, HR indicators, custom and scheduled reports (M-15) | 12 |
| `/api/evaluation/` | Evaluation campaigns, objectives, scores, proposals (M-10) | 14 |
| `/api/recruitment/` | Needs, offers, applications, hiring, onboarding; public careers page `/careers` (M-03) | 14 |
| `/api/training/` | Skills, needs, plan, sessions, results, costs (M-09) | 15 |
| `/api/imports/`, `/api/backups/` | Initial data import with control report, backups and restoration (BN-179, BN-183) | 15 |

Payroll settings marked "to validate" in `backend/payroll/reference_data.py` (minimum wage, seniority bonus, severance scale, overtime tiers) must be confirmed by the HR and payroll department before the first real payroll (open point OP-01). The Cameroon Labour Code rules are applied: leave counted in jours ouvrables (art. 89), 2.5 days a month under 18 and extra days for mothers (art. 90), weekly overtime tiers (decree 68/DF/249), fixed-term contracts limited to 2 years (art. 25) and trial period maximum (art. 28). The bank transfer file uses a generic CSV layout until the bank format is known (OP-03).

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

## Running with Docker (single address, port 8000)

One image contains everything: the Django backend serves the API under `/api/` and the
built React application at the root URL.

```bash
cp .env.docker.example .env        # set SECRET_KEY and POSTGRES_PASSWORD (both mandatory)
docker compose up -d --build       # application on port 8000
```

The files are prepared for **https://agile.emakotech.cloud**:

- If the server already has a reverse proxy or hosting platform handling HTTPS, point
  `agile.emakotech.cloud` to port 8000 (it must forward the `Host` and `X-Forwarded-Proto` headers).
- If nothing handles HTTPS yet, start the bundled Caddy proxy as well; it obtains the certificate
  automatically (DNS of the domain must point to the server, ports 80 and 443 open):
  `docker compose --profile https up -d --build`
- Local test without HTTPS: set `BEHIND_HTTPS_PROXY=false` in `.env` and open http://localhost:8000.
- `SEED_DEMO=true` in `.env` loads the demonstration accounts and data on the first start.
- Data is kept in the volumes `hrms_db` (PostgreSQL), `hrms_media` (uploaded files) and `hrms_backups`.
- Files: `Dockerfile`, `docker-compose.yml`, `Caddyfile`, `.dockerignore`, `.env.docker.example`,
  `backend/docker-entrypoint.sh`.

The same single-address mode works without Docker: run `npm run build` in `frontend/`, then start
the backend; when `frontend/dist` exists, Django serves it at `/` (requires `whitenoise`, listed in
`backend/requirements.txt`). During development, `npm run dev` still works as before.

## Design system (13 November 2026)

The interface takes its colours from the logo (`logo.png`, app icons in `frontend/public/brand/`):
orange for actions, navy for navigation and headings, red as an accent, flat colours only.
Tokens and component classes live in `frontend/src/styles/design-system.css`; the Tailwind scales
(`brand`, `gray`, `accent`) are in `frontend/src/index.css`. Printed documents (`backend/core/pdf.py`)
and Excel exports use the same navy and orange.

## Implemented on 10 October 2026

Work done in one day on the `elie` branch, from the expression of need (`docs/HRMS_Expression_of_Need.pdf`), following the Cameroon Labour Code.

**Planning and set-up**
- Sprint plan (sprints 1 → 15) built from the expression of need, starting from what was not yet done.
- Database seeding, employee record of the HR manager and Product Owner (Elie Makoda Kowo) linked to the `hrmanager` account.

**Backend – every module M-01 → M-18 (sprints 1 → 15)**
- Organisation, structure history and org chart; employee records with history, export and corrections requested by the employee; contracts with amendments, renewals, suspensions, terminations and final settlement.
- Attendance (calendars, schedules, clockings, badge import, overtime approval, consolidation and locking), leave (balances in jours ouvrables, minors and mothers, approvals, interruption and postponement, leave allowance), shift planning with conflicts and exchanges.
- Generic payroll engine (dated parameters, scales, formulas) with the Cameroonian payroll (CNPS, IRPP, CAC, CFC, FNE, CRTV, TDL), payroll cycle, anomalies, comparison, reversal, simulation, declarations, payment orders, provisions, back pay.
- OHADA (SYSCOHADA) accounting of the payroll: balanced and immutable entries, payment and settlement entries, reversal, books, reconciliation, analysis vs budget, financial statement items, export to the accounting software.
- Careers (promotions, transfers, salary revisions, discipline, departures), dashboards and reports, evaluation campaigns, recruitment with a public careers page, training (skills, plan, sessions, certificates).
- Approval circuits and inbox, notifications and daily job, permission matrix per module and action, data perimeter, salary confidentiality, two-factor authentication, data import with control report, backups and restoration, personal data and retention.

**Frontend**
- Complete redesign in the Odoo colours (purple `#714B67`, teal `#00A09D`) with SAP accents, flat colours only (no gradients) and a new logo.
- A screen for every module, personal space for the employees (time, payslips, documents, evaluations, training) and a public careers page.
- No identifier is ever typed: every relation (employee, department, position, period, account…) is a picker searched by name.

**Documents, exports and data (end of the day)**
- Professional PDF layout for every document: logo and legal identification of the organisation in the header, purple titles and tables, teal accents, alternating rows, totals, footer with the page numbers.
- Logo of the organisation uploaded from Organisation → Company identity (PNG / JPEG, 2 MB) and printed on every document; new company contact fields (city, P.O. box, telephone, e-mail, website, title of the representative).
- Accounting → Documents: journal book, general ledger, trial balance, personnel and social bodies balances, analysis of the personnel expenses, financial statement items, list of the entries in PDF / Excel / CSV; accounting voucher of an entry and payroll / accounting reconciliation in PDF.
- PDF and Excel export of every list of the application (`POST /api/exports/table/`), Excel files in the same colours.
- Employee record: title, maiden name, ID issue date and place, blood group, highest diploma, languages, disability, city, region, P.O. box, professional telephone, CNPS registration date; computed age and number of children; complete employee record in PDF.
- Demonstration data for every module (see "Seeding the Database").
- The system administrator has access to every module and every action.
- Fixed: the payroll of an employee under fixed-term contract failed (end date in the payslip snapshot); editing an employee with a photo failed.

## Branching Strategy & Workflow

Please see [BRANCHING_STRATEGY.md](./BRANCHING_STRATEGY.md) for a detailed explanation of our Agile branching strategy, branch naming conventions, and the Pull Request workflow.

# hello team 
everyone should clone and we'll review it on our next spring 