# Changelog

Updates across all plugins, newest first. Each plugin is versioned independently;
follow its link for detailed release notes.

## 2026-11-08

- **[view-mermaid 1.3.0](plugins/view-mermaid/CHANGELOG.md)** — Replace Mermaid.js with bundled Pele 1.13.0 while keeping offline rendering. Theme changes preserve fullscreen zoom/pan; add renderer delivery tests and portable server paths.
- **[brainstorm-preview 1.0.1](plugins/brainstorm-preview/CHANGELOG.md)** — Remove personal and fixed installation paths from server instructions; make the hook command home-relative and document updating its path after plugin upgrades.

## 2026-07-21

- **[diffsense 1.2.0](plugins/diffsense/CHANGELOG.md)** — Add a deeper review method covering intent, ground truth, blast radius, consistency, and finding verification.
- **[diffsense 1.1.0](plugins/diffsense/CHANGELOG.md)** — Align structured review output with updated CodeRabbit conventions.
- **[diffsense 1.0.0](plugins/diffsense/CHANGELOG.md)** — Introduce structured reviews for local diffs and GitHub PRs, with severity-tagged findings, proposed fixes, and AI-agent prompts.

## 2026-06-19

- **[view-mermaid 1.2.0](plugins/view-mermaid/CHANGELOG.md)** — Fix fullscreen sizing and fit; add `%% title:` labels, an icon-based theme switch, and compact navigation.
- **[view-mermaid 1.1.0](plugins/view-mermaid/CHANGELOG.md)** — Accept follow-ups such as "xem" to append diagrams to the existing viewer.
- **[view-mermaid 1.0.0](plugins/view-mermaid/CHANGELOG.md)** — Introduce the offline conversation diagram viewer with source copying, fullscreen zoom/pan, light/dark themes, and Tailscale access.
- **[pr-via](plugins/pr-via/CHANGELOG.md)** — Bundle the `create-pr.yml` workflow template; plugin version remains 1.0.0.

## 2026-05-14

- **[brainstorm-preview](plugins/brainstorm-preview/CHANGELOG.md)** — Use per-project dynamic ports to avoid collisions between simultaneous projects; plugin version remains 1.0.0.
- **[darkfin-slides 1.0.0](plugins/darkfin-slides/CHANGELOG.md)** — Introduce 29 dark fintech/blockchain slide templates, bundled visual assets, customizable colors, and PowerPoint export.

## 2026-05-11

- **[brainstorm-preview 1.0.0](plugins/brainstorm-preview/CHANGELOG.md)** — Introduce Markdown spec/plan previews with diagram rendering, latest-document links, and Tailscale access; document automatic startup via a PostToolUse hook.
- **[pr-via 1.0.0](plugins/pr-via/CHANGELOG.md)** — Create GitHub pull requests through workflow dispatch with generated titles, summaries, and test plans.
- **[rabbit-pr 1.0.0](plugins/rabbit-pr/CHANGELOG.md)** — Verify and address automated PR review comments, apply fixes, and reply to and resolve review threads.
