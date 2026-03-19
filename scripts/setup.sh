#!/bin/bash
set -e

echo "=========================================="
echo "  NURA Setup - Rcell Telecom"
echo "=========================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed."
    echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    exit 1
fi

echo "Starting NURA services..."
cd "$(dirname "$0")/.."
docker compose up -d --build

echo ""
echo "Waiting for services to be ready..."
sleep 15

echo ""
echo "Checking Ollama (requires SSH tunnel)..."
echo "If not running, open a new terminal and run:"
echo "  ssh -L 11434:localhost:11434 barzi@172.24.0.17 -N"
echo ""

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama is reachable."
    echo "Pulling llama3.1:8b model (this may take a while)..."
    curl -s http://localhost:11434/api/pull -d '{"name":"llama3.1:8b"}' > /dev/null
    echo "Pulling nomic-embed-text model..."
    curl -s http://localhost:11434/api/pull -d '{"name":"nomic-embed-text"}' > /dev/null
    echo "Models pulled."
else
    echo "WARNING: Ollama is not reachable. Start the SSH tunnel first."
fi

echo ""
echo "Copying handbook to ingestion directory..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HANDBOOK_PDF="$SCRIPT_DIR/../call center hand book ENG draft.pdf"
if [ -f "$HANDBOOK_PDF" ]; then
    cp "$HANDBOOK_PDF" "$SCRIPT_DIR/../ingestion/handbook/"
    echo "Handbook copied."
else
    echo "Handbook PDF not found at expected location."
fi

echo ""
echo "Running handbook ingestion..."
sleep 5
docker exec nura-api python /app/ingestion/ingest.py || echo "Note: Ingestion may need to run after Ollama is connected."

echo ""
echo "=========================================="
echo "  NURA is ready!"
echo ""
echo "  API:        http://localhost:8000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  Admin:      http://localhost:3000"
echo "  Test Chat:  open frontend/index.html in your browser"
echo "  Health:     http://localhost:8000/v1/health"
echo ""
echo "  API Key: nura-dev-key-change-in-production"
echo "=========================================="
