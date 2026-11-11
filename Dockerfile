
FROM python:3.11-slim

# Set working directory
WORKDIR /srv

# Prevent Python from creating unnecessary cache files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./app/
COPY kb/ ./kb/

# Create directories for database and vector storage
RUN mkdir -p /srv/data

# Expose the application port
EXPOSE 8000

# Start FastAPI using Render's assigned port
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
