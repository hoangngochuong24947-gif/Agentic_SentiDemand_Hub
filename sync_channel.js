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

// Execute only if run directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  checkDependencies();
  ensureDirectories();
}
