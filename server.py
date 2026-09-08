#!/usr/bin/env python3
"""taskboard server — haitian 的任务看板本地服务
GET /           -> index.html（记一次 visit = 对 being 的提醒）
GET /api/tasks  -> tasks.json（不记 visit，避免自动轮询污染提醒信号）
"""
import json
import os
import tempfile
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(BASE, "tasks.json")
VISITS = os.path.join(BASE, "visits.jsonl")
SIGNALS = os.path.join(BASE, "signals.jsonl")
PORT = 8765
EDITABLE_FIELDS = ("title", "summary", "next", "status")
EDITABLE_STATUSES = {"pending", "in_progress", "blocked", "done"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, code, body):
        self._send(code, json.dumps(body, ensure_ascii=False))

    def _now(self):
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8"))
        if not isinstance(body, dict):
            raise ValueError("JSON body must be an object")
        return body

    def _read_tasks(self):
        with open(TASKS, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_tasks(self, data):
        directory = os.path.dirname(TASKS) or "."
        fd, temporary = tempfile.mkstemp(
            prefix=os.path.basename(TASKS) + ".",
            suffix=".tmp",
            dir=directory,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, TASKS)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def _find_task(self, data, task_id):
        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None

    def _append_signal(self, signal_type, task_id):
        signal = {
            "type": signal_type,
            "task_id": task_id,
            "at": self._now(),
            "ua": self.headers.get("User-Agent", ""),
        }
        with open(SIGNALS, "a", encoding="utf-8") as f:
            f.write(json.dumps(signal, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

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
                self._send_json(200, self._read_tasks())
            except FileNotFoundError:
                self._send_json(500, {"ok": False, "error": "tasks.json missing"})
            except (json.JSONDecodeError, OSError):
                self._send_json(500, {"ok": False, "error": "tasks.json unreadable"})
        elif path == "/api/history":
            try:
                data = self._read_tasks()
                self._send_json(200, data.get("history", []))
            except FileNotFoundError:
                self._send_json(500, {"ok": False, "error": "tasks.json missing"})
            except (json.JSONDecodeError, OSError):
                self._send_json(500, {"ok": False, "error": "tasks.json unreadable"})
        else:
            self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        parts = [unquote(part) for part in urlparse(self.path).path.split("/") if part]
        if len(parts) != 4 or parts[:2] != ["api", "tasks"]:
            self._send_json(404, {"ok": False, "error": "not found"})
            return

        task_id, action = parts[2:]
        try:
            data = self._read_tasks()
        except FileNotFoundError:
            self._send_json(500, {"ok": False, "error": "tasks.json missing"})
            return
        except (json.JSONDecodeError, OSError):
            self._send_json(500, {"ok": False, "error": "tasks.json unreadable"})
            return

        task = self._find_task(data, task_id)
        if task is None:
            self._send_json(404, {"ok": False, "error": "task not found"})
            return

        try:
            if action == "edit":
                self._edit_task(data, task)
            elif action == "cancel":
                self._cancel_task(data, task)
            elif action in ("refresh", "remind"):
                self._append_signal(action, task_id)
            else:
                self._send_json(404, {"ok": False, "error": "not found"})
                return
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})
            return
        except OSError:
            self._send_json(500, {"ok": False, "error": "write failed"})
            return

        self._send_json(200, {"ok": True})

    def _edit_task(self, data, task):
        body = self._read_json_body()
        unknown = sorted(set(body) - set(EDITABLE_FIELDS))
        if unknown:
            raise ValueError("unsupported fields: " + ", ".join(unknown))
        for field, value in body.items():
            if not isinstance(value, str):
                raise ValueError(f"{field} must be a string")
            if field == "status" and value not in EDITABLE_STATUSES:
                raise ValueError("status must be pending, in_progress, blocked, or done")

        changed = []
        for field, value in body.items():
            if task.get(field) != value:
                task[field] = value
                changed.append(field)
        task["human_edited"] = {"at": self._now(), "fields": changed}
        self._write_tasks(data)

    def _cancel_task(self, data, task):
        data["tasks"].remove(task)
        task["status"] = "cancelled"
        data.setdefault("history", []).append(task)
        self._write_tasks(data)

    def log_message(self, *args):
        pass  # 静默，不刷终端


if __name__ == "__main__":
    print(f"taskboard serving on http://127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
