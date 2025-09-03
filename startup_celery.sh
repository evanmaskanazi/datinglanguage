#!/bin/bash
echo "Starting Celery Worker for Table for Two..."

# Wait for main app to be ready
echo "Waiting for main application..."
sleep 10

# Start Celery worker with optimized settings
echo "Starting Celery worker..."
exec celery -A celery_app worker \
    --loglevel=INFO \
    --concurrency=2 \
    --max-tasks-per-child=100 \
    --time-limit=300 \
    --soft-time-limit=240 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
