import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const HOME = os.homedir();
const CHANNEL_URL = 'https://www.youtube.com/@bulianglin';
const OBSIDIAN_DIR = path.join(HOME, 'Desktop', 'Lewis', '不良林');
const ASSETS_DIR = path.join(OBSIDIAN_DIR, 'assets');
const INDEX_FILE = path.join(OBSIDIAN_DIR, '.synced_videos.json');
const FAILED_FILE = path.join(OBSIDIAN_DIR, '.failed_videos.json');
const TEMP_DIR = path.join(OBSIDIAN_DIR, '.temp');
const PLUGIN_PATH = path.join(HOME, '.gemini/config/plugins/baoyu-youtube-transcript-plugin/skills/baoyu-youtube-transcript/scripts/main.ts');

function ensureDirectories() {
  if (!fs.existsSync(OBSIDIAN_DIR)) fs.mkdirSync(OBSIDIAN_DIR, { recursive: true });
  if (!fs.existsSync(ASSETS_DIR)) fs.mkdirSync(ASSETS_DIR, { recursive: true });
  if (!fs.existsSync(TEMP_DIR)) fs.mkdirSync(TEMP_DIR, { recursive: true });
}

function checkDependencies() {
  try {
    execSync('yt-dlp --version', { stdio: 'ignore' });
    console.log('✓ yt-dlp is installed');
  } catch (e) {
    console.log('Installing yt-dlp via Homebrew...');
    execSync('brew install yt-dlp', { stdio: 'inherit' });
  }
}

function loadIndex() {
  if (fs.existsSync(INDEX_FILE)) {
    try {
      return JSON.parse(fs.readFileSync(INDEX_FILE, 'utf8'));
    } catch (e) {
      return { synced: [] };
    }
  }
  return { synced: [] };
}

function saveIndex(index) {
  fs.writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2), 'utf8');
}

function loadFailed() {
  if (fs.existsSync(FAILED_FILE)) {
    try {
      return JSON.parse(fs.readFileSync(FAILED_FILE, 'utf8'));
    } catch (e) {
      return { failed: {} };
    }
  }
  return { failed: {} };
}

function saveFailed(failed) {
  fs.writeFileSync(FAILED_FILE, JSON.stringify(failed, null, 2), 'utf8');
}

function fetchChannelVideos() {
  console.log(`Fetching videos from channel ${CHANNEL_URL}...`);
  // Format: id|upload_date|title
  const command = `yt-dlp --flat-playlist --print "%(id)s|%(upload_date)s|%(title)s" "${CHANNEL_URL}"`;
  const output = execSync(command, { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  const lines = output.trim().split('\n');
  
  return lines.map(line => {
    const parts = line.split('|');
    const id = parts[0];
    const rawDate = parts[1];
    const title = parts.slice(2).join('|');
    // Format upload_date YYYYMMDD to YYYY-MM-DD
    const formattedDate = rawDate && rawDate.length === 8 
      ? `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}`
      : 'unknown-date';
    return { id, date: formattedDate, title };
  }).filter(v => v.id);
}

// Execute only if run directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  checkDependencies();
  ensureDirectories();
}
