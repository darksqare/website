#!/usr/bin/env python3
"""
darkdev.boo project sync service (stdlib only, no pip needed).

POST /sync  ->  copies *.html from SYNC_SRC into SYNC_DST
  - new files are copied
  - files that already exist are replaced ONLY if the source copy is newer
    and its content differs
  - nothing is ever deleted; other files in SYNC_DST are never touched
The projects page lists SYNC_DST on its own (nginx JSON directory listing),
so this service only has to copy files.

Listens on 127.0.0.1 only; nginx proxies /api/sync to it.
"""
import json, os, re, shutil, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SRC = os.environ.get("SYNC_SRC", "/mnt/shared/info_ora/html")
DST = os.environ.get("SYNC_DST", "/var/www/folder1/projects")
HOST = os.environ.get("SYNC_HOST", "127.0.0.1")
PORT = int(os.environ.get("SYNC_PORT", "8765"))
COOLDOWN = 3  # seconds between syncs (stops button spamming)

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.html$")

_lock = threading.Lock()
_last = 0.0


def same_content(a, b):
    if os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        while True:
            ca, cb = fa.read(65536), fb.read(65536)
            if ca != cb:
                return False
            if not ca:
                return True


def atomic_copy(src, dst, st):
    fd, tmp = tempfile.mkstemp(dir=DST, prefix=".sync-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
            shutil.copyfileobj(inp, out)
        os.chmod(tmp, 0o644)
        os.utime(tmp, (st.st_atime, st.st_mtime))  # keep source mtime
        os.replace(tmp, dst)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run_sync():
    if not os.path.isdir(SRC):
        raise FileNotFoundError("source folder not found: " + SRC)
    os.makedirs(DST, exist_ok=True)
    new, updated, skipped, unchanged = [], [], [], 0
    for entry in sorted(os.scandir(SRC), key=lambda e: e.name):
        name = entry.name
        if not name.lower().endswith(".html"):
            continue
        if (not NAME_RE.match(name) or entry.is_symlink()
                or not entry.is_file(follow_symlinks=False)):
            skipped.append(name)
            continue
        st = entry.stat(follow_symlinks=False)
        dst = os.path.join(DST, name)
        if not os.path.exists(dst):
            atomic_copy(entry.path, dst, st)
            new.append(name)
        elif st.st_mtime > os.stat(dst).st_mtime and not same_content(entry.path, dst):
            atomic_copy(entry.path, dst, st)
            updated.append(name)
        else:
            unchanged += 1
    return {"ok": True, "new": new, "updated": updated,
            "unchanged": unchanged, "skipped": skipped}


class Handler(BaseHTTPRequestHandler):
    server_version = "darkdev-sync"

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        global _last
        if self.path.split("?")[0] != "/sync":
            return self._send(404, {"ok": False, "error": "not found"})
        if not _lock.acquire(blocking=False):
            return self._send(429, {"ok": False, "error": "sync already running"})
        try:
            wait = COOLDOWN - (time.time() - _last)
            if wait > 0:
                return self._send(429, {"ok": False, "error": "slow down, try again in %ds" % (wait + 1)})
            result = run_sync()
            _last = time.time()
            self._send(200, result)
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})
        finally:
            _lock.release()

    def do_GET(self):
        self._send(405, {"ok": False, "error": "use POST"})

    do_PUT = do_DELETE = do_GET


if __name__ == "__main__":
    print("sync %s -> %s on %s:%d" % (SRC, DST, HOST, PORT), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
