import { execSync, execFileSync } from 'child_process';
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
    const content = fs.readFileSync(INDEX_FILE, 'utf8').trim();
    if (content.length > 0) {
      try {
        const data = JSON.parse(content);
        if (!data || !Array.isArray(data.synced)) {
          throw new Error('Invalid index format: synced must be an array');
        }
        return data;
      } catch (e) {
        console.error(`\nERROR: Failed to parse index file ${INDEX_FILE}:`, e.message);
        console.error('To avoid overwriting sync history, the process will exit.');
        process.exit(1);
      }
    }
  }
  return { synced: [] };
}

function saveIndex(index) {
  ensureDirectories();
  try {
    fs.writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2), 'utf8');
  } catch (e) {
    console.error(`Failed to write index file to ${INDEX_FILE}:`, e.message);
    throw e;
  }
}

function loadFailed() {
  if (fs.existsSync(FAILED_FILE)) {
    const content = fs.readFileSync(FAILED_FILE, 'utf8').trim();
    if (content.length > 0) {
      try {
        const data = JSON.parse(content);
        if (!data || typeof data.failed !== 'object' || data.failed === null) {
          throw new Error('Invalid failed file format: failed must be an object');
        }
        return data;
      } catch (e) {
        console.error(`\nERROR: Failed to parse failed file ${FAILED_FILE}:`, e.message);
        console.error('To avoid overwriting failed list history, the process will exit.');
        process.exit(1);
      }
    }
  }
  return { failed: {} };
}

function saveFailed(failed) {
  ensureDirectories();
  try {
    fs.writeFileSync(FAILED_FILE, JSON.stringify(failed, null, 2), 'utf8');
  } catch (e) {
    console.error(`Failed to write failed file to ${FAILED_FILE}:`, e.message);
    throw e;
  }
}

function fetchChannelVideos() {
  console.log(`Fetching videos from channel ${CHANNEL_URL}...`);
  // Format: id|upload_date|title
  const args = [
    '--flat-playlist',
    '--print',
    '%(id)s|%(upload_date)s|%(title)s',
    CHANNEL_URL
  ];
  let output;
  try {
    output = execFileSync('yt-dlp', args, { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  } catch (e) {
    console.error(`Failed to fetch channel videos from ${CHANNEL_URL}:`, e.message);
    throw new Error(`Failed to query yt-dlp: ${e.message}`);
  }
  const lines = output.trim().split(/\r?\n/);
  
  return lines.map(line => {
    const parts = line.split('|');
    if (parts.length < 3) return null;
    
    const id = parts[0];
    if (!/^[a-zA-Z0-9_-]{11}$/.test(id)) {
      return null;
    }
    
    const rawDate = parts[1];
    const title = parts.slice(2).join('|');
    // Format upload_date YYYYMMDD to YYYY-MM-DD
    const formattedDate = rawDate && rawDate.length === 8 
      ? `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}`
      : 'unknown-date';
    return { id, date: formattedDate, title };
  }).filter(v => v !== null);
}

// Execute only if run directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  checkDependencies();
  ensureDirectories();
}
