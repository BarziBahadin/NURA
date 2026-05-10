#!/bin/bash
# Fast local development: Docker for backend services, Vite for the admin UI.

set -e

cd "$(dirname "$0")"

LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || true)
if [ -z "$LAN_IP" ]; then
  LAN_IP=$(ipconfig getifaddr en1 2>/dev/null || true)
fi
if [ -z "$LAN_IP" ]; then
  LAN_IP=$(route -n get default 2>/dev/null | awk '/interface:/ {print $2; exit}' | xargs -I{} ipconfig getifaddr {} 2>/dev/null || true)
fi

echo "Starting backend services in Docker..."
if [ -n "$LAN_IP" ]; then
  echo "Detected LAN IP: $LAN_IP"
  LIVEKIT_NODE_IP="$LAN_IP" docker compose up -d postgres redis chromadb livekit nura-api
else
  docker compose up -d postgres redis chromadb livekit nura-api
fi

echo ""
echo "Starting Vite admin dev server..."
echo "  Local: http://localhost:5173"
if [ -n "$LAN_IP" ]; then
  echo "  LAN:   http://$LAN_IP:5173"
fi
echo "  API:   http://localhost:8080"
echo ""

npm --prefix admin run dev:host
