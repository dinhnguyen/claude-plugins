#!/usr/bin/env python3
"""
view-mermaid: serve every *.mmd file in a source dir as rendered Mermaid diagrams.

Index page (`/`): a list of every .mmd diagram (newest on top) plus a panel that
renders the selected one, with a Diagram/Source tab, a copy button, and a button
to open the diagram fullscreen in a new tab. Fullscreen (`/full?name=<file>`)
shows a single diagram with wheel-zoom and drag-pan.

The list is rebuilt per request, so adding/editing .mmd files and refreshing is
enough — no restart. Mermaid is served from a bundled mermaid.min.js on this same
server, so it renders fully offline (no CDN). Binds to 0.0.0.0 so peers on the
same Tailscale tailnet can reach it.

Usage:
    python3 scripts/serve.py --source-dir <dir> [--port 0] [--bind 0.0.0.0]
                             [--assets-dir <dir>] [--title "..."]
"""
from __future__ import annotations

import argparse
import html
import http.server
import json
import re
import socket
import socketserver
import subprocess
import sys
import threading
import time
from functools import partial
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

LIGHT_VARS = (
    "--bg: #fdfcf8; --fg: #1a1a1a; --muted: #6a6a6a; --accent: #2563eb;"
    " --code-bg: #f1efe7; --border: #e3e0d2; --card: #ffffff; --row-hover: #f6f3e7;"
)
DARK_VARS = (
    "--bg: #16181c; --fg: #e7e5dc; --muted: #9a9a9a; --accent: #93c5fd;"
    " --code-bg: #1f2126; --border: #2a2c30; --card: #1b1e23; --row-hover: #1c1f24;"
)
# Default = light. The OS dark preference applies only when no explicit theme is
# chosen (:root:not([data-theme])). An explicit data-theme on <html> always wins.
ROOT_VARS = (
    ":root {" + LIGHT_VARS + "}\n"
    "@media (prefers-color-scheme: dark) { :root:not([data-theme]) {" + DARK_VARS + "} }\n"
    ':root[data-theme="dark"] {' + DARK_VARS + "}\n"
) + """
.theme-switch { background: none; border: 0; padding: 0; cursor: pointer; line-height: 0; }
.theme-switch .track { position: relative; display: block; width: 46px; height: 26px; border-radius: 999px; background: var(--muted); transition: background .2s; }
.theme-switch.is-dark .track { background: var(--accent); }
.theme-switch .knob { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; display: flex; align-items: center; justify-content: center; transition: left .2s; box-shadow: 0 1px 3px rgba(0,0,0,.4); }
.theme-switch.is-dark .knob { left: 23px; }
.theme-switch .ico { display: none; width: 12px; height: 12px; }
.theme-switch .ico svg { width: 12px; height: 12px; display: block; }
.theme-switch .sun { color: #f59e0b; }
.theme-switch .moon { color: #475569; }
.theme-switch:not(.is-dark) .sun { display: block; }
.theme-switch.is-dark .moon { display: block; }
"""

# Applied inline in <head> so the chosen theme paints with no flash.
NOFLASH = (
    '<script>try{var _t=localStorage.getItem("vm-theme");'
    'if(_t)document.documentElement.setAttribute("data-theme",_t);}catch(e){}</script>'
)

# Light/dark toggle rendered as a sliding switch with a sun (light) / moon (dark)
# icon in the knob. State is driven by an `is-dark` class set in vmInitTheme.
SWITCH_HTML = (
    '<button id="themebtn" class="theme-switch" type="button" role="switch"'
    ' aria-label="Toggle light / dark" title="Light / dark">'
    '<span class="track"><span class="knob">'
    '<span class="ico sun"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="4"/>'
    '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2'
    'M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></span>'
    '<span class="ico moon"><svg viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></span>'
    '</span></span></button>'
)

# Shared theme helpers + toggle wiring. Both pages include this, then pass their
# own re-render callback to vmInitTheme so diagrams recolor on toggle.
THEME_JS = """
function vmIsDark() {
  const t = document.documentElement.getAttribute("data-theme");
  if (t) return t === "dark";
  return matchMedia("(prefers-color-scheme: dark)").matches;
}
function vmMermaidTheme() { return vmIsDark() ? "dark" : "default"; }
function vmInitTheme(onChange) {
  const btn = document.getElementById("themebtn");
  function reflect() {
    if (!btn) return;
    const dark = vmIsDark();
    btn.classList.toggle("is-dark", dark);
    btn.setAttribute("aria-checked", dark ? "true" : "false");
  }
  reflect();
  if (btn) btn.addEventListener("click", () => {
    const next = vmIsDark() ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("vm-theme", next); } catch (e) {}
    reflect();
    if (onChange) onChange();
  });
}
"""

PAGE_CSS = ROOT_VARS + """
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg); }
body { font: 16px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, Roboto, sans-serif; }
main { margin: 0; padding: 22px 28px 56px; }
nav.top { padding: 12px 24px; border-bottom: 1px solid var(--border); display: flex; gap: 16px; align-items: center; }
nav.top a { color: var(--fg); text-decoration: none; font-weight: 600; }
nav.top .brand { font-size: 1.05rem; }
nav.top .theme-switch { margin-left: auto; }
.count { color: var(--muted); font-size: 0.85em; margin: 0 0 18px; }
.wrap { display: grid; grid-template-columns: 290px minmax(0, 1fr); gap: 22px; align-items: start; }
ol.mmlist { list-style: none; margin: 0; padding: 0; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; position: sticky; top: 16px; }
ol.mmlist li { padding: 11px 14px; cursor: pointer; border-bottom: 1px solid var(--border); font-size: 0.92em; line-height: 1.3; word-break: break-word; }
ol.mmlist li:last-child { border-bottom: 0; }
ol.mmlist li:hover { background: var(--row-hover); }
ol.mmlist li.active { background: var(--accent); color: #fff; font-weight: 600; }
ol.mmlist .ord { color: var(--muted); font-size: 0.85em; margin-right: 7px; }
ol.mmlist li.active .ord { color: #fff; }
.panel { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; min-width: 0; }
.toolbar { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; margin-bottom: 16px; border-bottom: 2px solid var(--border); flex-wrap: wrap; }
.tabs { display: flex; gap: 4px; }
.tab { background: transparent; border: 0; border-bottom: 2px solid transparent; margin-bottom: -2px; color: var(--muted); padding: 9px 18px; cursor: pointer; font: inherit; font-size: 0.92em; font-weight: 600; }
.tab:hover:not(.active) { color: var(--fg); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.actions { display: flex; gap: 8px; padding-bottom: 8px; }
.actions button { background: var(--card); border: 1px solid var(--border); color: var(--fg); padding: 6px 13px; border-radius: 7px; cursor: pointer; font: inherit; font-size: 0.85em; }
.actions button:hover { background: var(--row-hover); }
.actions button[hidden] { display: none; }
.panel h2 { font-size: 1.05rem; margin: 0 0 12px; word-break: break-word; }
.tabpane[hidden] { display: none; }
#mmrender { display: flex; justify-content: center; overflow-x: auto; min-height: 60px; }
#mmrender svg { max-width: 100%; height: auto; }
#pane-source pre { background: var(--code-bg); border: 1px solid var(--border); padding: 14px 16px; border-radius: 8px; overflow-x: auto; margin: 0; }
code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 0.86em; }
.err { color: #b91c1c; white-space: pre-wrap; background: var(--code-bg); padding: 12px 14px; border-radius: 8px; }
p.empty { color: var(--muted); }
@media (max-width: 760px) { main { padding: 18px 14px 48px; } .wrap { grid-template-columns: 1fr; } ol.mmlist { position: static; } }
"""

FULL_CSS = ROOT_VARS + """
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; background: var(--bg); color: var(--fg); overflow: hidden;
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, Roboto, sans-serif; }
.fbar { position: fixed; top: 0; left: 0; right: 0; height: 48px; display: flex; align-items: center;
  justify-content: space-between; gap: 12px; padding: 0 16px; background: var(--card);
  border-bottom: 1px solid var(--border); z-index: 10; }
.fbar .ttl { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fbar .hint { color: var(--muted); font-size: 0.82em; }
.fbtns { display: flex; gap: 8px; align-items: center; }
.fbtns button:not(.theme-switch) { background: var(--bg); border: 1px solid var(--border); color: var(--fg);
  width: 34px; height: 30px; border-radius: 7px; cursor: pointer; font: inherit; font-size: 0.95em; }
.fbtns button:not(.theme-switch):hover { background: var(--row-hover); }
.fbtns .reset { width: auto; padding: 0 12px; }
#viewport { position: absolute; top: 48px; left: 0; right: 0; bottom: 0; overflow: hidden;
  cursor: grab; touch-action: none; }
#stage { position: absolute; top: 0; left: 0; transform-origin: 0 0; }
#stage svg { max-width: none; height: auto; display: block; }
.err { color: #b91c1c; white-space: pre-wrap; padding: 24px; }
"""

PAGE_SCRIPT = """
(function () {
  const out = document.getElementById("mmrender");
  const ttl = document.getElementById("mmtitle");
  const src = document.getElementById("mmsrc");
  const list = document.getElementById("mmlist");
  const copyBtn = document.getElementById("copybtn");
  const fullBtn = document.getElementById("fullbtn");
  const tabs = [...document.querySelectorAll(".tab")];
  const panes = { diagram: document.getElementById("pane-diagram"), source: document.getElementById("pane-source") };
  let current = 0, seq = 0;
  mermaid.initialize({ startOnLoad: false, theme: vmMermaidTheme() });
  function setTab(name) {
    tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === name));
    Object.keys(panes).forEach(k => { panes[k].hidden = k !== name; });
    fullBtn.hidden = name !== "diagram";
    copyBtn.hidden = name !== "source";
  }
  tabs.forEach(t => t.addEventListener("click", () => setTab(t.dataset.tab)));
  async function show(i) {
    if (!MM.length) return;
    current = i;
    [...list.children].forEach((li, idx) => li.classList.toggle("active", idx === i));
    const d = MM[i];
    ttl.textContent = d.title;
    src.textContent = d.src;
    out.innerHTML = "";
    try {
      const { svg, bindFunctions } = await mermaid.render("mmg" + (seq++), d.src);
      out.innerHTML = svg;
      if (bindFunctions) bindFunctions(out);
    } catch (e) {
      const div = document.createElement("div");
      div.className = "err";
      div.textContent = "[render failed] " + (e && e.message ? e.message : e);
      out.appendChild(div);
    }
  }
  function copyText(text, btn) {
    const ok = () => { const o = btn.textContent; btn.textContent = "Copied"; setTimeout(() => { btn.textContent = o; }, 1200); };
    const fallback = () => {
      const ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.focus(); ta.select();
      try { document.execCommand("copy"); ok(); } catch (e) {}
      document.body.removeChild(ta);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(ok).catch(fallback);
    } else { fallback(); }
  }
  copyBtn.addEventListener("click", () => copyText(MM[current].src, copyBtn));
  fullBtn.addEventListener("click", () => window.open("/full?name=" + encodeURIComponent(MM[current].name), "_blank"));
  [...list.children].forEach((li, idx) => li.addEventListener("click", () => show(idx)));
  setTab("diagram");
  if (MM.length) show(0);
  vmInitTheme(() => { mermaid.initialize({ startOnLoad: false, theme: vmMermaidTheme() }); if (MM.length) show(current); });
  const ping = () => { fetch("/heartbeat", { cache: "no-store" }).catch(() => {}); };
  ping();
  setInterval(ping, 30000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) ping(); });
})();
"""

FULL_SCRIPT = """
(function () {
  mermaid.initialize({ startOnLoad: false, theme: vmMermaidTheme() });
  const vp = document.getElementById("viewport");
  const stage = document.getElementById("stage");
  let scale = 1, tx = 0, ty = 0;
  function apply() { stage.style.transform = "translate(" + tx + "px," + ty + "px) scale(" + scale + ")"; }
  function natSize() {
    const svg = stage.querySelector("svg");
    if (!svg) return null;
    const vb = svg.viewBox && svg.viewBox.baseVal;
    const r = svg.getBoundingClientRect();
    return { w: (vb && vb.width) ? vb.width : r.width, h: (vb && vb.height) ? vb.height : r.height };
  }
  function fit() {
    const r = vp.getBoundingClientRect();
    const n = natSize();
    if (!n || !n.w || !n.h) { scale = 1; tx = 0; ty = 0; apply(); return; }
    scale = Math.min(r.width / n.w, r.height / n.h) * 0.95;
    if (!isFinite(scale) || scale <= 0) scale = 1;
    tx = (r.width - n.w * scale) / 2;
    ty = (r.height - n.h * scale) / 2;
    apply();
  }
  function zoomAt(cx, cy, f) {
    const ns = Math.min(16, Math.max(0.05, scale * f));
    tx = cx - (cx - tx) * (ns / scale);
    ty = cy - (cy - ty) * (ns / scale);
    scale = ns; apply();
  }
  vp.addEventListener("wheel", e => {
    e.preventDefault();
    const r = vp.getBoundingClientRect();
    zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.1 : 1 / 1.1);
  }, { passive: false });
  let drag = false, lx = 0, ly = 0;
  vp.addEventListener("pointerdown", e => { drag = true; lx = e.clientX; ly = e.clientY; vp.setPointerCapture(e.pointerId); vp.style.cursor = "grabbing"; });
  vp.addEventListener("pointermove", e => { if (!drag) return; tx += e.clientX - lx; ty += e.clientY - ly; lx = e.clientX; ly = e.clientY; apply(); });
  vp.addEventListener("pointerup", () => { drag = false; vp.style.cursor = "grab"; });
  vp.addEventListener("pointercancel", () => { drag = false; vp.style.cursor = "grab"; });
  document.querySelectorAll("[data-z]").forEach(b => b.addEventListener("click", () => {
    const r = vp.getBoundingClientRect();
    if (b.dataset.z === "in") zoomAt(r.width / 2, r.height / 2, 1.25);
    else if (b.dataset.z === "out") zoomAt(r.width / 2, r.height / 2, 1 / 1.25);
    else fit();
  }));
  window.addEventListener("keydown", e => { if (e.key === "0") fit(); });
  window.addEventListener("resize", fit);
  let seq = 0;
  function pinSvgSize() {
    // mermaid renders with width:100% + max-width (useMaxWidth); inside an
    // auto-width absolute stage that size is ambiguous. Pin the svg to its
    // viewBox px so fit()/zoom math is exact.
    const svg = stage.querySelector("svg");
    if (!svg) return;
    const vb = svg.viewBox && svg.viewBox.baseVal;
    if (vb && vb.width && vb.height) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      svg.style.maxWidth = "none";
      svg.style.width = vb.width + "px";
      svg.style.height = vb.height + "px";
    }
  }
  async function renderDiagram(doFit) {
    try {
      const { svg, bindFunctions } = await mermaid.render("full" + (seq++), D.src);
      stage.innerHTML = svg;
      pinSvgSize();
      if (bindFunctions) bindFunctions(stage);
      if (doFit) requestAnimationFrame(fit);
    } catch (e) {
      const div = document.createElement("div");
      div.className = "err";
      div.textContent = "[render failed] " + (e && e.message ? e.message : e);
      stage.innerHTML = "";
      stage.appendChild(div);
    }
  }
  renderDiagram(true);
  vmInitTheme(() => { mermaid.initialize({ startOnLoad: false, theme: vmMermaidTheme() }); renderDiagram(false); });
  const ping = () => { fetch("/heartbeat", { cache: "no-store" }).catch(() => {}); };
  ping();
  setInterval(ping, 30000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) ping(); });
})();
"""


def pretty_title(stem: str) -> str:
    """Drop a leading numeric prefix and turn separators into spaces."""
    stem = re.sub(r"^\d+[-_]+", "", stem)
    return stem.replace("-", " ").replace("_", " ").strip() or stem


def diagram_title(path: Path, text: str) -> str:
    """Display title: a `%% title:` comment or YAML-frontmatter `title:` (so the
    label can keep diacritics the ASCII filename drops), else the de-slugged name."""
    m = re.search(r"(?mi)^[ \t]*%%[ \t]*title:[ \t]*(.+?)[ \t]*$", text)
    if m:
        return m.group(1).strip()
    fm = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n", text, re.S)
    if fm:
        tm = re.search(r"(?mi)^[ \t]*title:[ \t]*(.+?)[ \t]*$", fm.group(1))
        if tm:
            return tm.group(1).strip().strip("\"'")
    return pretty_title(path.stem)


def list_diagrams(source: Path) -> list[Path]:
    """All *.mmd in source, newest first (mtime desc, name desc as tiebreak)."""
    if not source.is_dir():
        return []
    return sorted(source.glob("*.mmd"), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)


def _json_embed(obj) -> str:
    # json.dumps escapes quotes/newlines; the </ replace prevents </script> breakout.
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def render_index(source: Path, title: str) -> str:
    files = list_diagrams(source)
    esc_title = html.escape(title)
    if not files:
        body = '<p class="empty">No <code>*.mmd</code> files found in {}.</p>'.format(
            html.escape(str(source))
        )
        count = "0 diagrams"
        data = "[]"
    else:
        items, diagrams = [], []
        for n, p in enumerate(files, 1):
            text = p.read_text(encoding="utf-8")
            t = diagram_title(p, text)
            items.append(f'<li><span class="ord">{n}</span>{html.escape(t)}</li>')
            diagrams.append({"title": t, "src": text.strip(), "name": p.name})
        count = "{} diagram{} - newest first".format(len(files), "" if len(files) == 1 else "s")
        data = _json_embed(diagrams)
        body = (
            '<div class="wrap">'
            f'<ol class="mmlist" id="mmlist">{"".join(items)}</ol>'
            '<div class="panel">'
            '<div class="toolbar">'
            '<div class="tabs">'
            '<button class="tab active" data-tab="diagram">Diagram</button>'
            '<button class="tab" data-tab="source">Source</button>'
            '</div>'
            '<div class="actions">'
            '<button id="copybtn" hidden>Copy source</button>'
            '<button id="fullbtn">Open fullscreen</button>'
            '</div>'
            '</div>'
            '<h2 id="mmtitle"></h2>'
            '<div class="tabpane" id="pane-diagram"><div id="mmrender"></div></div>'
            '<div class="tabpane" id="pane-source" hidden><pre><code id="mmsrc"></code></pre></div>'
            '</div></div>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc_title}</title><style>{PAGE_CSS}</style>{NOFLASH}</head><body>'
        f'<nav class="top"><a href="/" class="brand">{esc_title}</a>{SWITCH_HTML}</nav>'
        f'<main><p class="count">{html.escape(count)}</p>{body}</main>'
        '<script src="/assets/mermaid.min.js"></script>'
        f'<script>const MM = {data};</script>'
        f'<script>{THEME_JS}</script>'
        f'<script>{PAGE_SCRIPT}</script>'
        '</body></html>'
    )


def render_full(source: Path, name: str) -> tuple[int, str]:
    base = Path(name).name
    f = source / base
    if not base.endswith(".mmd") or not f.is_file():
        page = (
            '<!doctype html><meta charset="utf-8">'
            f'<style>{FULL_CSS}</style><div class="err">Diagram not found: '
            f'{html.escape(base)}</div>'
        )
        return 404, page
    text = f.read_text(encoding="utf-8")
    t = diagram_title(f, text)
    data = _json_embed({"title": t, "src": text.strip()})
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{html.escape(t)}</title><style>{FULL_CSS}</style>{NOFLASH}</head><body>'
        '<div class="fbar">'
        f'<span class="ttl">{html.escape(t)}</span>'
        '<span class="hint">scroll = zoom, drag = pan</span>'
        '<span class="fbtns">'
        f'{SWITCH_HTML}'
        '<button data-z="out" title="Zoom out">&minus;</button>'
        '<button data-z="reset" class="reset" title="Fit (press 0)">Fit</button>'
        '<button data-z="in" title="Zoom in">+</button>'
        '</span>'
        '</div>'
        '<div id="viewport"><div id="stage"></div></div>'
        '<script src="/assets/mermaid.min.js"></script>'
        f'<script>const D = {data};</script>'
        f'<script>{THEME_JS}</script>'
        f'<script>{FULL_SCRIPT}</script>'
        '</body></html>'
    )
    return 200, page


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "view-mermaid/1.0"

    def __init__(self, *args, source: Path, assets: Path, title: str, activity, **kwargs):
        self.source = source
        self.assets = assets
        self.title = title
        self.activity = activity
        super().__init__(*args, **kwargs)

    def _send(self, code: int, body: bytes, ctype: str, cache: str = "no-store") -> None:
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", cache)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        self.activity[0] = time.monotonic()
        if path == "/heartbeat":
            return self._send(200, b"ok\n", "text/plain; charset=utf-8")
        if path in ("/", ""):
            page = render_index(self.source, self.title).encode("utf-8")
            return self._send(200, page, "text/html; charset=utf-8")
        if path == "/full":
            name = (parse_qs(parsed.query).get("name") or [""])[0]
            code, page = render_full(self.source, name)
            return self._send(code, page.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/assets/mermaid.min.js":
            f = self.assets / "mermaid.min.js"
            if not f.is_file():
                return self._send(404, b"mermaid.min.js not bundled", "text/plain; charset=utf-8")
            return self._send(200, f.read_bytes(), "application/javascript", cache="max-age=86400")
        if path == "/healthz":
            return self._send(200, b"ok\n", "text/plain; charset=utf-8")
        return self._send(404, b"Not found", "text/plain; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:  # noqa: N802
        sys.stderr.write(
            "[%s] %s %s\n" % (self.log_date_time_string(), self.address_string(), fmt % args)
        )


def tailscale_url(port: int) -> str | None:
    try:
        out = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
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
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description="Serve *.mmd files as rendered Mermaid diagrams.")
    p.add_argument("--source-dir", required=True, help="Directory containing *.mmd files.")
    p.add_argument("--port", type=int, default=0, help="Port (0 = pick a free one).")
    p.add_argument("--bind", default="0.0.0.0", help="Bind address (default 0.0.0.0).")
    p.add_argument(
        "--assets-dir",
        default=str(here.parent / "assets"),
        help="Directory holding mermaid.min.js (default: ../assets).",
    )
    p.add_argument("--title", default="Mermaid diagrams", help="Page title.")
    p.add_argument(
        "--idle-timeout",
        type=int,
        default=180,
        help="Auto-shutdown after N seconds with no request / heartbeat (0 = never).",
    )
    p.add_argument("--state-file", default=None, help="Remove this file on shutdown.")
    p.add_argument("--log-file", default=None, help="Remove this file on shutdown.")
    args = p.parse_args()

    source = Path(args.source_dir).resolve()
    assets = Path(args.assets_dir).resolve()
    if not (assets / "mermaid.min.js").is_file():
        sys.stderr.write(f"warn: {assets}/mermaid.min.js missing; diagrams will not render.\n")

    activity = [time.monotonic()]
    handler = partial(Handler, source=source, assets=assets, title=args.title, activity=activity)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.bind, args.port), handler) as httpd:
        port = httpd.server_address[1]
        print(f"view-mermaid serving {source} ({len(list_diagrams(source))} diagram(s))", flush=True)
        print(f"  local:     http://localhost:{port}/", flush=True)
        lan = lan_url(port)
        if lan:
            print(f"  lan:       {lan}", flush=True)
        ts = tailscale_url(port)
        if ts:
            print(f"  tailscale: {ts}", flush=True)
        else:
            print("  tailscale: (not detected - run `tailscale ip -4` to verify)", flush=True)
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
