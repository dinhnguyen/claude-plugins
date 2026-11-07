# Changelog

## [1.3.0] - 2026-11-08

### Changed

- Replace Mermaid.js with bundled Pele 1.13.0 for rendering Mermaid diagrams. The viewer remains fully offline and requires only Python's standard library at runtime.
- Apply light/dark diagram colors through CSS variables without re-rendering, preserving fullscreen zoom and pan when switching themes.
- Document Pele compatibility differences, including its own layouts and theming and lack of HTML label support.

### Fixed

- Resolve the bundled server relative to the loaded skill directory instead of a hard-coded personal path or fixed installation location.

### Added

- Bundle Pele's license notices alongside the browser renderer.
- Add automated tests for local renderer delivery, page asset loading, missing diagrams, unknown asset paths, and safe title/source embedding.

## [1.2.0] - 2026-06-19

### Added

- Support `%% title:` labels for diagram names.

### Changed

- Use an icon-based theme switch and more compact navigation.

### Fixed

- Correct fullscreen diagram sizing and fit behavior.

## [1.1.0] - 2026-06-19

### Added

- Support lightweight follow-ups such as "xem" to append diagrams to the existing viewer.

## [1.0.0] - 2026-06-19

### Added

- Initial conversation diagram viewer with offline rendering, diagram selection, source copying, fullscreen zoom/pan, light/dark themes, and Tailscale-accessible serving.
