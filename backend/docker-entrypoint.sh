#!/bin/sh
# Start-up of the HRMS container: wait for the database, apply the
# migrations, optionally load the demonstration data, then serve on $PORT.
set -e

echo "[hrms] Applying database migrations…"
tries=0
until python manage.py migrate --noinput; do
  tries=$((tries + 1))
  if [ "$tries" -ge 15 ]; then
    echo "[hrms] The database is still unreachable after $tries attempts." >&2
    exit 1
  fi
  echo "[hrms] Database not ready yet, new attempt in 3 s ($tries/15)…"
  sleep 3
done

if [ "${SEED_DEMO:-false}" = "true" ]; then
  # Demo accounts and data; skipped once users exist so restarts stay fast.
  if python manage.py shell -c "from django.contrib.auth import get_user_model as g; import sys; sys.exit(0 if g().objects.exists() else 1)"; then
    echo "[hrms] Data already present: demonstration seed skipped."
  else
    echo "[hrms] Loading the demonstration data…"
    python manage.py seed_data
  fi
fi

echo "[hrms] Listening on port ${PORT:-8000}"
exec gunicorn hrms_backend.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout "${WEB_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
