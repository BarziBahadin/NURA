#!/bin/bash
# Fast local development: Docker for backend services, Vite for the admin UI.

set -e

cd "$(dirname "$0")"

detect_lan_ip() {
  for iface in en0 en1 en2 en3 en4 en5 bridge100; do
    ip=$(ipconfig getifaddr "$iface" 2>/dev/null || true)
    if [ -n "$ip" ]; then
      echo "$ip"
      return
    fi
  done

  if command -v route >/dev/null 2>&1; then
    iface=$(route -n get default 2>/dev/null | awk '/interface:/ {print $2; exit}' || true)
    if [ -n "$iface" ]; then
      ip=$(ipconfig getifaddr "$iface" 2>/dev/null || true)
      if [ -n "$ip" ]; then
        echo "$ip"
        return
      fi
    fi
  fi

  if command -v ifconfig >/dev/null 2>&1; then
    ifconfig | awk '
      /^[a-z0-9]+: / { iface=$1; sub(":", "", iface) }
      /inet / && $2 !~ /^127\./ && iface !~ /^(lo|docker|veth|utun|awdl|llw)/ {
        print $2
        exit
      }
    '
  fi
}

setup_https_certs() {
  local lan_ip="$1"

  if ! command -v mkcert &>/dev/null; then
    echo "mkcert not found — installing via Homebrew..."
    brew install mkcert
  fi

  mkcert -install 2>/dev/null || true

  mkdir -p certs

  local domains="localhost 127.0.0.1"
  [ -n "$lan_ip" ] && domains="$domains $lan_ip"

  echo "Generating HTTPS certs for: $domains"
  mkcert -cert-file certs/cert.pem -key-file certs/key.pem $domains
}

LAN_IP=$(detect_lan_ip)

setup_https_certs "$LAN_IP"

echo "Starting backend services in Docker..."
docker compose up -d postgres redis chromadb nura-api nura-admin caddy

echo ""
echo "Services running:"
echo "  API  (HTTP):  http://localhost:8080"
echo "  API  (HTTPS): https://localhost:8443"
echo "  Admin(HTTP):  http://localhost:3004"
echo "  Admin(HTTPS): https://localhost:3443"
if [ -n "$LAN_IP" ]; then
  echo "  API  (LAN):   https://$LAN_IP:8443"
  echo "  Admin(LAN):   https://$LAN_IP:3443"
fi
echo ""
echo "Starting Vite admin dev server..."
echo "  Local: http://localhost:5173"
if [ -n "$LAN_IP" ]; then
  echo "  LAN:   http://$LAN_IP:5173"
fi
echo ""

npm --prefix admin run dev:host
