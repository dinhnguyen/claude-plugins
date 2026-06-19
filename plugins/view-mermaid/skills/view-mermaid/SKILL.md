---
name: view-mermaid
description: View Mermaid diagrams from the current Claude conversation in a browser. The mermaid lives in the chat as a ```mermaid code block (text), not as a file - this skill reads each block out of the conversation, writes it to a .mmd file, and serves them rendered on a local HTTP server (bundled mermaid.js, fully offline) bound to 0.0.0.0, printing local + Tailscale URLs so the diagrams open on this machine or another device on the tailnet. The page lists every diagram (newest first), renders the newest by default, lets you pick any from the list, copy its source, and open one fullscreen in a new tab with zoom + pan. Use when the user types /view-mermaid, or asks to view / open / render a mermaid chart or diagram in the browser, see a diagram bigger or fullscreen, or says "xem mermaid", "mở sơ đồ trên trình duyệt", "xem biểu đồ to hơn", "render cái diagram này". After the first /view-mermaid in a conversation, also treat a later bare "xem" / "view" / "render nốt" as a request to append the newest diagram to the same running viewer and refresh - without retyping /view-mermaid.
---

# View Mermaid

## What this does

The user produced (or pasted) one or more Mermaid diagrams in the conversation as
```` ```mermaid ```` blocks. Those are just text in the chat - no file exists. This
skill reads the mermaid source out of the conversation, writes each block to a
`.mmd` file, and starts a small Python server that renders them in the browser.

The user does NOT create any file. Reading the mermaid text from conversation
context and writing the `.mmd` files is this skill's job.

## What to render (default scope)

Write **every** ```` ```mermaid ```` block currently in the conversation, in order of
appearance, so the page's list is complete. The newest is shown first and selected
by default. If the user clearly wants only one specific diagram, write just that one.

## Server location

The server script is `scripts/serve.py` in this skill, normally installed at:

```
/Users/dinhnguyen/.claude/skills/view-mermaid/scripts/serve.py
```

Pure stdlib `python3`, no dependencies, no `uv`. `mermaid.min.js` is bundled in
`assets/` and served by the script itself, so diagrams render with no internet.

## Workflow

### 1. Pick a working dir (once per conversation)

Choose one directory and reuse the exact same path for every `/view-mermaid` in
this conversation (so re-invoking adds to the same running server). Prefer your
session scratchpad, e.g. `<scratchpad>/mermaid-view/`. Create it with `mkdir -p`.

### 2. Write each mermaid block to a `.mmd` file

For each block, strip the ```` ```mermaid ```` / ```` ``` ```` fences and write only
the diagram source. Number files in appearance order so the newest sorts to the top:

```bash
WORK=/abs/path/chosen/once            # the dir from step 1
cat > "$WORK/03-component-architecture.mmd" <<'MMD'
flowchart TD
  A --> B
MMD
```

Use a zero-padded numeric prefix (`01-`, `02-`, ...) and a short slug. The prefix
is stripped for display ("03-component-architecture" shows as "component
architecture"). Write oldest first, newest last.

### 3. Start the server (or reuse the running one)

Run this once per invocation, after writing the files. It reuses the server if one
is already up for this working dir (the server re-reads the dir each request, so a
browser refresh is enough); otherwise it starts one on a free port:

```bash
WORK=/abs/path/chosen/once
SERVE="$HOME/.claude/skills/view-mermaid/scripts/serve.py"
H=$(printf %s "$WORK" | md5)
STATE="/tmp/view-mermaid-$H.state"; LOG="/tmp/view-mermaid-$H.log"

if [ -f "$STATE" ] && source "$STATE" && kill -0 "${VM_PID:-0}" 2>/dev/null; then
  echo "reuse port $VM_PORT - refresh the browser"
  grep -E 'local|lan|tailscale' "$LOG"
else
  PORT=$(python3 -c "import socket;s=socket.socket();s.bind(('',0));p=s.getsockname()[1];s.close();print(p)")
  nohup python3 "$SERVE" --source-dir "$WORK" --port "$PORT" --bind 0.0.0.0 \
    --title "Mermaid diagrams" --idle-timeout 180 --state-file "$STATE" --log-file "$LOG" \
    >"$LOG" 2>&1 &
  VM_PID=$!; disown
  printf 'VM_PID=%s\nVM_PORT=%s\n' "$VM_PID" "$PORT" > "$STATE"
  sleep 1
  grep -E 'local|lan|tailscale' "$LOG"
fi
```

### 4. Relay the URLs as clickable links

Read the `local:` / `lan:` / `tailscale:` lines the script printed and relay them
to the user as **clickable markdown links** (`[url](url)`). Do NOT wrap URLs in
inline code (`` `url` ``) or fenced blocks - that breaks the click target in most
renderers. Only show URLs the script actually printed; do not invent them. Include
the Tailscale URL only if it appeared (it is absent when the tailnet is down).

### 5. Adding more / stopping

- **More diagrams later**: write more `.mmd` files into the same `$WORK`, then tell
  the user to refresh. The server picks them up with no restart.
- **Auto-stop**: the open page sends a heartbeat every 30s; the server shuts itself
  down ~180s after the last tab closes, then removes its own `$STATE`/`$LOG`. So
  orphaned servers do not pile up. (Reuse in step 3 still works while it is alive.)
- **Stop now**: `source "$STATE" && kill "$VM_PID"` (or kill the background shell).

## Re-view with just "xem" (after the first run)

Once `/view-mermaid` has run in this conversation, remember `$WORK`. After that,
treat a lightweight cue - "xem", "xem đi", "xem cái này", "view", "render nốt",
"thêm vào" - as "append the newest diagram and refresh", WITHOUT re-running the
full workflow and WITHOUT making the user retype `/view-mermaid`.

1. Take the ```` ```mermaid ```` block(s) from your most recent message (the diagram
   the user is reacting to) and append each as the next-numbered file in `$WORK`:

   ```bash
   WORK=/abs/path/remembered
   N=$(printf '%02d' $(( $(ls "$WORK"/*.mmd 2>/dev/null | wc -l) + 1 )))
   cat > "$WORK/$N-<slug>.mmd" <<'MMD'
   <diagram source, fences stripped>
   MMD
   ```

   Numbering by current file count keeps it append-only - no renaming existing
   files, no duplicates. The new one gets the newest mtime, so it lands on top.

2. Check the server is still alive (it may have hit the idle auto-stop):

   ```bash
   H=$(printf %s "$WORK" | md5); STATE="/tmp/view-mermaid-$H.state"
   if [ -f "$STATE" ] && source "$STATE" && kill -0 "${VM_PID:-0}" 2>/dev/null; then
     echo "alive on $VM_PORT - just refresh"
   else
     echo "server gone - restart via step 3 (URL will change)"
   fi
   ```

3. If alive: tell the user to **refresh** (the new diagram is on top, already
   selected). If it had auto-stopped: restart per step 3 and relay the new URL.

This is the only "automatic" behavior - the very first view in a conversation
still needs an explicit `/view-mermaid`.

## What the page provides

- A list of all diagrams, **newest on top**; the newest renders by default; click
  any item to render it (client-side, no reload).
- **Diagram / Source tabs.** Diagram tab shows an **Open fullscreen** button;
  Source tab shows a **Copy source** button.
- **Fullscreen** (`/full?name=<file>`) opens one diagram in a new tab with wheel
  zoom (toward the cursor), drag to pan, `-` / `Fit` / `+` buttons, and `0` to fit.
- **Light/dark toggle** (top-right button) overrides the OS theme and is remembered
  in `localStorage`; it recolors both the page and the diagram. Renders fully offline.

## Script options

| Flag | Default | Notes |
|------|---------|-------|
| `--source-dir` | (required) | Directory of `*.mmd` files. |
| `--port` | `0` | `0` picks a free port; the script prints it. |
| `--bind` | `0.0.0.0` | Use `127.0.0.1` to keep it local-only. |
| `--assets-dir` | `../assets` | Where `mermaid.min.js` lives. |
| `--title` | `Mermaid diagrams` | Page heading. |
| `--idle-timeout` | `180` | Auto-stop after N seconds with no open tab (`0` = never). |
| `--state-file` | none | Removed on shutdown (keeps reuse state clean). |
| `--log-file` | none | Removed on shutdown. |

## Troubleshooting

- **A diagram shows "[render failed]"**: the mermaid source has a syntax error.
  Open the Source tab to inspect it; fix the `.mmd` file and refresh.
- **Tailscale URL missing**: the daemon isn't running. `tailscale status` to check;
  the URL only appears when `tailscale ip -4` returns an address.
- **Diagrams blank**: confirm `assets/mermaid.min.js` exists next to the script
  (`/assets/mermaid.min.js` should return 200). It is required for offline render.
- **Port already in use**: the script picks a free port itself; if you passed an
  explicit `--port`, drop it or choose another.
