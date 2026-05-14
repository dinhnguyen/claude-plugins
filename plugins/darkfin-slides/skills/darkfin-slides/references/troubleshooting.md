# Troubleshooting

`html2pptx` validates every slide before generating PPTX. Read the error message; apply the matching fix below.

## Error → Fix table

| Error message | Cause | Fix |
|---------------|-------|-----|
| `HTML content overflows body by Npt vertically` | Slide content taller than 405pt | Trim in order: 1) `.body { padding }` -4..-8pt → 2) `h1` font-size -2..-4pt → 3) inter-card gap/margin -2..-4pt → 4) card padding -2..-4pt → 5) drop lead/sub paragraph or shorten body text |
| `DIV element contains unwrapped text "..."` | Plain text in `<div>` or `<span>` | Wrap text in `<p>` (or `<h1>`-`<h6>`). Never put loose text in a div. |
| `Background images on DIV elements are not supported` | `background-image` on inner `<div>` | Move the `background-image` to `<body>` only. Use solid colors / borders on inner divs. |
| `CSS gradients are not supported` | `linear-gradient(...)` or `radial-gradient(...)` in CSS | Pre-render the gradient as PNG via `scripts/gen-assets.js`, reference via `<img>` or `background-image` on `<body>`. |
| `HTML dimensions must match presentation layout` | Body not exactly 720×405pt | Set `body { width: 720pt; height: 405pt; ... }` exactly. |
| `Text box "X" ends too close to bottom edge` | Last text shape inside slide too close to 405pt | Add padding-bottom to the body or shrink the final block. Minimum 0.5" margin = ~36pt. |
| `shadow.opacity can only be 0-1` | `box-shadow` alpha > 1 or unsupported syntax | Use `rgba(0,0,0,0.3)` style; keep alpha 0–1. Outer shadows only — inset shadows are skipped. |
| `Browser console: Failed to load resource: net::ERR_FILE_NOT_FOUND` | Wrong relative path to asset PNG | Slides live in `slides/`, assets in `assets/`. Use `../assets/file.png` (two dots) from the slide. |

## Quick checks before building

Before `node build.js`, verify each slide:

1. `<body style="width: 720pt; height: 405pt;">` — exact dimensions
2. `background-image` only on `<body>` (never on inner div)
3. Every visible text is inside `<p>`/`<h1>`-`<h6>`/`<ul>`/`<ol>`
4. No `linear-gradient` / `radial-gradient` in CSS
5. Font-family uses only Arial or Courier New
6. Asset paths are `../assets/<file>.png` from a slide HTML

## Iteration loop

If a slide fails:
1. Read the exact error message — it tells you which slide + which line.
2. Apply the one matching fix.
3. Re-run `node build.js`. Repeat until pass.

Do NOT batch many speculative fixes — each iteration takes ~1s per slide.

## Manual visual review

After `.pptx` builds successfully, ALWAYS recommend the user open in Keynote / PowerPoint to scan for:

- Truncated text (validator only checks overflow, not narrow columns)
- Color contrast that looks fine in HTML preview but washes out projected
- Tables wrapping where you didn't expect

If `soffice` (LibreOffice) is installed, also generate a thumbnail grid via the `pptx` skill's `scripts/thumbnail.py` for quick scanning.
