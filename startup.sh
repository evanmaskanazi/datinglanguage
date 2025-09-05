#!/bin/bash

echo "Starting Table for Two Dating App..."

# Print environment info
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"

# Check for required files
echo ""
echo "Checking application files:"
for file in dating_backend.py init_db.py; do
    if [ -f "$file" ]; then
        echo "✓ Found: $file"
    else
        echo "✗ Missing: $file"
    fi
done

# Initialize database
if [ ! -z "$DATABASE_URL" ]; then
    echo ""
    echo "Initializing database..."
    python init_db.py
    
    # Run migrations
    echo "Running database migrations..."
#    flask db upgrade
else
    echo ""
    echo "WARNING: DATABASE_URL not set, skipping database initialization"
fi

# Start the application
echo ""
echo "Starting Gunicorn with gevent workers..."
exec gunicorn dating_backend:app \
    --bind 0.0.0.0:${PORT:-5000} \
    --workers ${WORKERS:-2} \
    --worker-class gevent \
    --worker-connections 1000 \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
