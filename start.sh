#!/bin/bash
# Start all services. Port cleanup is opt-in to avoid killing unrelated processes.

set -e

PORTS=(8080 8001 5432 6379 3004 9000)

if [ "${NURA_FORCE_FREE_PORTS:-0}" = "1" ]; then
  echo "Freeing NURA ports..."
  for PORT in "${PORTS[@]}"; do
    PIDS=$(lsof -ti tcp:$PORT 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
      echo "  stopping port $PORT (PIDs: $PIDS)"
      echo "$PIDS" | xargs kill 2>/dev/null || true
    fi
  done
else
  BUSY_PORTS=()
  for PORT in "${PORTS[@]}"; do
    if lsof -ti tcp:$PORT >/dev/null 2>&1; then
      BUSY_PORTS+=("$PORT")
    fi
  done
  if [ "${#BUSY_PORTS[@]}" -gt 0 ]; then
    echo "Ports already in use: ${BUSY_PORTS[*]}"
    echo "Stop those services, or rerun with NURA_FORCE_FREE_PORTS=1 to send a normal SIGTERM."
    exit 1
  fi
fi

echo "Starting Docker services..."
cd "$(dirname "$0")"
docker compose up -d

echo ""
echo "Serving frontend on http://localhost:9000"
open "http://localhost:9000/widget.html"
python3 -m http.server 9000 --directory frontend &
FRONTEND_PID=$!

echo ""
echo "All services running:"
echo "  Widget     → http://localhost:9000/widget.html"
echo "  API        → http://localhost:8080"
echo "  Admin      → http://localhost:3004"
echo ""
echo "Press Ctrl+C to stop the frontend server"
trap "kill $FRONTEND_PID 2>/dev/null; echo 'Frontend stopped.'" EXIT
wait $FRONTEND_PID
