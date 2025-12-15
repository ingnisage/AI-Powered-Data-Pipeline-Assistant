#!/bin/bash

# Script to package the project for submission without unnecessary files
echo "Creating clean package for submission..."

# Create a temporary directory for the clean package
mkdir -p ../capstone_submission_temp

# Copy only the essential files and directories
cp -r app ../capstone_submission_temp/
cp -r backend ../capstone_submission_temp/
cp -r Supabase ../capstone_submission_temp/
cp main.py ../capstone_submission_temp/
cp requirements.txt ../capstone_submission_temp/
cp README.md ../capstone_submission_temp/
cp CONSOLIDATED_DOCUMENTATION.md ../capstone_submission_temp/
cp SEARCH_FUNCTIONALITY.md ../capstone_submission_temp/

# Create the final zip file
cd ..
rm -f capstone_submission.zip
zip -r capstone_submission.zip capstone_submission_temp

# Clean up temporary directory
rm -rf capstone_submission_temp

echo "Submission package created: capstone_submission.zip"
echo "This package excludes the virtual environment and other unnecessary files."