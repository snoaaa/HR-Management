# HR Management

A Django + React (Vite) full-stack project.

---

## Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

Create the PostgreSQL database:

```sql
CREATE DATABASE hr_management;
```

Update the database credentials in `backend/hrms_backend/settings.py` if needed.

```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start server
python manage.py runserver
```

API is available at `http://127.0.0.1:8000/api/`

---

## Frontend Setup

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

App is available at `http://localhost:5173/`