#!/bin/zsh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

HOST="127.0.0.1"
PORT="8000"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Chyba: python3 neni nainstalovany nebo neni v PATH."
  echo "Nainstaluj Python 3 a pak skript spust znovu."
  read -r "?Stiskni Enter pro zavreni..."
  exit 1
fi

echo "Spoustim Fire Separation API..."
echo "Adresa: http://$HOST:$PORT"
echo "Ukonceni: zavri toto okno nebo stiskni Ctrl+C"
echo

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

python3 app.py --host "$HOST" --port "$PORT" &
SERVER_PID=$!

sleep 1

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "API se nepodarilo spustit."
  read -r "?Stiskni Enter pro zavreni..."
  exit 1
fi

wait "$SERVER_PID"

