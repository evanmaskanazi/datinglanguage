FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Convert line endings and make scripts executable
RUN dos2unix startup.sh && chmod +x startup.sh
RUN dos2unix startup_celery.sh && chmod +x startup_celery.sh

# Create necessary directories
RUN mkdir -p static templates logs

# Expose port
EXPOSE 5000

# Default command
CMD ["./startup.sh"]
