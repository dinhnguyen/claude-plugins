---
name: brainstorm-preview
description: Serve Markdown files under `docs/` (specs/plans from `superpowers:brainstorming` and `superpowers:writing-plans`) as styled HTML on an HTTP server bound to 0.0.0.0 so the user can review them from another device on their Tailscale tailnet. Use when the user asks to "preview the spec/plan in a browser", "view the brainstorming output as HTML", "serve docs over the network", "render plans for remote review", "open the plan on my phone via tailscale". Also auto-invoke with `--latest` right after `superpowers:brainstorming` writes a spec or `superpowers:writing-plans` writes a plan, so the freshly-written doc is highlighted and a direct URL is printed — unless the user opted out.
---

# Brainstorm Preview

## Overview

Spins up a single-file Python web server that walks the project's `docs/` tree, renders every `*.md` file to styled HTML (with client-side rendering for ```dot / ```mermaid blocks via CDN), and prints the URLs the user can open — including the Tailscale tailnet URL so peers on the same tailnet can reach it.

## When to use

- User just finished `superpowers:brainstorming` or `superpowers:writing-plans` and wants to review the resulting spec/plan in a browser instead of in the terminal.
- User asks to "preview", "serve", "render", or "view in browser" any `docs/` content.
- User mentions they need to look at the doc on another device (phone, tablet, second laptop) and the project machine is on Tailscale.

Do NOT use this skill when the user wants to:
- Generate a new spec/plan (that is `superpowers:brainstorming` / `superpowers:writing-plans`).
- Publish docs as a static site or to a public host.
- Edit docs (just open them in the editor).

## Auto-trigger via PostToolUse hook (recommended)

The skill description hints at auto-invocation after brainstorming/writing-plans
writes a spec or plan. In practice that hint loses to the brainstorming
workflow's "do not invoke any other skill" rule, so Claude rarely fires the
skill on its own. Make it deterministic with a `PostToolUse` hook instead.

`~/.claude/hooks/brainstorm-preview-trigger.sh`:

```bash
#!/usr/bin/env bash
set -e
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')
FP=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')

case "$TOOL" in Write|Edit|MultiEdit) ;; *) exit 0 ;; esac
case "$FP" in
  */docs/superpowers/specs/*.md|*/docs/superpowers/plans/*.md) ;;
  *) exit 0 ;;
esac

ROOT="${FP%%/docs/superpowers/*}"
[ -d "$ROOT/docs" ] || exit 0

# Per-project state so multiple simultaneous projects each get their own port
ROOT_HASH=$(printf '%s' "$ROOT" | md5)
STATE_FILE="/tmp/brainstorm-preview-${ROOT_HASH}.state"
LOG="/tmp/brainstorm-preview-${ROOT_HASH}.log"

# If server for THIS project root is already running, do nothing
if [ -f "$STATE_FILE" ]; then
  source "$STATE_FILE"
  if [ -n "${PREVIEW_PID:-}" ] && kill -0 "$PREVIEW_PID" 2>/dev/null; then
    exit 0
  fi
fi

# Find a free port
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); p=s.getsockname()[1]; s.close(); print(p)")

nohup uv run \
  ~/.claude/skills/brainstorm-preview/scripts/serve.py \
  --docs-root "$ROOT" --port "$PORT" --latest \
  --idle-timeout 180 --state-file "$STATE_FILE" --log-file "$LOG" \
  >"$LOG" 2>&1 &
PREVIEW_PID=$!
disown

printf 'PREVIEW_PID=%s\nPREVIEW_PORT=%s\nPREVIEW_ROOT=%s\n' \
  "$PREVIEW_PID" "$PORT" "$ROOT" > "$STATE_FILE"
```

`~/.claude/settings.json` (add a second entry alongside the existing notifier):

```json
"PostToolUse": [
  { "matcher": "Write|Edit|MultiEdit",
    "hooks": [{ "type": "command",
                "command": "/Users/<you>/.claude/hooks/brainstorm-preview-trigger.sh" }] }
]
```

After the hook spawns the server, retrieve the URLs from the per-project log.
The log path is `/tmp/brainstorm-preview-<HASH>.log` where `<HASH>` is
`$(printf '%s' "$ROOT" | md5)`. To find it, run:

```bash
ROOT_HASH=$(printf '%s' /path/to/project | md5)
tail -20 "/tmp/brainstorm-preview-${ROOT_HASH}.log"
```

Or list all active state files to find ports for all running projects:

```bash
cat /tmp/brainstorm-preview-*.state 2>/dev/null
```

Relay the URLs as clickable markdown links. The hook does nothing when the
server for that project root is already running — avoids restart churn.

## Workflow

1. Confirm the project root contains `docs/` (preferably with `docs/superpowers/specs/` and/or `docs/superpowers/plans/`). If not, tell the user and stop.
2. Decide which startup flag to pass:
   - **Auto-invoked right after brainstorming/writing-plans wrote a file in this turn** → pass `--latest` (or `--open <relpath>` if the exact file path is already known).
   - **User invoked manually with no specific file in mind** → no extra flag; the index is enough.
   - **Server already running on this port** → skip restart; just remind the user of the URLs and (optionally) hand them the `/view/<relpath>` URL for the new doc.
3. Start the server in the background from the project root so the conversation stays interactive:

   ```bash
   PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); p=s.getsockname()[1]; s.close(); print(p)")
   uv run /Users/dinhnguyen/.claude/skills/brainstorm-preview/scripts/serve.py \
     --docs-root "$PWD" --port "$PORT" --idle-timeout 180 [--latest | --open <docs/relpath>]
   ```

   Use Bash with `run_in_background: true` so the server doesn't block. The script prints local, LAN, Tailscale, and (when `--latest` / `--open` is set) `latest:` URLs to stdout on startup. Using a dynamically allocated port avoids collisions when multiple project servers are running simultaneously.
4. Read the first ~20 lines of the background process's output (via BashOutput on the started shell) and relay the printed URLs to the user as **clickable markdown links** (`[url](url)`). Do not wrap URLs in inline code (`` `url` ``) or fenced code blocks — those break the click target in most renderers. Include the Tailscale URL if it appears. Do not invent or rewrite URLs — only show what the script actually printed.
5. The server **auto-stops ~180s after the last open tab closes** (the page heartbeats every 30s); pass `--state-file`/`--log-file` so it removes its own state/log on exit. If the user wants it stopped immediately, KillShell the background process.

### Auto-trigger handoff

When this skill runs right after brainstorming or writing-plans, relay the URLs as clickable markdown links — **never** wrap a URL in inline code (`` `...` ``) or a fenced code block, because most renderers (Claude Code, IDE terminals) will not make a code-styled URL clickable.

**URL format — the `/view/` prefix is followed by the path relative to `--docs-root` (the project root), which includes the leading `docs/` segment.** Do NOT strip `docs/`. A spec at `docs/superpowers/specs/foo.md` is served at `http://host:8765/view/docs/superpowers/specs/foo.md`, never at `/view/superpowers/specs/foo.md` (that path returns 404).

The natural handoff is:

> Spec/plan written to `docs/superpowers/specs/foo.md`. Preview server up — click to review:
> - local: [http://localhost:8765/view/docs/superpowers/specs/foo.md](http://localhost:8765/view/docs/superpowers/specs/foo.md)
> - tailscale: [http://&lt;ts-ip&gt;:8765/view/docs/superpowers/specs/foo.md](http://<ts-ip>:8765/view/docs/superpowers/specs/foo.md)

Pull the exact `latest:` URLs out of the script's startup output whenever possible — the script emits the correct path so you don't have to construct it. Do not invent the URL. Render each URL with markdown link syntax (`[label-or-url](url)`) so it stays clickable.

If the server is already running from a previous turn and the script's `latest:` output is not available, build the URL by **prefixing `/view/` directly to the relative path of the file from the project root** (e.g., `docs/...md`). Quick verification: `curl -s -o /dev/null -w '%{http_code}\n' <url>` should return `200`, not `404`.

### Brainstorming Visual Companion — also relay a Tailscale URL

When the `superpowers:brainstorming` Visual Companion (`scripts/start-server.sh`, `node server.cjs`) starts during the same session, it emits a `server-started` JSON with a single `url` field (commonly `http://localhost:<random-port>`). Its `--url-host` flag has been known to ship a wrong/stale IP in prior runs, and the upstream plugin only prints one URL.

After the companion's start-server.sh succeeds:

1. Read the `port` field out of the `server-started` JSON.
2. Run `tailscale ip -4` (via Bash). Take the first non-empty stdout line.
3. If a Tailscale IP is returned, relay BOTH URLs to the user as clickable markdown links (do not wrap in inline code or fences), e.g.:
   > Visual companion up:
   > - local: [http://localhost:&lt;port&gt;/](http://localhost:<port>/)
   > - tailscale: [http://&lt;ts-ip&gt;:&lt;port&gt;/](http://<ts-ip>:<port>/)
4. If `tailscale ip -4` is missing or empty, just relay the original `url` field — no fabricated IP.

**Do not modify** `scripts/start-server.sh` or `scripts/server.cjs` in the brainstorming plugin to "fix" this upstream. The Tailscale URL is purely a presentation augmentation done by this conversation's agent. Skill files in the upstream plugin cache get overwritten on update.

## Script details

`scripts/serve.py` (PEP 723 inline metadata; uses `uv run` to fetch its own deps the first time):

- Walks `<docs-root>/docs` for every `*.md` file. Groups them in the index as **Specs** (`docs/superpowers/specs/...`), **Plans** (`docs/superpowers/plans/...`), and **Other docs** (everything else), sorted newest first by mtime.
- Renders Markdown with `markdown` + `pygments` (fenced code, tables, TOC, codehilite, task-list checkboxes).
- Mermaid blocks (` ```mermaid `) render client-side via `cdn.jsdelivr.net/npm/mermaid@10`.
- Graphviz/dot blocks (` ```dot ` or ` ```graphviz `) render client-side via `cdn.jsdelivr.net/npm/d3-graphviz@5` + `@hpcc-js/wasm`.
- Binds to `0.0.0.0` by default so Tailscale peers reach it.
- Tailscale URL is discovered by shelling out to `tailscale ip -4`. If `tailscale` isn't installed or returns no addresses, the script prints `(not detected — run \`tailscale ip -4\` to verify)` and continues.

### Options

| Flag | Default | Notes |
|------|---------|-------|
| `--port` | `8765` | Override via flag or `PORT` env var. |
| `--docs-root` | `.` | Project root that contains `docs/`. |
| `--bind` | `0.0.0.0` | Set to `127.0.0.1` to keep the server local-only. |

### Fallback if `uv` is missing

If `uv` is not on PATH, run with the system Python after installing the two deps once:

```bash
pip install markdown pygments
python3 /Users/dinhnguyen/.claude/skills/brainstorm-preview/scripts/serve.py --docs-root "$PWD"
```

## Troubleshooting

- **Port already in use**: re-run with `--port <other>`. Common collisions: 3000 (Next.js), 5173 (Vite), 4000 (Jekyll).
- **Tailscale URL missing**: run `tailscale status` to confirm the tailnet is up; the script only reports the URL if `tailscale ip -4` returns at least one address.
- **Diagrams not rendering**: the viewing device needs internet (CDN). If the user is offline, the ```dot / ```mermaid blocks fall back to plain code blocks.
- **403 on `/view/...`**: the requested path tried to escape `--docs-root`. Move the file under `docs/` or rerun with a higher `--docs-root`.

## Limitations

- No live reload. After editing a doc, refresh the browser. (If the user requests auto-reload, that's a follow-up — current scope is intentionally minimal.)
- Only `.md` is served. Images embedded in markdown that reference relative paths won't load — the server has no static asset route by design.
- Index is built per-request, so very large `docs/` trees (>10k files) will be slow. None of the brainstorming output dirs come close.
