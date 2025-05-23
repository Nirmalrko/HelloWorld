# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
# ENV FLASK_ENV=production # Optional: can be set here or in Cloud Run service definition
# PORT is automatically set by Cloud Run, but can be defaulted here for local Docker runs
ENV PORT 8080
# Set FLASK_SECRET_KEY in Cloud Run service environment variables, not here.
# For local Docker runs, you can pass it with -e FLASK_SECRET_KEY="..."

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by Python packages (if any)
# For example, if a package needed gcc or other build tools:
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
# For now, our requirements (Flask, pandas, openpyxl, gunicorn) don't seem to need extra system deps.

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# This includes app.py, database_setup.py, store.db, and the static/ and templates/ folders
COPY . .

# Make port 8080 available to the world outside this container
# (Cloud Run uses the PORT env var, which we've defaulted to 8080)
EXPOSE 8080

# Define the command to run the application using Gunicorn
# Gunicorn will listen on the port specified by the PORT environment variable.
# Number of workers can be adjusted based on expected load and available CPU.
# For Cloud Run, typically 1 worker with multiple threads is a good starting point.
# Cloud Run will send SIGTERM for shutdown. Default timeout is 10s.
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 0 app:app
