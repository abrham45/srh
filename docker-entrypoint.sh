#!/bin/bash

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."

# Function to check if PostgreSQL is ready
wait_for_postgres() {
    while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
        echo "PostgreSQL is unavailable - sleeping for 2 seconds"
        sleep 2
    done
    echo "PostgreSQL is ready!"
}

# Wait for database
wait_for_postgres

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser if it doesn't exist..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@srh-chatbot.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
" 2>/dev/null || echo "Superuser creation skipped"

# Collect static files (if needed)
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Static files collection skipped"

# Start the application
echo "Starting SRH Chatbot..."
exec "$@" 