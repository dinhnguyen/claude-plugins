---
name: darkfin-slides
description: Create dark fintech/blockchain style PowerPoint decks for stakeholder, sales, or customer presentations. Use when the user asks to "tạo slide", "make a deck", "build a pitch", "design a presentation" AND wants a dark/neon/fintech/blockchain visual style — or when they reference this skill explicitly. Outputs .pptx via HTML to PowerPoint pipeline with pre-rendered gradient backgrounds, slate-aligned cyan/violet/amber/emerald accents, deep slate palette by default (Tailwind-aligned), Courier numerics, 39 bundled cyan icon PNGs, and gradient step-number PNGs. Custom tone is supported on request — re-confirm scope, then run gen-assets/icons/numbers + sed find-replace hex in workdir slides. Output is always saved inside the current project's docs/slides/ folder (never /tmp unless explicitly asked). Provides 29 ready-made slide templates covering title, problem, solution, scenario tables, admin mockups, KPI grids, before/after, process flows, quotes, pricing tiers, architecture maps, scoring tiers, horizontal + 3 vertical timeline variants (rail+card, date-prefix, alternating zigzag), and more. Audience-agnostic (sales, exec, customer); skip technical jargon and lean on visuals.
---

# Darkfin Slides — Dark Fintech Deck Builder

Build a polished 12-slide pitch deck with consistent dark-fintech aesthetics. HTML slides convert to .pptx via the `html2pptx` library (Playwright renders the layout; PptxGenJS writes the PowerPoint).

## When to use

- User wants a stakeholder/customer/sales deck in **dark, neon, fintech, blockchain, crypto, or "premium tech"** style.
- User says "tạo slide", "make a pitch deck", "build a proposal deck", "design a presentation" and shows or asks for a dark visual style.
- User references this skill by name.

Do not use this skill for:
- Light/corporate decks (use the base `pptx` skill).
- Single posters/PDFs (use `canvas-design` or `minimax-pdf`).
- Editing an existing .pptx (use `pptx` for OOXML edits).

## Output format

A `.pptx` file (16:9, 720pt × 405pt) saved inside the **current project's `docs/slides/<deck-name>/`** directory. Default output filename: `<deck-name>.pptx` inside that folder. Do NOT write to `/tmp` unless the user explicitly asks for a throwaway scratch deck.

## Workflow

### 1. Bootstrap the working directory

Run from the project root. The script creates `./docs/slides/<deck-name>/` by default:

```bash
bash <skill-dir>/scripts/init-deck.sh <deck-name>
```

Optional second arg overrides the workdir path:

```bash
bash <skill-dir>/scripts/init-deck.sh <deck-name> <custom-path>
```

This:
- Creates `<workdir>/slides/`, `<workdir>/assets/`
- Copies the pre-rendered gradient backgrounds + `html2pptx.js` from this skill
- Runs `npm init -y` and installs `pptxgenjs`, `playwright`, `sharp`
- Writes a `.gitignore` (excludes `node_modules/`, `package-lock.json`) so the project repo stays clean
- Generates a starter `build.js` that outputs `<workdir>/<deck-name>.pptx`

**Important:** Always cd to the project root before running the script. If unsure, ask the user where the project root is.

If assets already match the user's needs, do NOT regenerate them. Only run `gen-assets.js` if the user requests a different palette.

### 2. Plan the slides

Before writing HTML, draft the outline based on the user's brief. Pick from the 29 available templates (see [references/slide-templates.md](references/slide-templates.md)). A typical 12-slide pitch:

| # | Template | Purpose |
|---|----------|---------|
| 1 | **1. title** | Topic, audience, date, accent chips |
| 2 | **12. agenda / TOC** | What we'll cover |
| 3 | **2. problem cards** | 3 pain points |
| 4 | **11. section divider** | Transition to "the solution" |
| 5 | **3. solution + spotlight** | Core idea + 3 features |
| 6 | **4. how-it-works** | 3-layer overview map |
| 7–9 | **5. rule + example** | One rule per slide |
| 10 | **6. scenario table** OR **14. before/after** | Who sees what / impact framing |
| 11 | **7. admin mockup** | Operations walkthrough |
| 12 | **8. timeline** OR **18. roadmap** | Launch plan |
| 13 | **9. decision questions** | What we need from the customer |
| 14 | **17. closing / Q&A** | Thanks + contact |

Other available types for specialty decks:
- **13. KPI grid** — big numbers when you need to show traction/impact
- **15. process flow** — sequential horizontal steps
- **16. quote / testimonial** — social proof
- **19. pricing tiers** — 3 plan cards (use for commercial proposals)
- **20. architecture map** — system/component diagram
- **21. risk × impact 2×2** — quadrant matrix
- **22. feature comparison table** — feature × plan grid

Confirm the outline with the user before writing every slide unless they've said to just go.

### 3. Write each slide HTML

Use the patterns in [references/slide-templates.md](references/slide-templates.md). Each template has been overflow-tested at 720×405pt.

**Critical rules (`html2pptx` will reject otherwise):**
- All text MUST be in `<p>`, `<h1>–<h6>`, `<ul>`, or `<ol>`. Plain text in `<div>`/`<span>` is silently dropped.
- NO CSS gradients in HTML — use pre-rendered PNG backgrounds via `background-image: url(...)`.
- NO background images on inner `<div>` elements — only on `<body>`.
- Use only web-safe fonts: `Arial`, `Courier New` (for numerics/IDs).
- Body MUST be `width: 720pt; height: 405pt; display: flex;` to avoid margin-collapse overflow.

### 4. Build the deck

```bash
cd <workdir> && node build.js
```

The build script:
- Iterates `slides/*.html` in order
- Runs `html2pptx()` for each (validates overflow, dimensions, text wrapping)
- Writes the final `.pptx`

### 5. Fix overflow errors

`html2pptx` errors on validation. Common fixes (apply in order until pass):

1. Reduce `.body { padding }` by 4–8pt.
2. Reduce `h1` font-size by 2–4pt.
3. Reduce inter-element `margin` / `gap` by 2–4pt.
4. Reduce card `padding` by 2–4pt.
5. Drop one decorative line / shrink the lead paragraph.

See [references/troubleshooting.md](references/troubleshooting.md) for an error-to-fix table.

### 6. Hand off

Report the absolute path of the `.pptx` to the user. Suggest opening in Keynote/PowerPoint to review. Do not auto-convert to PDF unless asked.

## Design system

See [references/design-system.md](references/design-system.md) for the full palette, typography, spacing rules. Summary (slate palette, Tailwind-aligned):

- **Background**: deep navy `#0B0E1A` with pre-rendered gradient PNG. Cyan `#00E5FF` is fixed primary.
- **Panels**: `#151A2E` fill, `#2A3043` border.
- **Accent**: cyan `#00E5FF` (primary), violet `#8B5CF6`, amber `#F59E0B`, emerald `#10B981`, red `#EF4444`.
- **Text**: `#F8FAFC` body, `#94A3B8` muted, `#64748B` labels.
- **Fonts**: Arial (sans), Courier New (numerics, IDs, mono details).
- **Visual signature**: top status bar with `NN /` mono prefix, eyebrow tag in accent color, h1 with one accent-colored word in `<span>`, oversized cyan-to-purple gradient step numbers, cyan-tinted icon PNGs throughout.

## Bundled assets

After running `init-deck.sh`, the workdir has:

- `assets/title-bg.png` — clean cover background (twin radial glow, no grid)
- `assets/title-bg-grid.png` — cover variant with subtle grid
- `assets/content-bg.png` — standard content slide background
- `assets/accent-bg.png` — accent variant for solution / launch / questions
- `assets/icons/` — **39 cyan PNG icons** (`lock.png`, `email.png`, `ticket.png`, `qr.png`, `shield.png`, `user.png`, `arrow.png`, etc.) at 256×256
- `assets/numbers/` — **12 gradient step-number PNGs** (`num-1.png` through `num-12.png`) at 600×600

Reference in slide HTML as plain `<img>`:
```html
<img src="../assets/icons/lock.png" style="width: 24pt; height: 24pt;">
<img src="../assets/numbers/num-3.png" style="width: 90pt; height: 90pt;">
```

## Custom palette / tone change

**Default palette is slate** (Tailwind-aligned, see [references/design-system.md](references/design-system.md)). Templates and bundled PNG assets all use slate hex. Do not change anything unless the user explicitly asks for a different tone.

### When user asks for a different tone

Before swapping, confirm with the user:

1. **What changes?** Just the secondary accent (e.g. swap violet for pink), or the entire palette including primary cyan?
2. **Brand-tied?** If they have a brand color spec (logo hex, Figma variables, etc.), ask them to share it. Otherwise propose: keep slate panel/text, swap accent colors only — minimizes scope.
3. **Cyan primary is the skill's visual signature.** Replacing it is supported but the result no longer reads as "darkfin". Flag this and re-confirm.

### Swap procedure (after user confirms)

Run all three from the **workdir** (`docs/slides/<deck-name>/`) so generated assets land in the deck folder, not the skill:

```bash
# 1. Regenerate background glow PNGs (title-bg, content-bg, accent-bg, etc.)
node <skill-dir>/scripts/gen-assets.js --primary "<new-cyan-or-keep>" --secondary "<new-purple>" --out ./assets

# 2. Recolor the 39 icon PNGs (single tint)
node <skill-dir>/scripts/gen-icons.js --color "<new-cyan-or-keep>" --out ./assets/icons

# 3. Regenerate gradient step numbers
node <skill-dir>/scripts/gen-numbers.js --primary "<new-cyan-or-keep>" --secondary "<new-purple>" --out ./assets/numbers
```

Then **find/replace hex in `slides/*.html`** for any template hardcoded colors. The 12 slate codes to look for:

| Slate hex | Token | Typical role |
|-----------|-------|--------------|
| `#0B0E1A` | bg-deep | Page base, dot ring |
| `#151A2E` | panel | Card fill |
| `#1F2437` | panel-alt | Sub-panel |
| `#10182A` | panel-inset | Nested row |
| `#2A3043` | border | 1pt panel border, divider |
| `#00E5FF` | cyan primary | Eyebrow, accents, dot, h1 span |
| `#8B5CF6` | violet-500 | Secondary accent |
| `#F59E0B` | amber-500 | Warning |
| `#10B981` | emerald-500 | Success / ok |
| `#EF4444` | red-500 | Error |
| `#F8FAFC` | text | Body text |
| `#94A3B8` | muted | Sub-text |

Multi-pattern sed example:

```bash
cd <workdir>/slides && \
sed -i.bak \
  -e 's/#00E5FF/<new-cyan>/g' \
  -e 's/#8B5CF6/<new-purple>/g' \
  -e 's/#F59E0B/<new-amber>/g' \
  *.html && \
rm *.html.bak
```

After swap, **rebuild and visually inspect**: `node build.js`, then open the .pptx. Color combinations that look fine in HTML may clash on a projected slide.

### Caveats

- The cyan-to-purple **gradient step numbers** rebuild from primary+secondary args. Step slides (#23) will pick up the new gradient automatically.
- Some templates use **deep variants** (`#0E3F4F` cyan-deep, `#2E1B5C` purple-deep, `#3F2E0A` amber-deep, `#0A3F2E` green-deep). These need manual derivation — `~25% saturation, ~20% lightness` of the new accent. Easiest: pick from Tailwind 950 scale of the chosen hue.
- Skill source files at `<skill-dir>/assets/` must NOT be modified — only the workdir copies.
