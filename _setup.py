import subprocess, os, shutil

src = "/Users/5d/.heart-portal/workspace/taskboard"
dst = "/Users/5d/.heart-portal/workspace/pulseboard"
os.makedirs(dst, exist_ok=True)

# 复制三件套（不带运行时产物 visits.jsonl）
for f in ["server.py", "index.html", "tasks.json"]:
    shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
print("copied:", os.listdir(dst))
