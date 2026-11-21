#!/usr/bin/env python3
"""
Registration National - server (Python 3.8+, standard library only).

Run:      python app.py
Open:     http://127.0.0.1:8000
Phones:   python app.py --host 0.0.0.0   (phones need HTTPS or localhost for encryption APIs)

Project layout
  app.py                 this server: static files + REST API + SQLite storage
  static/index.html      page shell
  static/style.css       all styling
  static/js/rwanda.js    all provinces, districts, sectors and cells of Rwanda
  static/js/core.js      shared state, helpers, translations, storage, encryption, seed data
  static/js/chw.js       CHW intake wizard and sync
  static/js/portal.js    registrar portal and admin console
  static/js/app.js       top bar, sign in / sign up, render loop

API
  GET  /api/ping    health check
  GET  /api/db      read the shared database (404 until first seeded)
  POST /api/db      replace the shared database (JSON body)
  POST /api/reset   delete all shared data (re-seeded on next page load)
"""
import argparse
import json
import os
import socket
import sqlite3
import threading
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# =============================================================================
# Configuration
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_FILE = os.path.join(BASE_DIR, "registration_national.db")
MAX_BODY = 20 * 1024 * 1024
LOCK = threading.Lock()

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


# =============================================================================
# Database (SQLite key/value store holding the shared state as JSON)
# =============================================================================
def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return conn


def load_state():
    with LOCK, closing(connect()) as conn:
        row = conn.execute("SELECT value FROM kv WHERE key = 'server'").fetchone()
        return row[0] if row else None


def save_state(text):
    with LOCK, closing(connect()) as conn, conn:
        conn.execute("INSERT OR REPLACE INTO kv (key, value) VALUES ('server', ?)", (text,))


def reset_state():
    with LOCK, closing(connect()) as conn, conn:
        conn.execute("DELETE FROM kv")


# =============================================================================
# HTTP server
# =============================================================================
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, url_path):
        """Serve a file from static/, refusing anything outside that folder."""
        rel = "index.html" if url_path in ("", "/") else url_path.lstrip("/")
        full = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not full.startswith(STATIC_DIR + os.sep) or not os.path.isfile(full):
            return self._send(404, '{"error": "not found"}')
        ctype = CONTENT_TYPES.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/ping":
            self._send(200, '{"ok": true}')
        elif path == "/api/db":
            state = load_state()
            if state is None:
                self._send(404, '{"error": "empty"}')
            else:
                self._send(200, state)
        elif path.startswith("/api/"):
            self._send(404, '{"error": "not found"}')
        else:
            self._serve_static(path)

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._send(413, '{"error": "too large"}')
        raw = self.rfile.read(length)
        if path == "/api/db":
            try:
                data = json.loads(raw)
                if not (isinstance(data, dict) and "users" in data and "records" in data):
                    raise ValueError("bad shape")
            except ValueError:
                return self._send(400, '{"error": "invalid database"}')
            save_state(json.dumps(data))
            self._send(200, '{"ok": true}')
        elif path == "/api/reset":
            reset_state()
            self._send(200, '{"ok": true}')
        else:
            self._send(404, '{"error": "not found"}')

    def log_message(self, fmt, *args):
        if "/api/" not in self.path:
            print("  %s - %s" % (self.address_string(), fmt % args))


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


# =============================================================================
# Entry point
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Registration National server")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()

    if not os.path.isfile(os.path.join(STATIC_DIR, "index.html")):
        raise SystemExit("Missing static/index.html. Keep app.py next to the static folder.")

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("Registration National is running")
    print("  Local:   http://127.0.0.1:%d" % args.port)
    if args.host == "0.0.0.0":
        print("  Network: http://%s:%d" % (lan_ip(), args.port))
    print("  Data:    %s" % DB_FILE)
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
