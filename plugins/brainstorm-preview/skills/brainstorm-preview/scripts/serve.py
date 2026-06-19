#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "markdown>=3.6",
#   "pygments>=2.17",
# ]
# ///
"""
brainstorm-preview: serve every markdown file under docs/ as styled HTML.

Renders specs, plans, and other docs as a sortable index plus per-file pages,
including client-side rendering for ```dot (Graphviz) and ```mermaid blocks
via CDN. Binds to 0.0.0.0 so peers on the same Tailscale tailnet can reach it.

Usage:
    uv run scripts/serve.py [--port 8765] [--docs-root .] [--bind 0.0.0.0]
                            [--latest] [--open <relpath>]

`--latest` highlights the most-recently-modified spec/plan at the top of the
index and prints a direct URL on startup — useful right after brainstorming
or writing-plans finishes so the caller can hand the user a single link.
`--open <relpath>` does the same for a specific file (relpath must live
under `<docs-root>/docs`).

If `uv` is missing, install once:
    pip install markdown pygments
    python3 scripts/serve.py [args...]
"""
from __future__ import annotations

import argparse
import html
import http.server
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from urllib.parse import quote, unquote

import markdown


PAGE_CSS = """
:root {
  --bg: #fdfcf8; --fg: #1a1a1a; --muted: #6a6a6a; --accent: #2563eb;
  --code-bg: #f1efe7; --border: #e3e0d2; --row-hover: #f6f3e7;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181c; --fg: #e7e5dc; --muted: #9a9a9a; --accent: #93c5fd;
    --code-bg: #1f2126; --border: #2a2c30; --row-hover: #1c1f24;
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg); }
body { font: 16px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, Roboto, sans-serif; }
main { max-width: 880px; margin: 0 auto; padding: 32px 24px 64px; }
nav.top { padding: 12px 24px; border-bottom: 1px solid var(--border); display: flex; gap: 16px; align-items: center; }
nav.top a { color: var(--fg); text-decoration: none; font-weight: 600; }
nav.top .crumb { color: var(--muted); font-weight: 400; }
h1, h2, h3, h4 { font-family: ui-serif, "New York", "Iowan Old Style", Georgia, serif; line-height: 1.25; }
h1 { font-size: 2rem; margin-top: 0; }
h2 { font-size: 1.5rem; margin-top: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
h3 { font-size: 1.2rem; margin-top: 1.6rem; }
a { color: var(--accent); }
code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 0.92em; background: var(--code-bg); padding: 1px 5px; border-radius: 4px; }
pre { background: var(--code-bg); padding: 14px 16px; border-radius: 8px; overflow-x: auto; line-height: 1.45; }
pre code { background: transparent; padding: 0; font-size: 0.88em; }
blockquote { margin: 0 0 1em 0; padding: 6px 14px; border-left: 3px solid var(--accent); color: var(--muted); background: var(--code-bg); border-radius: 0 6px 6px 0; }
table { border-collapse: collapse; margin: 14px 0; width: 100%; }
th, td { padding: 8px 12px; border: 1px solid var(--border); text-align: left; }
th { background: var(--code-bg); }
hr { border: 0; border-top: 1px solid var(--border); margin: 28px 0; }
ul.idx { list-style: none; padding: 0; margin: 8px 0 20px; }
ul.idx li { padding: 12px; border-radius: 8px; border: 1px solid transparent; }
ul.idx li:hover { background: var(--row-hover); border-color: var(--border); }
ul.idx a { text-decoration: none; color: var(--fg); display: grid; grid-template-columns: 1fr auto; grid-template-areas: "name mtime" "path mtime"; column-gap: 12px; row-gap: 2px; align-items: baseline; }
ul.idx .name { grid-area: name; font-weight: 700; font-size: 1.02em; line-height: 1.3; word-break: break-word; }
ul.idx .path { grid-area: path; color: var(--muted); font-size: 0.78em; line-height: 1.2; word-break: break-all; }
ul.idx .mtime { grid-area: mtime; color: var(--muted); font-size: 0.78em; white-space: nowrap; align-self: start; }
ul.idx h3 { margin: 22px 0 4px; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-family: inherit; font-weight: 700; }
@media (max-width: 640px) {
  main { padding: 20px 14px 56px; }
  ul.idx li { padding: 14px 10px; }
  ul.idx a { grid-template-columns: 1fr; grid-template-areas: "name" "path" "mtime"; row-gap: 4px; }
  ul.idx .mtime { align-self: auto; }
  h1 { font-size: 1.65rem; }
}
.task-list-item { list-style: none; }
input[type=checkbox] { margin-right: 8px; }
.graphviz svg, .mermaid svg { max-width: 100%; height: auto; }
"""

PAGE_HEAD = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<nav class="top"><a href="/">brainstorm-preview</a><span class="crumb">{crumb}</span></nav>
<main>
"""

PAGE_FOOT = """
</main>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/@hpcc-js/wasm@2/dist/index.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-graphviz@5"></script>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: false, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" });
  // Render mermaid blocks
  document.querySelectorAll("pre > code.language-mermaid").forEach((el, i) => {
    const wrap = document.createElement("div");
    wrap.className = "mermaid";
    wrap.id = "mermaid-" + i;
    wrap.textContent = el.textContent;
    el.parentElement.replaceWith(wrap);
  });
  await mermaid.run();
</script>
<script>
  // Render dot/graphviz blocks
  document.querySelectorAll("pre > code.language-dot, pre > code.language-graphviz").forEach((el, i) => {
    const wrap = document.createElement("div");
    wrap.className = "graphviz";
    wrap.id = "graphviz-" + i;
    const src = el.textContent;
    el.parentElement.replaceWith(wrap);
    try { d3.select("#graphviz-" + i).graphviz({ fit: true }).renderDot(src); }
    catch (e) { wrap.textContent = "[graphviz render failed] " + e.message; }
  });
</script>
<script>
  // Heartbeat: lets the server auto-stop ~180s after the last tab closes.
  (function () {
    const ping = () => { fetch("/heartbeat", { cache: "no-store" }).catch(() => {}); };
    ping();
    setInterval(ping, 30000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) ping(); });
  })();
</script>
</body></html>
"""

INDEX_GROUP_ORDER = ["specs", "plans", "other"]


def list_docs(root: Path) -> dict[str, list[Path]]:
    """Return {group: [Path, ...]} for every *.md under docs/, newest first.

    Files under docs/superpowers/specs/ are grouped as "specs", those under
    docs/superpowers/plans/ as "plans", everything else under docs/ as "other".
    """
    docs_dir = root / "docs"
    if not docs_dir.is_dir():
        return {}
    groups: dict[str, list[Path]] = {g: [] for g in INDEX_GROUP_ORDER}
    for path in docs_dir.rglob("*.md"):
        rel = path.relative_to(root)
        parts = rel.parts
        if "superpowers" in parts and "specs" in parts:
            groups["specs"].append(path)
        elif "superpowers" in parts and "plans" in parts:
            groups["plans"].append(path)
        else:
            groups["other"].append(path)
    for g in groups:
        groups[g].sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return groups


def _row(root: Path, p: Path) -> str:
    rel = p.relative_to(root)
    mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return (
        "<li><a href=\"/view/{href}\">"
        "<span class=\"name\">{name}</span>"
        "<span class=\"path\">{path}</span>"
        "<span class=\"mtime\">{mtime}</span>"
        "</a></li>".format(
            href=quote(str(rel)),
            name=html.escape(p.stem),
            path=html.escape(str(rel.parent)),
            mtime=mtime,
        )
    )


def render_index(root: Path, highlight: Path | None = None) -> str:
    groups = list_docs(root)
    if not groups:
        body = "<p>No <code>docs/</code> directory found under {}.</p>".format(html.escape(str(root)))
    else:
        chunks = []
        if highlight is not None and highlight.is_file():
            chunks.append("<h3>Latest</h3><ul class=\"idx\">")
            chunks.append(_row(root, highlight))
            chunks.append("</ul>")
        labels = {"specs": "Specs", "plans": "Plans", "other": "Other docs"}
        for g in INDEX_GROUP_ORDER:
            items = groups.get(g) or []
            if not items:
                continue
            chunks.append(f"<h3>{labels[g]}</h3><ul class=\"idx\">")
            for p in items:
                chunks.append(_row(root, p))
            chunks.append("</ul>")
        body = "".join(chunks)
    return (
        PAGE_HEAD.format(title="brainstorm-preview", css=PAGE_CSS, crumb=html.escape(str(root)))
        + "<h1>Docs index</h1>"
        + body
        + PAGE_FOOT
    )


def latest_doc(root: Path) -> Path | None:
    """Return the most-recently-modified .md under docs/superpowers/{specs,plans}."""
    candidates: list[Path] = []
    for sub in ("docs/superpowers/specs", "docs/superpowers/plans"):
        d = root / sub
        if d.is_dir():
            candidates.extend(d.glob("*.md"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


MD_EXTS = ["fenced_code", "tables", "toc", "codehilite", "sane_lists", "attr_list"]
MD_EXT_CFG = {"codehilite": {"guess_lang": False, "noclasses": True}}


def render_file(root: Path, rel: Path) -> tuple[int, str]:
    path = (root / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return 403, "Forbidden"
    if not path.is_file() or path.suffix.lower() != ".md":
        return 404, "Not found"
    text = path.read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=MD_EXTS, extension_configs=MD_EXT_CFG)
    body = md.convert(text)
    page = (
        PAGE_HEAD.format(
            title=html.escape(path.stem),
            css=PAGE_CSS,
            crumb=html.escape(str(rel)),
        )
        + body
        + PAGE_FOOT
    )
    return 200, page


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "brainstorm-preview/1.0"

    def __init__(self, *args, root: Path, highlight: Path | None = None, activity=None, **kwargs):
        self.root = root
        self.highlight = highlight
        self.activity = activity if activity is not None else [0.0]
        super().__init__(*args, **kwargs)

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(self.path.split("?", 1)[0])
        self.activity[0] = time.monotonic()
        if path == "/heartbeat":
            return self._send(200, "ok\n", "text/plain; charset=utf-8")
        if path == "/" or path == "":
            return self._send(200, render_index(self.root, self.highlight))
        if path.startswith("/view/"):
            rel = Path(path[len("/view/") :])
            code, body = render_file(self.root, rel)
            ctype = "text/html; charset=utf-8" if code == 200 else "text/plain; charset=utf-8"
            return self._send(code, body, ctype)
        if path == "/healthz":
            return self._send(200, "ok\n", "text/plain; charset=utf-8")
        return self._send(404, "Not found", "text/plain; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:  # noqa: N802
        sys.stderr.write(
            "[%s] %s %s\n" % (self.log_date_time_string(), self.address_string(), fmt % args)
        )


def tailscale_url(port: int) -> str | None:
    try:
        out = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    line = next((l.strip() for l in out.stdout.splitlines() if l.strip()), None)
    return f"http://{line}:{port}/" if line else None


def lan_url(port: int) -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return f"http://{s.getsockname()[0]}:{port}/"
    except OSError:
        return None


def main() -> int:
    p = argparse.ArgumentParser(description="Preview docs/*.md as HTML over HTTP.")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    p.add_argument("--docs-root", default=".", help="Project root (defaults to cwd)")
    p.add_argument("--bind", default="0.0.0.0", help="Bind address (default 0.0.0.0)")
    p.add_argument(
        "--latest",
        action="store_true",
        help="Highlight the newest spec/plan and print its direct URL on startup.",
    )
    p.add_argument(
        "--open",
        dest="open_path",
        default=None,
        help="Relpath under <docs-root>/docs to highlight and print on startup.",
    )
    p.add_argument(
        "--idle-timeout",
        type=int,
        default=180,
        help="Auto-shutdown after N seconds with no request / heartbeat (0 = never).",
    )
    p.add_argument("--state-file", default=None, help="Remove this file on shutdown.")
    p.add_argument("--log-file", default=None, help="Remove this file on shutdown.")
    args = p.parse_args()

    root = Path(args.docs_root).resolve()
    if not (root / "docs").is_dir():
        sys.stderr.write(f"warn: {root}/docs does not exist; index will be empty.\n")

    highlight: Path | None = None
    if args.open_path:
        candidate = (root / args.open_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            sys.stderr.write(f"warn: --open path {args.open_path} escapes docs-root; ignored.\n")
        else:
            if candidate.is_file() and candidate.suffix.lower() == ".md":
                highlight = candidate
            else:
                sys.stderr.write(f"warn: --open path {args.open_path} not a .md file; ignored.\n")
    elif args.latest:
        highlight = latest_doc(root)
        if highlight is None:
            sys.stderr.write("warn: --latest passed but no specs/plans found.\n")

    activity = [time.monotonic()]
    handler = partial(Handler, root=root, highlight=highlight, activity=activity)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.bind, args.port), handler) as httpd:
        print(f"brainstorm-preview serving from {root}", flush=True)
        print(f"  local:     http://localhost:{args.port}/", flush=True)
        lan = lan_url(args.port)
        if lan:
            print(f"  lan:       {lan}", flush=True)
        ts = tailscale_url(args.port)
        if ts:
            print(f"  tailscale: {ts}", flush=True)
        else:
            print("  tailscale: (not detected — run `tailscale ip -4` to verify)", flush=True)
        if highlight is not None:
            rel = highlight.relative_to(root)
            path_seg = f"/view/{quote(str(rel))}"
            print(f"  latest:    http://localhost:{args.port}{path_seg}", flush=True)
            if ts:
                print(f"             {ts.rstrip('/')}{path_seg}", flush=True)
        if args.idle_timeout > 0:
            print(f"  (auto-stop after {args.idle_timeout}s with no open tab)", flush=True)

            def monitor() -> None:
                interval = max(1, min(15, args.idle_timeout))
                while True:
                    time.sleep(interval)
                    if time.monotonic() - activity[0] > args.idle_timeout:
                        httpd.shutdown()
                        return

            threading.Thread(target=monitor, daemon=True).start()
        print("Press Ctrl+C to stop.", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.", flush=True)
        else:
            print("Idle - shutting down.", flush=True)
    for f in (args.state_file, args.log_file):
        if f:
            try:
                Path(f).unlink()
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
