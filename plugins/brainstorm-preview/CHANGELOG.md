# Changelog

## [1.0.1] - 2026-11-08

### Fixed

- Resolve the bundled server relative to the loaded skill directory instead of hard-coded personal paths or a fixed installation location.
- Use a home-relative hook command rather than a macOS-specific path.
- Document refreshing the server path in standalone hooks after plugin updates or relocation.

## [1.0.0] - 2026-05-11

### Added

- Initial Markdown spec/plan preview server with local and Tailscale URLs, diagram rendering, and latest-document links.

### Subsequent updates before 1.0.1

- Document PostToolUse hook setup for automatically starting the preview server (2026-05-11).
- Use per-project dynamic ports to avoid collisions when multiple projects are open (2026-05-14).
