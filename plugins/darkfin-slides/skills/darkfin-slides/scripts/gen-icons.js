#!/usr/bin/env node
// Rasterize a set of react-icons to PNG (cyan tinted by default).
// Usage: node gen-icons.js [--color "#00E5FF"] [--size 256] [--out ./assets/icons]
// Run from the skill directory (where react/react-dom/react-icons are installed).
// Requires: npm install react react-dom react-icons sharp
// To customize the icon set, edit ICONS below.

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
}

const color = (arg('color', '00E5FF') || '').replace(/^#/, '');
const size  = parseInt(arg('size', '256'), 10);
const outDir = arg('out', './assets/icons');

fs.mkdirSync(outDir, { recursive: true });

// Resolve react-icons + sharp from either local node_modules or globally
function tryRequire(mod) {
  try { return require(mod); } catch (e) {}
  try {
    const globalPath = execFileSync('npm', ['root', '-g'], { encoding: 'utf-8' }).trim();
    return require(path.join(globalPath, mod));
  } catch (e) {
    console.error(`Cannot find module "${mod}". Run: npm install react react-dom react-icons sharp`);
    process.exit(1);
  }
}

const React = tryRequire('react');
const ReactDOMServer = tryRequire('react-dom/server');
const sharp = tryRequire('sharp');
const fa = tryRequire('react-icons/fa');

// Default icon set covering common deck needs.
// To add/remove icons, edit this list. Use `Fa<Name>` from react-icons/fa.
const ICONS = [
  // Identity / users
  { name: 'user',        comp: fa.FaUser },
  { name: 'user-add',    comp: fa.FaUserPlus },
  { name: 'team',        comp: fa.FaUsers },
  { name: 'admin',       comp: fa.FaUserShield },
  { name: 'manager',     comp: fa.FaUserTie },
  // Communication
  { name: 'email',       comp: fa.FaEnvelope },
  { name: 'phone',       comp: fa.FaPhone },
  { name: 'mobile',      comp: fa.FaMobileAlt },
  { name: 'globe',       comp: fa.FaGlobe },
  // Security
  { name: 'lock',        comp: fa.FaLock },
  { name: 'shield',      comp: fa.FaShieldAlt },
  { name: 'fingerprint', comp: fa.FaFingerprint },
  { name: 'bot',         comp: fa.FaRobot },
  // Commerce / sales
  { name: 'ticket',      comp: fa.FaTicketAlt },
  { name: 'qr',          comp: fa.FaQrcode },
  { name: 'chart',       comp: fa.FaChartLine },
  { name: 'money',       comp: fa.FaDollarSign },
  { name: 'cart',        comp: fa.FaShoppingCart },
  // Actions / state
  { name: 'success',     comp: fa.FaCheckCircle },
  { name: 'warning',     comp: fa.FaExclamationTriangle },
  { name: 'error',       comp: fa.FaTimesCircle },
  { name: 'info',        comp: fa.FaInfoCircle },
  { name: 'star',        comp: fa.FaStar },
  // Process / flow
  { name: 'arrow',       comp: fa.FaArrowRight },
  { name: 'arrow-down',  comp: fa.FaArrowDown },
  { name: 'clock',       comp: fa.FaClock },
  { name: 'hourglass',   comp: fa.FaHourglassHalf },
  { name: 'calendar',    comp: fa.FaCalendarAlt },
  // System
  { name: 'database',    comp: fa.FaDatabase },
  { name: 'cloud',       comp: fa.FaCloud },
  { name: 'cog',         comp: fa.FaCog },
  { name: 'tasks',       comp: fa.FaTasks },
  { name: 'rocket',      comp: fa.FaRocket },
  // Social
  { name: 'twitter',     comp: fa.FaTwitter },
  { name: 'facebook',    comp: fa.FaFacebook },
  { name: 'tiktok',      comp: fa.FaTiktok },
  { name: 'linkedin',    comp: fa.FaLinkedin },
  // Camera / wifi
  { name: 'camera',      comp: fa.FaCamera },
  { name: 'wifi',        comp: fa.FaWifi },
];

async function rasterize(IconComponent, color, size, filename) {
  const svgString = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color: `#${color}`, size: size })
  );
  await sharp(Buffer.from(svgString)).png().toFile(filename);
}

(async () => {
  for (const { name, comp } of ICONS) {
    if (!comp) { console.warn('Skip missing icon:', name); continue; }
    const out = path.join(outDir, `${name}.png`);
    await rasterize(comp, color, size, out);
    console.log('OK', out);
  }
  console.log(`Done. ${ICONS.length} icons → ${outDir}`);
})();
