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

let runner = 'bun';
let runnerArgs = [PLUGIN_PATH];
try {
  execSync('bun --version', { stdio: 'ignore' });
} catch (e) {
  runner = 'npx';
  runnerArgs = ['-y', 'bun', PLUGIN_PATH];
}

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
        throw new Error(`Failed to parse index file ${INDEX_FILE}: ${e.message}`);
      }
    }
  }
  return { synced: [] };
}

function saveIndex(index) {
  ensureDirectories();
  const tempPath = path.join(TEMP_DIR, 'index.tmp.json');
  try {
    fs.writeFileSync(tempPath, JSON.stringify(index, null, 2), 'utf8');
    fs.renameSync(tempPath, INDEX_FILE);
  } catch (e) {
    console.error(`Failed to write index file atomically:`, e.message);
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
        throw new Error(`Failed to parse failed file ${FAILED_FILE}: ${e.message}`);
      }
    }
  }
  return { failed: {} };
}

function saveFailed(failed) {
  ensureDirectories();
  const tempPath = path.join(TEMP_DIR, 'failed.tmp.json');
  try {
    fs.writeFileSync(tempPath, JSON.stringify(failed, null, 2), 'utf8');
    fs.renameSync(tempPath, FAILED_FILE);
  } catch (e) {
    console.error(`Failed to write failed file atomically:`, e.message);
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

function sanitizeFilename(name) {
  return name.replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, ' ').trim();
}

function processVideo(video, index, total) {
  console.log(`[${index}/${total}] Processing: ${video.id} - ${video.title}`);
  
  // Clean temp dir before running
  if (fs.existsSync(TEMP_DIR)) {
    fs.rmSync(TEMP_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(TEMP_DIR, { recursive: true });

  const args = [
    ...runnerArgs,
    video.id,
    '--languages', 'zh,en',
    '--chapters',
    '--output-dir', TEMP_DIR
  ];
  try {
    execFileSync(runner, args, { stdio: 'inherit' });
  } catch (e) {
    console.error(`Error executing transcript tool for ${video.id}:`, e.message);
    throw new Error(`Transcript extraction failed: ${e.message}`);
  }

  // Locate the downloaded files in TEMP_DIR. Path format: TEMP_DIR/{channel-slug}/{video-slug}/
  const channelFolders = fs.readdirSync(TEMP_DIR).filter(f => fs.statSync(path.join(TEMP_DIR, f)).isDirectory());
  if (channelFolders.length === 0) {
    throw new Error(`No downloaded channel folder found in temp directory for ${video.id}`);
  }
  const channelPath = path.join(TEMP_DIR, channelFolders[0]);
  const videoFolders = fs.readdirSync(channelPath).filter(f => fs.statSync(path.join(channelPath, f)).isDirectory());
  if (videoFolders.length === 0) {
    throw new Error(`No video output folder found in temp directory for ${video.id}`);
  }
  const videoPath = path.join(channelPath, videoFolders[0]);

  // Expected files
  const metaFile = path.join(videoPath, 'meta.json');
  const mdFile = path.join(videoPath, 'transcript.md');
  const coverFile = path.join(videoPath, 'imgs', 'cover.jpg');

  if (!fs.existsSync(mdFile)) {
    throw new Error(`transcript.md not found in output for ${video.id}`);
  }

  // Read meta to get normalized publish date if available
  let publishDate = video.date;
  let title = video.title;
  if (fs.existsSync(metaFile)) {
    try {
      const meta = JSON.parse(fs.readFileSync(metaFile, 'utf8'));
      if (meta.publishDate) publishDate = meta.publishDate;
      if (meta.title) title = meta.title;
    } catch (e) {
      // Fallback to yt-dlp parsed info
    }
  }

  const cleanTitle = sanitizeFilename(title);
  const cleanDate = sanitizeFilename((publishDate || '').slice(0, 10));
  const targetMdName = `[${cleanDate}] ${cleanTitle}.md`;
  const targetMdPath = path.join(OBSIDIAN_DIR, targetMdName);
  const targetCoverName = `${video.id}.jpg`;
  const targetCoverPath = path.join(ASSETS_DIR, targetCoverName);

  // Copy cover image if exists
  let hasCover = false;
  if (fs.existsSync(coverFile)) {
    fs.copyFileSync(coverFile, targetCoverPath);
    hasCover = true;
  }

  // Process markdown content (fix cover image path to relative Obsidian format)
  let mdContent = fs.readFileSync(mdFile, 'utf8');
  
  // Replace default cover image reference with Obsidian relative asset reference
  if (hasCover) {
    mdContent = mdContent.replace(/!\[cover\]\(imgs\/cover\.jpg\)/g, `![封面图](assets/${targetCoverName})`);
    mdContent = mdContent.replace(/cover:\s*imgs\/cover\.jpg/g, `cover: assets/${targetCoverName}`);
  } else {
    mdContent = mdContent.replace(/!\[cover\]\(imgs\/cover\.jpg\)/g, '');
    mdContent = mdContent.replace(/cover:\s*imgs\/cover\.jpg\r?\n/g, '');
  }

  // Write modified file to target Obsidian path
  fs.writeFileSync(targetMdPath, mdContent, 'utf8');
  console.log(`✓ Successfully saved: ${targetMdName}`);
}

function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function main() {
  ensureDirectories();
  checkDependencies();

  let index, failed;
  try {
    index = loadIndex();
    failed = loadFailed();
  } catch (e) {
    console.error(`❌ Initialization error: ${e.message}`);
    process.exit(1);
  }

  const syncedIds = new Set(index.synced);

  let allVideos = [];
  try {
    allVideos = fetchChannelVideos();
    console.log(`Found total of ${allVideos.length} videos on the channel.`);
  } catch (e) {
    console.error('Failed to retrieve video list from channel:', e.message);
    process.exit(1);
  }

  // Filter to unsynced
  const unsynced = allVideos.filter(v => !syncedIds.has(v.id));
  console.log(`Found ${unsynced.length} unsynced videos.`);

  if (unsynced.length === 0) {
    console.log('All videos are up to date! Nothing to do.');
    return;
  }

  let successCount = 0;
  let failCount = 0;

  for (let i = 0; i < unsynced.length; i++) {
    const video = unsynced[i];
    try {
      processVideo(video, i + 1, unsynced.length);
      
      // Mark as synced
      index.synced.push(video.id);
      saveIndex(index);
      
      // Remove from failed list if it previously failed
      if (failed.failed[video.id]) {
        delete failed.failed[video.id];
        saveFailed(failed);
      }
      
      successCount++;
    } catch (err) {
      console.error(`❌ Failed to sync video ${video.id}: ${err.message}`);
      failed.failed[video.id] = {
        title: video.title,
        date: video.date,
        error: err.message,
        timestamp: new Date().toISOString()
      };
      saveFailed(failed);
      failCount++;
    } finally {
      // Clean up temp dir
      if (fs.existsSync(TEMP_DIR)) {
        fs.rmSync(TEMP_DIR, { recursive: true, force: true });
      }
    }

    // Add a sleep interval (1.5 seconds) to avoid aggressive spamming
    if (i < unsynced.length - 1) {
      console.log('Waiting 1.5 seconds...');
      sleepSync(1500);
    }
  }

  console.log('\n--- Sync Complete ---');
  console.log(`Successfully synced: ${successCount}`);
  console.log(`Failed to sync: ${failCount}`);
  if (failCount > 0) {
    console.log(`Failed details written to: ${FAILED_FILE}`);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
