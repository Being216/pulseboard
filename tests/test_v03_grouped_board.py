import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GroupedBoardV03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.server_py = (ROOT / "server.py").read_text(encoding="utf-8")

    def test_backend_enum_matches_current_task_data(self):
        self.assertIn('EDITABLE_STATUSES = {"pending", "in_progress", "blocked", "done"}', self.server_py)

    @unittest.skipUnless(shutil.which("node"), "node is required for inline JavaScript behavior tests")
    def test_frontend_groups_aliases_and_sorts_status_tasks(self):
        script_match = re.search(r"<script>\s*([\s\S]*?)\s*</script>", self.index_html)
        self.assertIsNotNone(script_match)
        script = script_match.group(1)
        script = re.sub(r"\nload\(\);\s*\nsetInterval\(load, 30000\);\s*$", "\n", script)
        node_program = r"""
const fs = require('fs');
const vm = require('vm');
const script = process.argv[1];
const noop = () => {};
const element = {
  addEventListener: noop,
  replaceChildren: noop,
  appendChild: noop,
  querySelector: () => null,
  textContent: "",
  className: ""
};
const context = {
  window: {},
  document: {getElementById: () => element},
  localStorage: {getItem: () => null, setItem: noop},
  setTimeout: noop,
  clearTimeout: noop,
  setInterval: noop,
  fetch: noop,
  confirm: () => true,
  console
};
vm.createContext(context);
vm.runInContext(script, context);
if (!context.window.PulseboardV03) throw new Error("PulseboardV03 test API is missing");
const api = context.window.PulseboardV03;
const tasks = [
  {id: "ip-old", status: "in_progress", updated_at: "2026-09-01T10:00:00+08:00"},
  {id: "ip-new", status: "in_progress", updated_at: "2026-09-02T10:00:00+08:00"},
  {id: "todo", status: "todo"},
  {id: "pending", status: "pending"},
  {id: "blocked", status: "blocked"},
  {id: "done-old", status: "completed", completed_at: "2026-09-01T10:00:00+08:00"},
  {id: "done-new", status: "done", completed_at: "2026-09-03T10:00:00+08:00"}
];
const groups = api.groupTasks(tasks);
const ids = Object.fromEntries(Object.entries(groups).map(([key, value]) => [key, value.map(task => task.id)]));
process.stdout.write(JSON.stringify({ids, defaults: api.DEFAULT_GROUP_OPEN, key: api.GROUP_STATE_STORAGE_KEY}));
"""
        result = subprocess.run(
            ["node", "-e", node_program, script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["ids"]["in_progress"], ["ip-new", "ip-old"])
        self.assertEqual(payload["ids"]["todo"], ["todo", "pending"])
        self.assertEqual(payload["ids"]["blocked"], ["blocked"])
        self.assertEqual(payload["ids"]["done"], ["done-new", "done-old"])
        self.assertEqual(payload["defaults"], {"in_progress": True, "todo": True, "blocked": False, "done": False})
        self.assertEqual(payload["key"], "pulseboard.groupState.v03")

    def test_page_contains_four_rendered_groups_and_persistent_state_hooks(self):
        for marker in ("in_progress", "todo", "blocked", "done"):
            self.assertIn(marker, self.index_html)
        self.assertIn("localStorage", self.index_html)
        self.assertIn("aria-expanded", self.index_html)
        self.assertIn("renderTaskGroups", self.index_html)


if __name__ == "__main__":
    unittest.main()
