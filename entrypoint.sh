#!/bin/bash
echo "Starting Ollama..."
ollama serve &> /proc/1/fd/1 &

sleep 15

echo "Pulling deepseek-r1:1.5b model..."
ollama pull deepseek-r1:1.5b

sleep 10

echo "Starting Flask application..."
flask run -h 0.0.0.0 -p 5000