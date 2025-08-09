#!/bin/bash

# UsefulWriter LMS Server Stop Script

echo "🛑 Stopping UsefulWriter LMS server..."

# Find and kill any process using port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    echo "✅ Server stopped successfully"
else
    echo "ℹ️  No server running on port 8000"
fi