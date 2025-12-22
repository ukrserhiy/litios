# LITI Open Source - Self-hosted Psycholinguistic HR Analysis Tool
# Dockerfile for Google Cloud Run or self-hosted deployment
# Uses SQLite for persistent storage

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Expose port (Cloud Run uses PORT env variable)
EXPOSE 8080

# Set default PORT if not provided
ENV PORT=8080

# Run the application with gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 server:app
