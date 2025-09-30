#!/bin/bash

set -e

echo "Starting the application..."
echo "Environment: ${ENV:-development}"

# Add your application startup commands here
source venv/bin/activate
pip install -r requirements.txt
python unified_messaging_server/manage.py migrate
python unified_messaging_server/manage.py runserver 8080

echo "Application started successfully!"