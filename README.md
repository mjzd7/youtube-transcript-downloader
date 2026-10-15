# YouTube Transcript Downloader

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Skill Ready](https://img.shields.io/badge/Agent%20Skill-Compatible-brightgreen.svg)](SKILL.md)

A high-performance, resumable YouTube transcript downloader designed to extract subtitles from **entire playlists, channels, or custom video lists** at scale. Built with automated proxy discovery and rotation to effortlessly evade YouTube's aggressive rate limiting (`429 Too Many Requests` / `IpBlocked`).

---

## ⚡ Why This Tool?

When scraping captions or subtitles for more than 50–100 videos, YouTube's `timedtext` API triggers strict IP rate limits (`IpBlocked`). Standard tools and cookie-based scrapers fail with `HTTP 429`.

This tool solves that by:
1. **Dynamic Proxy Scraping & Verification:** Automatically probes elite public proxies from sources like ProxyScrape, testing each against YouTube's live caption endpoints concurrently before swapping.
2. **Transparent Proxy Rotation:** Switches the underlying HTTP session seamlessly upon detecting blocks, without crashing or dropping your place in the download queue.
3. **Resumable Execution:** Detects already downloaded video IDs in the target directory and skips them immediately.
4. **Agent Skill Compatible:** Drop it into `.agents/skills/` or `~/.gemini/config/skills/` for autonomous AI agent workflows (Antigravity, Claude Code, Cursor, etc.).

---

## 🚀 Installation

Ensure you have Python 3.9+ and `yt-dlp` installed:

```bash
git clone https://github.com/mjzd7/youtube-transcript-downloader.git
cd youtube-transcript-downloader
pip install -r requirements.txt
```

*(Optional)* Install `yt-dlp` via Homebrew if not already installed:
```bash
brew install yt-dlp
```

---

## 📖 Usage

### 1. Download Entire Channel or Playlist

Pass any YouTube channel or playlist URL:

```bash
# Download all videos from a channel
python3 download_transcripts.py "https://www.youtube.com/@blenderguru/videos" -o transcripts_blenderguru

# Download a playlist
python3 download_transcripts.py "https://www.youtube.com/playlist?list=PLjEaoINr3zgFX8ZsChQVQsuDSjEqdWMAD" -o transcripts_playlist
```

### 2. Download from a Pre-extracted TSV File

For massive channels or custom video selections, extract the video IDs first using `yt-dlp`:

```bash
# Extract IDs and titles
yt-dlp --flat-playlist --print "%(id)s\t%(title)s" "https://www.youtube.com/@channel/videos" > all_videos.tsv

# Run the downloader using the TSV
python3 download_transcripts.py all_videos.tsv -o transcripts
```

---

## ⚙️ CLI Options

| Argument | Flag | Description | Default |
|---|---|---|---|
| `source` | Positional | YouTube channel/playlist URL, or path to a `.tsv` file | *Required* |
| `--output-dir` | `-o` | Directory where transcripts & catalog index are saved | `transcripts` |
| `--proxy` | `-p` | Initial HTTP/HTTPS proxy to route requests | `http://45.125.64.215:443` |
| `--auto-proxy` | | Automatically fetch & test candidate proxies upon `IpBlocked` | `True` |
| `--delay` | `-d` | Delay (in seconds) between video downloads to prevent throttling | `0.5` |
| `--languages` | `-l` | Comma-separated priority list of transcript language codes | `en,en-US,en-GB` |
| `--limit` | | Cap download to the first `N` videos | `None` (all) |

---

## 📄 Output Structure

For every video, the downloader saves a clean `.txt` file containing both a **timestamped log** and **clean continuous prose**:

```text
Title: Fundamentals of Lighting in Blender
Video ID: ENnEYoUpFfU
URL: https://www.youtube.com/watch?v=ENnEYoUpFfU
Snippets: 2291
================================================================================

--- TIMESTAMPED TRANSCRIPT ---

[00:00] In this video we are going to explore lighting...
[00:04] starting from the key light and falloff...

================================================================================

--- FULL TEXT ---

In this video we are going to explore lighting starting from the key light and falloff...
```

### Auto-Generated Catalog `README.md`
The output directory will also include an index table indexing all videos:

| # | Title | Video ID | Status | File |
|---|---|---|---|---|
| 1 | [Fundamentals of Lighting in Blender](https://www.youtube.com/watch?v=ENnEYoUpFfU) | `ENnEYoUpFfU` | success | [01 - Fundamentals of Lighting in Blender [ENnEYoUpFfU].txt](./01 - Fundamentals of Lighting in Blender [ENnEYoUpFfU].txt) |

---

## 🤖 Using as an AI Agent Skill

This repository is formatted as an agent skill out of the box (`SKILL.md` included).

To install into your local project or global agent environment:

```bash
# In your local project repository:
mkdir -p .agents/skills
git clone https://github.com/mjzd7/youtube-transcript-downloader.git .agents/skills/youtube-transcript-downloader

# Or globally for Antigravity / Gemini CLI:
git clone https://github.com/mjzd7/youtube-transcript-downloader.git ~/.gemini/config/skills/youtube-transcript-downloader
```

Once installed, your agent can naturally trigger transcript downloads upon requests like:
> *"Download all video transcripts from this channel and store them in transcripts_channel."*

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).
