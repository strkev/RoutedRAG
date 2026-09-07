#!/usr/bin/env bash
set -e

if [ "$1" == "--docker" ]; then
    echo "Starting with Docker Compose..."
    docker compose up --build
else
    echo "Starting locally with Uvicorn..."
    echo "Note: Ensure your Conda environment is active: 'conda activate env'"
    echo "Running on: http://localhost:8000"
    uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "data/*" --reload-exclude "config/*"
fi
