FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Pre-install CPU version of PyTorch to save massive amounts of disk space
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

# Copy application code
COPY . .

# Create data directories and set permissions
RUN mkdir -p data/uploads \
    && chown -R appuser:appgroup /app \
    && chmod -R 755 /app

# Switch to non-root user
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:5000", "--timeout=600", "app:create_app()"]
