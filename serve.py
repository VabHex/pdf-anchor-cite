#!/usr/bin/env python3
"""
PDF Anchor Cite - local launcher  v1.0.0 (2026-11-24)

Starts a small web server on this computer only (127.0.0.1), opens the viewer
in your browser, and lets the viewer load PDFs automatically from your
library folder by matching the filenames listed in a summary.

  python serve.py                         start, open the viewer
  python serve.py "path\\to\\summary.md"    start and open that summary
  python serve.py --library "D:\\Papers"   use a different library folder
  python serve.py --port 8790 --no-browser

The library folder is read from config.json ("library"), default ./library.
Nothing is sent anywhere; press Ctrl+C (or close the window) to stop.
Standard library only.
"""
import argparse
import json
import mimetypes
import os
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SUMMARY_EXT = (".md", ".markdown", ".txt")
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/javascript", ".js")


def load_config():
    try:
        with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def resolve(p):
    p = os.path.expandvars(os.path.expanduser(p))
    return os.path.abspath(p if os.path.isabs(p) else os.path.join(HERE, p))


def inside(root, path):
    try:
        return os.path.commonpath([os.path.realpath(root), os.path.realpath(path)]) == os.path.realpath(root)
    except ValueError:
        return False


class Roots:
    """Folders the viewer may read from: /library/... and /extra/..."""

    def __init__(self, library, extra=None):
        self.library, self.extra = library, extra
        self._index, self._index_time = {}, 0
        self._lock = threading.Lock()

    def items(self):
        out = [("library", self.library)]
        if self.extra and not inside(self.library, self.extra):
            out.append(("extra", self.extra))
        return out

    def url_for(self, path):
        for prefix, root in self.items():
            if inside(root, path):
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                return f"{prefix}/" + urllib.parse.quote(rel)
        return None

    def reindex(self, force=False):
        with self._lock:
            if not force and time.time() - self._index_time < 30:
                return
            idx = {}
            for _p, root in self.items():
                if not os.path.isdir(root):
                    continue
                for r, dirs, files in os.walk(root):
                    dirs[:] = [d for d in dirs if not d.startswith((".", "$"))]
                    for f in files:
                        idx.setdefault(f.lower(), os.path.join(r, f))
            self._index, self._index_time = idx, time.time()

    def find(self, name):
        self.reindex()
        hit = self._index.get(name.lower())
        if not hit or not os.path.isfile(hit):
            self.reindex(force=True)
            hit = self._index.get(name.lower())
        return hit

    def summaries(self, limit=3000):
        self.reindex(force=True)
        out = []
        for low, path in self._index.items():
            if low.endswith(SUMMARY_EXT) and low != "readme.md":
                try:
                    m = os.path.getmtime(path)
                except OSError:
                    continue
                prefix_root = next((r for _p, r in self.items() if inside(r, path)), self.library)
                out.append({"name": os.path.basename(path),
                            "path": os.path.relpath(path, prefix_root).replace(os.sep, "/"),
                            "url": self.url_for(path), "mtime": m,
                            "modified": time.strftime("%d/%m/%Y %H:%M", time.localtime(m))})
        out.sort(key=lambda x: -x["mtime"])
        return out[:limit]


def make_handler(roots):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kw):
            super().__init__(*args, directory=HERE, **kw)

        def log_message(self, fmt, *args):
            pass  # keep the console quiet

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def send_json(self, obj, code=200):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def send_path(self, path):
            if not os.path.isfile(path):
                return self.send_error(404)
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            if ctype.startswith("text/"):
                ctype += "; charset=utf-8"
            size = os.path.getsize(path)
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            self.end_headers()
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            path = urllib.parse.unquote(u.path)
            q = urllib.parse.parse_qs(u.query)
            if path in ("/", ""):
                self.send_response(302)
                self.send_header("Location", "/viewer.html" + (("?" + u.query) if u.query else ""))
                self.end_headers()
                return
            if path == "/api/ping":
                return self.send_json({"ok": True, "version": VERSION})
            if path == "/api/find":
                name = os.path.basename((q.get("name") or [""])[0])
                hit = roots.find(name) if name else None
                return self.send_json({"url": roots.url_for(hit)}) if hit else self.send_json({"error": "not found"}, 404)
            if path == "/api/list":
                return self.send_json(roots.summaries())
            for prefix, root in roots.items():
                if path.startswith(f"/{prefix}/"):
                    target = os.path.normpath(os.path.join(root, path[len(prefix) + 2:]))
                    if not inside(root, target):
                        return self.send_error(403)
                    return self.send_path(target)
            return super().do_GET()

        def list_directory(self, path):
            self.send_error(404)

    return Handler


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    cfg = load_config()
    ap = argparse.ArgumentParser(description="Start the PDF Anchor Cite viewer on this computer.")
    ap.add_argument("summary", nargs="?", help="optional summary file to open straight away")
    ap.add_argument("--library", default=cfg.get("library", "library"), help="folder searched for PDFs and summaries")
    ap.add_argument("--port", type=int, default=int(cfg.get("port", 8765)))
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    library = resolve(a.library)
    if not os.path.isdir(library):
        if os.path.abspath(library) == os.path.join(HERE, "library"):
            os.makedirs(library, exist_ok=True)
        else:
            print(f"Library folder not found: {library}\nEdit config.json or pass --library.")
    extra, start_q = None, ""
    if a.summary:
        sp = os.path.abspath(a.summary.strip('"'))
        if not os.path.isfile(sp):
            sys.exit(f"Summary not found: {sp}")
        extra = os.path.dirname(sp)
        roots = Roots(library, extra)
        start_q = "?summary=" + urllib.parse.quote(roots.url_for(sp), safe="/")
    else:
        roots = Roots(library)

    server = None
    for port in range(a.port, a.port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(roots))
            break
        except OSError:
            continue
    if not server:
        sys.exit("Could not find a free port.")
    url = f"http://127.0.0.1:{server.server_address[1]}/viewer.html{start_q}"
    print(f"PDF Anchor Cite {VERSION}")
    print(f"Library : {library}")
    if extra:
        print(f"Summary : {a.summary}")
    print(f"Viewer  : {url}")
    print("Leave this window open while you use the viewer. Ctrl+C to stop.")
    threading.Thread(target=roots.reindex, kwargs={"force": True}, daemon=True).start()
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
