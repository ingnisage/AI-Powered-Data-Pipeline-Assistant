#!/bin/bash
# Render startup script

echo "Starting AI Workbench on Render..."

# Export environment variables
echo "Exporting environment variables..."
export RENDER=true
export ENVIRONMENT=production

# Show current directory and files
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if running as frontend or backend based on PORT
if [ "$PORT" = "8000" ] || [ -z "$PORT" ]; then
    echo "Starting backend service..."
    python -m backend.main --port ${PORT:-8000}
else
    echo "Starting frontend service on port $PORT..."
    streamlit run app/app.py --server.port $PORT --server.address 0.0.0.0
fi