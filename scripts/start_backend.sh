#!/bin/bash

cd "$(dirname "$0")/../backend"

echo "Starting backend server..."
echo "Creating virtual environment..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting FastAPI server on http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
