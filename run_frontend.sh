#!/bin/bash
# Script to run the frontend with proper environment variables

# Load environment variables from .env file
if [ -f .env ]; then
    # Export only non-comment lines from .env file
    export $(grep -v '^#' .env | xargs)
    echo "Environment variables loaded from .env file"
else
    echo "Warning: .env file not found, using default development settings"
    export ENVIRONMENT=development
    export BACKEND_API_KEY=dev-key-12345
fi

# Run the frontend
streamlit run app/app.py