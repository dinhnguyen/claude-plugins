# Định Nguyễn 's Claude Code plugins

Personal Claude Code plugin marketplace.

## Install the marketplace

```text
/plugin marketplace add dinhnguyen/claude-plugins
```

Then browse + install plugins:

```text
/plugin install brainstorm-preview@dinhnn-claude-plugins
```

## Plugins

### brainstorm-preview

Serve `docs/superpowers/{specs,plans}/*.md` as styled HTML on a Tailscale-reachable HTTP server so spec/plan drafts can be reviewed from any device on the same tailnet. Renders Mermaid + Graphviz diagrams client-side via CDN. Auto-invokes right after `superpowers:brainstorming` or `superpowers:writing-plans` so the freshly-written doc gets a one-click review URL.

Requires `uv` (or `python3` + `pip install markdown pygments`).

See [`plugins/brainstorm-preview/skills/brainstorm-preview/SKILL.md`](plugins/brainstorm-preview/skills/brainstorm-preview/SKILL.md).

### pr-via

Open a GitHub pull request by dispatching the repo's `create-pr.yml` workflow via `gh` CLI. Synthesizes a Conventional-Commits title + `Summary` / `Test plan` body from the commit range so the PR has real content instead of the workflow's auto-generated default.

Requires a `.github/workflows/create-pr.yml` `workflow_dispatch` in the target repo. See [`plugins/pr-via/skills/pr-via/SKILL.md`](plugins/pr-via/skills/pr-via/SKILL.md).

### rabbit-pr

Address CodeRabbit (or similar bot) review comments on a GitHub PR end-to-end: fetch inline + review-body comments, skip resolved threads + already-replied items, build a checklist, verify each finding against current code, apply fixes, push, batch-reply, and resolve threads via GraphQL.

Requires `gh` CLI. See [`plugins/rabbit-pr/skills/rabbit-pr/SKILL.md`](plugins/rabbit-pr/skills/rabbit-pr/SKILL.md).

### darkfin-slides

Build dark fintech / blockchain PowerPoint decks from 29 slate-palette HTML slide templates (title, problem, KPI grids, pricing, roadmap, scoring tiers, horizontal + 3 vertical timeline variants, and more), converted to `.pptx` via Playwright + PptxGenJS. Bundles cyan icon PNGs, gradient step-number PNGs, and pre-rendered glow backgrounds. Default palette is slate; custom palettes via the bundled asset scripts.

See [`plugins/darkfin-slides/skills/darkfin-slides/SKILL.md`](plugins/darkfin-slides/skills/darkfin-slides/SKILL.md).

### view-mermaid

View Mermaid diagrams from the current Claude conversation in a browser. Reads each Mermaid code block in the chat, writes it to a `.mmd` file, and serves them rendered on a Tailscale-reachable HTTP server with bundled `mermaid.js` (fully offline, no CDN). The page lists every diagram (newest first), renders the newest by default, and adds a light/dark toggle, copyable source, and per-diagram fullscreen with zoom + pan. The server auto-stops ~3 minutes after the last browser tab closes. Trigger with `/view-mermaid`.

Requires `python3` (standard library only). See [`plugins/view-mermaid/skills/view-mermaid/SKILL.md`](plugins/view-mermaid/skills/view-mermaid/SKILL.md).

## License

MIT — see [LICENSE](LICENSE).
