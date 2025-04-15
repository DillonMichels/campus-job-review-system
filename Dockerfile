# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install system dependencies required for Ollama
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

RUN ollama --version

# Copy the requirements file into the container at /app
COPY requirements.txt /app/requirements.txt



# Install system packages needed for Pillow
RUN apt-get update && apt-get install -y \
    libjpeg-dev zlib1g-dev libpng-dev gcc \
    && rm -rf /var/lib/apt/lists/*
    
# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install --upgrade ollama  # Explicitly upgrade ollama
RUN pip install pytest coverage

# Copy the rest of the application code to /app
COPY . /app

# Set environment variables
ENV FLASK_APP=crudapp.py
ENV FLASK_ENV=development

# Initialize the database
RUN flask db init || true
RUN flask db migrate -m "entries table" || true
RUN flask db upgrade || true

# Expose port 5000
EXPOSE 5000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run the application
ENTRYPOINT ["sh","/app/entrypoint.sh"]