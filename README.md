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