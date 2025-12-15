#!/bin/bash

# Script to package only the essential files for submission
echo "Creating minimal package for submission..."

# Create a temporary directory for the minimal package
mkdir -p ../capstone_minimal_temp

# Copy only the absolutely essential files and directories
cp -r app ../capstone_minimal_temp/
cp -r backend ../capstone_minimal_temp/
cp main.py ../capstone_minimal_temp/
cp requirements.txt ../capstone_minimal_temp/

# Remove test-related files from backend
rm -rf ../capstone_minimal_temp/backend/tests

# Remove __pycache__ directories if any exist
find ../capstone_minimal_temp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create the final minimal zip file
cd ..
rm -f capstone_minimal.zip
zip -r capstone_minimal.zip capstone_minimal_temp

# Clean up temporary directory
rm -rf capstone_minimal_temp

echo "Minimal submission package created: capstone_minimal.zip"
echo "Size:"
du -h capstone_minimal.zip