# YouTube to Obsidian Syncing Utility for Bulianglin Channel

This design document outlines the technical specification for downloading transcripts and metadata from the YouTube channel `@bulianglin` and syncing them as organized notes into the user's Obsidian vault.

## Goal

Automate the extraction of transcripts, metadata (titles, publishing dates, description, chapters), and cover images for all videos from the YouTube channel `https://www.youtube.com/@bulianglin` and format them into an Obsidian-ready folder `/Users/luliuyuan/Desktop/Lewis/不良林` with incremental sync support.

## Proposed Architecture

1. **Environment Setup**:
   - Check and install `yt-dlp` via Homebrew (`brew install yt-dlp`).
   - Run the integration utilizing `npx -y bun` for the existing `baoyu-youtube-transcript` plugin script.

2. **Sync Automation Script (`youtube_to_obsidian.ts`)**:
   - Location: `/Users/luliuyuan/Documents/Codex/youtube_to_obsidian.ts`
   - Flow:
     - Run `yt-dlp --flat-playlist --print "%(id)s|%(upload_date)s|%(title)s" "https://www.youtube.com/@bulianglin"` to list all video metadata.
     - Load `/Users/luliuyuan/Desktop/Lewis/不良林/.synced_videos.json` to identify which videos have already been successfully processed.
     - For each pending video:
       1. Run `baoyu-youtube-transcript` CLI to generate raw transcripts and metadata under `/Users/luliuyuan/Desktop/Lewis/不良林/.temp/`.
       2. Read the generated metadata and subtitle files.
       3. Reformat the Markdown document to match the target layout, placing the cover image in `/Users/luliuyuan/Desktop/Lewis/不良林/assets/`.
       4. Save the finalized Markdown file to `/Users/luliuyuan/Desktop/Lewis/不良林/[YYYYMMDD] Title.md`.
       5. Update `.synced_videos.json` to mark the video as synced.
       6. Clean up temporary files.

3. **Incremental Sync State (`.synced_videos.json`)**:
   - Stores an array or object map of processed video IDs:
     ```json
     {
       "synced": [
         "video_id_1",
         "video_id_2"
       ]
     }
     ```

## Verification Plan

### Manual Verification
- Run the script for a single/recent video to verify:
  1. The Markdown file is correctly named and formatted.
  2. The cover image is copied to the `/assets/` directory and linked properly using relative paths.
  3. The note renders perfectly in Obsidian.
- Run the script a second time to ensure it skips the already processed video (incremental sync test).
- Run the script for a small batch of videos.
