#!/usr/bin/env python3
"""
YouTube Playlist & Channel Transcript Downloader
Robust, resumable downloader with automated proxy discovery and rate-limit evasion.
"""

import os
import re
import sys
import time
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.proxies import GenericProxyConfig

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=all&ssl=yes&anonymity=elite",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
]

DEFAULT_FALLBACK_PROXIES = [
    "http://45.125.64.215:443",
    "http://116.104.251.199:2111"
]

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r'\s+', " ", clean).strip()
    return clean[:120]

def format_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def get_existing_video_ids(transcripts_dir):
    existing = {}
    if not os.path.exists(transcripts_dir):
        return existing
    for fname in os.listdir(transcripts_dir):
        if fname.endswith(".txt"):
            m = re.search(r'\[([a-zA-Z0-9_-]{11})\]\.txt$', fname)
            if m:
                existing[m.group(1)] = fname
    return existing

def fetch_playlist_videos(source):
    """
    Source can be:
    - Path to a .tsv file
    - YouTube URL (playlist, channel /videos, or single video)
    """
    videos = []
    if os.path.isfile(source):
        print(f"[*] Reading video list from TSV: {source}")
        with open(source, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line or "\t" not in line:
                    continue
                vid_id, title = line.split("\t", 1)
                videos.append({"index": idx, "id": vid_id.strip(), "title": title.strip()})
        return videos

    # Use yt-dlp to extract playlist/channel entries
    print(f"[*] Querying video list from YouTube using yt-dlp: {source}")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s",
        source
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        lines = [l for l in res.stdout.strip().split("\n") if l and "\t" in l]
        for idx, line in enumerate(lines, start=1):
            vid_id, title = line.split("\t", 1)
            videos.append({"index": idx, "id": vid_id.strip(), "title": title.strip()})
    except subprocess.CalledProcessError as e:
        print(f"[-] yt-dlp failed to fetch video list: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    return videos

def test_single_proxy(proxy_url, test_video_id="knzKHaZFzbQ"):
    try:
        p_cfg = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
        api = YouTubeTranscriptApi(proxy_config=p_cfg)
        t = api.fetch(test_video_id)
        if list(t):
            return proxy_url
    except Exception:
        pass
    return None

def find_working_proxy(test_video_id="knzKHaZFzbQ"):
    print("[*] Probing for verified working proxies...")
    # First test known defaults
    for p in DEFAULT_FALLBACK_PROXIES:
        if test_single_proxy(p, test_video_id):
            print(f"[+] Found working proxy from defaults: {p}")
            return p

    print("[*] Querying public elite proxy lists...")
    candidates = []
    for src in PROXY_SOURCES:
        try:
            r = requests.get(src, timeout=4)
            for line in r.text.splitlines():
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    candidates.append(f"http://{line}")
        except Exception:
            pass

    candidates = list(dict.fromkeys(candidates))[:80]
    print(f"[*] Testing {len(candidates)} proxy candidates concurrently...")
    with ThreadPoolExecutor(max_workers=15) as ex:
        for res in ex.map(lambda p: test_single_proxy(p, test_video_id), candidates):
            if res:
                print(f"[+] Verified active proxy: {res}")
                return res

    print("[-] Warning: No working external proxy found in current scan.")
    return None

def update_readme(output_dir, source_name, videos, results):
    index_md_path = os.path.join(output_dir, "README.md")
    total = len(videos)
    success_count = sum(1 for r in results.values() if r.get("status") == "success")
    failed_count = sum(1 for r in results.values() if r.get("status") != "success")

    with open(index_md_path, "w", encoding="utf-8") as f:
        f.write(f"# YouTube Transcripts: {source_name}\n\n")
        f.write(f"- **Total Videos:** {total}\n")
        f.write(f"- **Transcripts Downloaded:** {success_count}\n")
        f.write(f"- **Failed / Disabled / Rate-Limited:** {failed_count}\n\n")
        f.write("## Video Index\n\n")
        f.write("| # | Title | Video ID | Status | File |\n")
        f.write("|---|---|---|---|---|\n")
        for v in videos:
            vid_id = v["id"]
            res = results.get(vid_id, {})
            status = res.get("status", "pending")
            filename = res.get("filename")
            file_link = f"[{filename}](./{filename})" if filename else "-"
            f.write(f"| {v['index']} | [{v['title']}](https://www.youtube.com/watch?v={vid_id}) | `{vid_id}` | {status} | {file_link} |\n")

def main():
    parser = argparse.ArgumentParser(description="Download YouTube transcripts for playlists/channels with proxy fallback.")
    parser.add_argument("source", help="YouTube playlist/channel URL or path to .tsv file (video_id<tab>title)")
    parser.add_argument("-o", "--output-dir", default="transcripts", help="Directory to save transcripts (default: transcripts)")
    parser.add_argument("--proxy", help="Initial HTTP/HTTPS proxy URL (e.g. http://host:port)")
    parser.add_argument("--auto-proxy", action="store_true", default=True, help="Automatically rotate proxies if blocked (default: True)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between requests (default: 0.5)")
    parser.add_argument("--languages", default="en,en-US,en-GB", help="Comma-separated language codes to fetch (default: en,en-US,en-GB)")
    parser.add_argument("--limit", type=int, default=None, help="Max number of transcripts to download")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    lang_list = [l.strip() for l in args.languages.split(",") if l.strip()]

    videos = fetch_playlist_videos(args.source)
    if args.limit:
        videos = videos[:args.limit]

    existing_map = get_existing_video_ids(args.output_dir)
    print(f"[*] Total videos in queue: {len(videos)}")
    print(f"[*] Already present in '{args.output_dir}': {len(existing_map)}")

    current_proxy = args.proxy or DEFAULT_FALLBACK_PROXIES[0]
    proxy_cfg = GenericProxyConfig(http_url=current_proxy, https_url=current_proxy) if current_proxy else None
    api = YouTubeTranscriptApi(proxy_config=proxy_cfg)

    results = {}
    for v in videos:
        vid_id = v["id"]
        if vid_id in existing_map:
            results[vid_id] = {
                "status": "success",
                "filename": existing_map[vid_id]
            }

    consecutive_blocked = 0

    for v in videos:
        vid_id = v["id"]
        title = v["title"]
        idx = v["index"]

        if vid_id in existing_map:
            continue

        if consecutive_blocked >= 3:
            if args.auto_proxy:
                print(f"\n[!] Block detected on proxy {current_proxy}. Rotating proxy...")
                new_p = find_working_proxy(vid_id)
                if new_p:
                    current_proxy = new_p
                    proxy_cfg = GenericProxyConfig(http_url=current_proxy, https_url=current_proxy)
                    api = YouTubeTranscriptApi(proxy_config=proxy_cfg)
                    consecutive_blocked = 0
                else:
                    print("[!] No replacement proxy available right now. Pausing.")
                    results[vid_id] = {"status": "rate-limited (ip blocked)", "filename": None}
                    break
            else:
                print(f"[!] Encountered rate limits and auto-proxy disabled. Pausing.")
                break

        print(f"[{idx}/{len(videos)}] Fetching: {title} ({vid_id})...")
        clean_title = sanitize_filename(title)
        filename = f"{idx:02d} - {clean_title} [{vid_id}].txt"
        filepath = os.path.join(args.output_dir, filename)

        transcript_snippets = None
        err_type = "unknown"

        try:
            transcript_obj = api.fetch(vid_id, languages=lang_list)
            transcript_snippets = list(transcript_obj)
            consecutive_blocked = 0
        except Exception as e:
            err_type = type(e).__name__
            if "IpBlocked" in err_type or "RequestBlocked" in err_type:
                consecutive_blocked += 1
            try:
                tl = api.list(vid_id)
                for t in tl:
                    transcript_snippets = list(t.fetch())
                    consecutive_blocked = 0
                    break
            except Exception as e2:
                err_type = type(e2).__name__
                if "IpBlocked" in err_type or "RequestBlocked" in err_type:
                    consecutive_blocked += 1

        if transcript_snippets:
            timestamped_lines = []
            plain_text_words = []
            for snippet in transcript_snippets:
                text = getattr(snippet, 'text', None) or (snippet.get('text') if isinstance(snippet, dict) else str(snippet))
                start = getattr(snippet, 'start', 0.0) if hasattr(snippet, 'start') else (snippet.get('start', 0.0) if isinstance(snippet, dict) else 0.0)
                text_clean = text.replace('\n', ' ').strip()
                timestamped_lines.append(f"[{format_timestamp(start)}] {text_clean}")
                plain_text_words.append(text_clean)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\n")
                f.write(f"Video ID: {vid_id}\n")
                f.write(f"URL: https://www.youtube.com/watch?v={vid_id}\n")
                f.write(f"Snippets: {len(transcript_snippets)}\n")
                f.write("=" * 80 + "\n\n")
                f.write("--- TIMESTAMPED TRANSCRIPT ---\n\n")
                f.write("\n".join(timestamped_lines))
                f.write("\n\n" + "=" * 80 + "\n\n")
                f.write("--- FULL TEXT ---\n\n")
                f.write(" ".join(plain_text_words) + "\n")

            existing_map[vid_id] = filename
            results[vid_id] = {"status": "success", "filename": filename}
            print(f"  ✓ Saved to {filename}")
        else:
            results[vid_id] = {"status": f"failed: {err_type}", "filename": None}
            print(f"  ✗ Failed: {err_type}")

        time.sleep(args.delay)

    update_readme(args.output_dir, args.source, videos, results)
    downloaded_now = len(existing_map)
    print(f"\n[✓] Completed: {downloaded_now}/{len(videos)} transcripts present in '{args.output_dir}'.")

if __name__ == "__main__":
    main()
