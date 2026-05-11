# dinhnn Claude Code plugins

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

See [`plugins/brainstorm-preview/skills/brainstorm-preview/SKILL.md`](plugins/brainstorm-preview/skills/brainstorm-preview/SKILL.md) for details.

## License

MIT — see [LICENSE](LICENSE).
