---
name: youtube-transcript-downloader
description: Download timestamped YouTube transcripts for playlists or channels with automatic IP rate-limit evasion, proxy rotation, and README indexing. Use whenever downloading video transcripts, playlists, channel video texts, or when facing YouTube IpBlocked/429 errors.
---

# YouTube Transcript Downloader

Download full, timestamped transcripts and continuous plain text from any YouTube channel, playlist, or TSV list. Automatically recovers from YouTube IP blocks (`IpBlocked` / HTTP 429) via verified elite proxy rotation.

## Quick Start

### 1. Download Channel or Playlist Directly

```bash
# Download all videos from a channel URL
python3 .agents/skills/youtube-transcript-downloader/scripts/download_transcripts.py \
  "https://www.youtube.com/@blenderguru/videos" \
  -o "transcripts_blenderguru"

# Download a playlist URL
python3 .agents/skills/youtube-transcript-downloader/scripts/download_transcripts.py \
  "https://www.youtube.com/playlist?list=PLjEaoINr3zgEPv5y--4MKpciLaoQYZB1Z" \
  -o "transcripts_playlist"
```

### 2. Download from Pre-extracted TSV File

If the video list is already stored in a `video_id\ttitle` TSV file:

```bash
python3 .agents/skills/youtube-transcript-downloader/scripts/download_transcripts.py \
  "all_videos.tsv" \
  -o "transcripts"
```

To generate the TSV file using `yt-dlp`:
```bash
yt-dlp --flat-playlist --print "%(id)s\t%(title)s" "https://www.youtube.com/@channel/videos" > all_videos.tsv
```

## Options & Arguments

| Argument | Description | Default |
|---|---|---|
| `source` | YouTube channel/playlist URL or local TSV file | Required |
| `-o`, `--output-dir` | Target folder for saved transcript `.txt` files & `README.md` | `transcripts` |
| `--proxy` | Initial HTTP/HTTPS proxy to route requests | `http://45.125.64.215:443` |
| `--auto-proxy` | Automatically query ProxyScrape & test candidate proxies upon 429/IpBlocked | `True` |
| `--delay` | Interval (in seconds) between requests to prevent aggressive throttling | `0.5` |
| `--languages` | Priority comma-separated list of transcript language codes | `en,en-US,en-GB` |
| `--limit` | Cap download to the first N videos | None (all) |

## Output Format

Each downloaded video produces a `.txt` file named:
`{index:02d} - {clean_title} [{video_id}].txt`

Structured as follows:
```text
Title: How To Make The Backrooms In Blender
Video ID: kBsVJSETydU
URL: https://www.youtube.com/watch?v=kBsVJSETydU
Snippets: 2291
================================================================================

--- TIMESTAMPED TRANSCRIPT ---

[00:00] In this video we are going to explore...
[00:04] starting from the carpet material...

================================================================================

--- FULL TEXT ---

In this video we are going to explore starting from the carpet material...
```

Additionally, an index `README.md` is automatically created/updated in the target directory listing the status and relative link for every video.

## Rate-Limit Evasion Protocol

YouTube enforces aggressive rate-limits (`429 Too Many Requests` or `IpBlocked`) when scraping caption tracks repeatedly from a single IP.

The downloader handles this seamlessly:
1. **Resume Guarantee**: On start, the script scans existing `.txt` files matching `[video_id]` in the target folder and skips already downloaded videos.
2. **Consecutive Block Detection**: If 3 requests encounter `IpBlocked` or `RequestBlocked`, it pauses the queue.
3. **Automated Proxy Scrape & Verification**: It probes known verified proxies and queries public elite proxies from ProxyScrape concurrently, verifying that the candidate can successfully fetch a test caption snippet before switching.
4. **Transparent Switch**: The HTTP client swaps to the verified working proxy and resumes without exiting or losing position.
