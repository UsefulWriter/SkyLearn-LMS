#!/bin/bash

# SkyLearn LMS Server Startup Script

echo "🚀 Starting SkyLearn LMS..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is already in use."
    echo "Do you want to kill the existing process? (y/n)"
    read -r response
    if [[ "$response" == "y" ]]; then
        lsof -ti:8000 | xargs kill -9 2>/dev/null
        echo "✅ Killed existing process on port 8000"
        sleep 1
    else
        echo "Please stop the existing process or use a different port."
        exit 1
    fi
fi

# Run migrations if needed
echo "📦 Checking for pending migrations..."
python manage.py migrate --no-input

echo ""
echo "✅ Server is starting..."
echo "📍 Access your application at: http://127.0.0.1:8000"
echo "📍 Admin panel: http://127.0.0.1:8000/admin"
echo ""
echo "Admin credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"
echo ""

# Start the development server
python manage.py runserver