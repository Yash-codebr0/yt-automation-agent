FROM python:3.12-slim

# Install ffmpeg and system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# COPY requirements.txt (which will be in build context)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
