#!/usr/bin/env node
// Regenerate gradient PNG backgrounds for darkfin-slides.
// Usage: node gen-assets.js [--primary "#00E5FF"] [--secondary "#7B61FF"] [--out ./assets]
// Defaults match the canonical darkfin palette.

const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
}

const primary   = arg('primary',   '#00E5FF');
const secondary = arg('secondary', '#7B61FF');
const outDir    = arg('out',       './assets');

fs.mkdirSync(outDir, { recursive: true });

async function write(file, svgInner, w = 1440, h = 810) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">${svgInner}</svg>`;
  const out = path.join(outDir, file);
  await sharp(Buffer.from(svg)).png().toFile(out);
  console.log('OK', out);
}

(async () => {
  // title-bg.png — clean hero radial (no grid). Used for cover, dividers, closing.
  // Matches the 1event-proposal cover style: twin radial glow on near-black.
  await write('title-bg.png', `
    <defs>
      <radialGradient id="bg" cx="50%" cy="50%" r="80%">
        <stop offset="0%" stop-color="#0B0E1A"/>
        <stop offset="100%" stop-color="#000000"/>
      </radialGradient>
      <radialGradient id="g1" cx="22%" cy="32%" r="55%">
        <stop offset="0%" stop-color="${secondary}" stop-opacity="0.55"/>
        <stop offset="60%" stop-color="${secondary}" stop-opacity="0.12"/>
        <stop offset="100%" stop-color="${secondary}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="g2" cx="80%" cy="72%" r="45%">
        <stop offset="0%" stop-color="${primary}" stop-opacity="0.50"/>
        <stop offset="60%" stop-color="${primary}" stop-opacity="0.10"/>
        <stop offset="100%" stop-color="${primary}" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <rect width="100%" height="100%" fill="url(#bg)"/>
    <rect width="100%" height="100%" fill="url(#g1)"/>
    <rect width="100%" height="100%" fill="url(#g2)"/>
  `);

  // title-bg-grid.png — alt variant with subtle grid overlay
  await write('title-bg-grid.png', `
    <defs>
      <radialGradient id="g1" cx="20%" cy="30%" r="80%">
        <stop offset="0%" stop-color="#1E2A4A"/>
        <stop offset="60%" stop-color="#0B0F1A"/>
        <stop offset="100%" stop-color="#000000"/>
      </radialGradient>
      <radialGradient id="g2" cx="85%" cy="85%" r="50%">
        <stop offset="0%" stop-color="${secondary}" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="${secondary}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="g3" cx="50%" cy="20%" r="40%">
        <stop offset="0%" stop-color="${primary}" stop-opacity="0.18"/>
        <stop offset="100%" stop-color="${primary}" stop-opacity="0"/>
      </radialGradient>
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E2A4A" stroke-width="0.5" opacity="0.6"/>
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#g1)"/>
    <rect width="100%" height="100%" fill="url(#grid)"/>
    <rect width="100%" height="100%" fill="url(#g2)"/>
    <rect width="100%" height="100%" fill="url(#g3)"/>
  `);

  // content-bg.png — subtle dark + grid + corner glow
  await write('content-bg.png', `
    <defs>
      <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#0F1525"/>
        <stop offset="100%" stop-color="#0B0F1A"/>
      </linearGradient>
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1A2440" stroke-width="0.5" opacity="0.4"/>
      </pattern>
      <radialGradient id="glow" cx="95%" cy="5%" r="40%">
        <stop offset="0%" stop-color="${primary}" stop-opacity="0.08"/>
        <stop offset="100%" stop-color="${primary}" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <rect width="100%" height="100%" fill="url(#g1)"/>
    <rect width="100%" height="100%" fill="url(#grid)"/>
    <rect width="100%" height="100%" fill="url(#glow)"/>
  `);

  // accent-bg.png — twin glows (purple + cyan)
  await write('accent-bg.png', `
    <defs>
      <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#0F1525"/>
        <stop offset="100%" stop-color="#0B0F1A"/>
      </linearGradient>
      <radialGradient id="glow1" cx="10%" cy="90%" r="40%">
        <stop offset="0%" stop-color="${secondary}" stop-opacity="0.25"/>
        <stop offset="100%" stop-color="${secondary}" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="glow2" cx="90%" cy="10%" r="35%">
        <stop offset="0%" stop-color="${primary}" stop-opacity="0.15"/>
        <stop offset="100%" stop-color="${primary}" stop-opacity="0"/>
      </radialGradient>
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1A2440" stroke-width="0.5" opacity="0.4"/>
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#g1)"/>
    <rect width="100%" height="100%" fill="url(#grid)"/>
    <rect width="100%" height="100%" fill="url(#glow1)"/>
    <rect width="100%" height="100%" fill="url(#glow2)"/>
  `);

  // Card backgrounds (rarely used — most cards are solid #141B2D)
  await write('card-cyan.png', `
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0E3F4F"/><stop offset="100%" stop-color="#1A2440"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  `, 800, 400);

  await write('card-purple.png', `
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2D1B5C"/><stop offset="100%" stop-color="#1A2440"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  `, 800, 400);

  await write('card-gold.png', `
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3F2E0E"/><stop offset="100%" stop-color="#1A2440"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  `, 800, 400);

  console.log('Done. Output:', outDir);
})();
