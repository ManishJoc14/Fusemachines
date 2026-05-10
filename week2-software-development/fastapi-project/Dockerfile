# Base Python image
FROM python:3.12-slim

# Prevent .pyc generation
ENV PYTHONDONTWRITEBYTECODE=1

# Show logs immediately
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy requirements first for Docker cache optimization
COPY requirements ./requirements

# Install production dependencies
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]