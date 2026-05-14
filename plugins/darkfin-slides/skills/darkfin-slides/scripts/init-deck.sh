#!/usr/bin/env bash
# Bootstrap a darkfin-slides working directory inside the current project's docs/slides/.
# Usage:
#   bash init-deck.sh <deck-name>            # creates ./docs/slides/<deck-name>
#   bash init-deck.sh <deck-name> <path>     # custom workdir path (overrides default)

set -e

NAME="${1:-deck}"
WORKDIR="${2:-./docs/slides/$NAME}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$WORKDIR/slides" "$WORKDIR/assets" "$WORKDIR/assets/icons" "$WORKDIR/assets/numbers"

# Copy pre-rendered gradient backgrounds (top-level PNGs only)
cp "$SKILL_DIR/assets/"*.png "$WORKDIR/assets/" 2>/dev/null || true

# Copy bundled icon library + gradient step numbers
cp "$SKILL_DIR/assets/icons/"*.png "$WORKDIR/assets/icons/" 2>/dev/null || true
cp "$SKILL_DIR/assets/numbers/"*.png "$WORKDIR/assets/numbers/" 2>/dev/null || true

# Copy html2pptx library
cp "$SKILL_DIR/scripts/html2pptx.js" "$WORKDIR/html2pptx.js"

cd "$WORKDIR"

# Init Node project + install deps
if [ ! -f package.json ]; then
  npm init -y > /dev/null
fi
if [ ! -d node_modules/pptxgenjs ]; then
  npm install pptxgenjs playwright sharp 2>&1 | tail -3
fi

# Write .gitignore so node_modules doesn't pollute the project repo
if [ ! -f .gitignore ]; then
  cat > .gitignore <<'EOF'
node_modules/
package-lock.json
EOF
fi

# Write hello-world starter slide so user can verify pipeline before writing real content
if [ ! -f slides/00-hello.html ]; then
  cat > slides/00-hello.html <<'HTML'
<!DOCTYPE html>
<html><head><style>
html { background: #0B0E1A; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  font-family: Arial, sans-serif; display: flex; flex-direction: column;
  background-image: url('../assets/title-bg.png'); background-size: cover;
}
.frame { flex: 1; padding: 50pt 60pt; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; }
.eyebrow { display: flex; align-items: center; gap: 12pt; margin: 0 0 16pt 0; }
.dot { width: 8pt; height: 8pt; background: #00E5FF; border-radius: 50%; }
.eyebrow p { color: #00E5FF; font-size: 11pt; letter-spacing: 4pt; font-weight: bold; margin: 0; }
h1 { color: #F8FAFC; font-size: 38pt; margin: 0 0 14pt 0; line-height: 1.1; font-weight: bold; }
h1 span { color: #00E5FF; }
.sub { color: #94A3B8; font-size: 14pt; margin: 0 0 22pt 0; line-height: 1.4; max-width: 560pt; }
.meta { display: flex; gap: 24pt; padding-top: 16pt; border-top: 1pt solid #2A3043; }
.meta p { margin: 0; color: #64748B; font-size: 9pt; letter-spacing: 2pt; font-weight: bold; }
.meta .ok { color: #10B981; font-family: 'Courier New', monospace; }
</style></head><body>
<div class="frame">
  <div class="eyebrow">
    <div class="dot"></div>
    <p>DARKFIN-SLIDES</p>
  </div>
  <h1>Pipeline <span>OK</span></h1>
  <p class="sub">Delete this file and add your real slides as <code>slides/01-*.html</code>, <code>slides/02-*.html</code>, etc. Templates in references/slide-templates.md.</p>
  <div class="meta">
    <p>PALETTE</p>
    <p class="ok">SLATE</p>
    <p>STATUS</p>
    <p class="ok">READY</p>
  </div>
</div>
</body></html>
HTML
fi

# Write starter build.js if not present
if [ ! -f build.js ]; then
  cat > build.js <<EOF
const pptxgen = require('pptxgenjs');
const html2pptx = require('./html2pptx');
const fs = require('fs');
const path = require('path');

async function main() {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.title = '$NAME';
  pptx.author = 'darkfin-slides';

  const slidesDir = path.join(__dirname, 'slides');
  const files = fs.readdirSync(slidesDir).filter(f => f.endsWith('.html')).sort();

  for (const file of files) {
    await html2pptx(path.join(slidesDir, file), pptx);
    console.log('OK', file);
  }

  const out = path.join(__dirname, '$NAME.pptx');
  await pptx.writeFile({ fileName: out });
  console.log('Saved', out);
}

main().catch(e => { console.error(e.message); process.exit(1); });
EOF
fi

echo ""
echo "Workdir ready: $WORKDIR"
echo "Next: write slides to $WORKDIR/slides/NN-name.html, then 'cd $WORKDIR && node build.js'"
echo "Output will be: $WORKDIR/$NAME.pptx"
