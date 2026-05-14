#!/usr/bin/env node
// Generate oversized gradient step-number PNGs (cyan to purple).
// Usage: node gen-numbers.js [--primary "#00E5FF"] [--secondary "#7B61FF"] [--out ./assets/numbers] [--max 9] [--size 600]
// Used by templates that want a giant step number badge (1event-proposal style).

const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
}

const primary   = arg('primary',   '#00E5FF');
const secondary = arg('secondary', '#7B61FF');
const outDir    = arg('out',       './assets/numbers');
const maxN      = parseInt(arg('max', '9'), 10);
const size      = parseInt(arg('size', '600'), 10);

fs.mkdirSync(outDir, { recursive: true });

async function makeNumber(n) {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${primary}"/>
          <stop offset="100%" stop-color="${secondary}"/>
        </linearGradient>
      </defs>
      <text x="50%" y="50%"
            font-family="Arial Black, Arial, sans-serif"
            font-size="${size * 0.85}"
            font-weight="900"
            text-anchor="middle"
            dominant-baseline="central"
            fill="url(#g)">${n}</text>
    </svg>`;
  const file = path.join(outDir, `num-${n}.png`);
  await sharp(Buffer.from(svg)).png().toFile(file);
  console.log('OK', file);
}

(async () => {
  for (let n = 1; n <= maxN; n++) {
    await makeNumber(n);
  }
  // Also generate two-digit 10-12 for occasional needs
  for (let n = 10; n <= 12; n++) {
    await makeNumber(n);
  }
  console.log('Done. Output:', outDir);
})();
