#!/bin/bash

cd "$(dirname "$0")/../frontend"

echo "Starting frontend server..."
echo "Installing dependencies..."

if [ ! -d "node_modules" ]; then
    npm install
fi

echo "Starting Next.js server on http://localhost:3000"
npm run dev
