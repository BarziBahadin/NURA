#!/bin/bash
# Kill anything on NURA ports, then start all services

PORTS=(8080 8001 5432 6379 3004 9000)

echo "Freeing ports..."
for PORT in "${PORTS[@]}"; do
  PIDS=$(lsof -ti tcp:$PORT 2>/dev/null)
  if [ -n "$PIDS" ]; then
    echo "  killing port $PORT (PIDs: $PIDS)"
    echo "$PIDS" | xargs kill -9 2>/dev/null
  fi
done

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
