#!/usr/bin/env python3
"""taskboard server — haitian 的任务看板本地服务
GET /           -> index.html（记一次 visit = 对 being 的提醒）
GET /api/tasks  -> tasks.json（不记 visit，避免自动轮询污染提醒信号）
"""
import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(BASE, "tasks.json")
VISITS = os.path.join(BASE, "visits.jsonl")
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _log_visit(self, path):
        try:
            with open(VISITS, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                    "path": path,
                    "ua": self.headers.get("User-Agent", ""),
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._log_visit("/")
            try:
                with open(os.path.join(BASE, "index.html"), "rb") as f:
                    body = f.read()
            except FileNotFoundError:
                self._send(404, '{"error": "index.html missing"}')
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/tasks":
            try:
                with open(TASKS, "rb") as f:
                    self._send(200, f.read().decode("utf-8"))
            except FileNotFoundError:
                self._send(500, '{"error": "tasks.json missing"}')
        else:
            self._send(404, '{"error": "not found"}')

    def log_message(self, *args):
        pass  # 静默，不刷终端


if __name__ == "__main__":
    print(f"taskboard serving on http://127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
