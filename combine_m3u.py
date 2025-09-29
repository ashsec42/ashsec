#!/usr/bin/env python3
import argparse
import os
import requests
from pathlib import Path
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="Combine multiple M3U playlists into one.")
    parser.add_argument("-o", "--output", default="ashsec.m3u", help="Output file path")
    parser.add_argument("--no-dedupe", action="store_true", help="Disable URL deduplication")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP fetch timeout in seconds")
    return parser.parse_args()

def fetch_content(url, timeout=10, session=None):
    s = session or requests
    resp = s.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text

def parse_m3u(content):
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            extinf = line
            i += 1
            url = lines[i].strip() if i < len(lines) else ""
            yield (extinf, url)
        elif line and not line.startswith("#"):
            yield (None, line)
        i += 1

def combine(entries, dedupe=True):
    combined = []
    seen_urls = set()
    for extinf, url in entries:
        if not dedupe or url not in seen_urls:
            combined.append((extinf, url))
            seen_urls.add(url)
    return combined

def main():
    args = parse_args()
    secret_links = os.getenv("M3U_LINKS")
    if not secret_links:
        print("ERROR: M3U_LINKS secret is missing", file=sys.stderr)
        sys.exit(1)

    links = [line.strip() for line in secret_links.splitlines() if line.strip()]

    session = requests.Session()
    all_entries = []
    for link in links:
        try:
            print(f"Fetching: {link}")
            content = fetch_content(link, timeout=args.timeout, session=session)
            entries = list(parse_m3u(content))
            print(f"  -> {len(entries)} entries parsed")
            all_entries.extend(entries)
        except Exception as e:
            print(f"Warning: failed to fetch/parse {link}: {e}")

    final_entries = combine(all_entries, dedupe=not args.no_dedupe)

    with Path(args.output).open('w', encoding='utf-8') as out:
        out.write('#EXTM3U\n')
        for extinf, url in final_entries:
            if extinf:
                out.write(f'{extinf}\n')
            out.write(f'{url}\n')

    print(f"Wrote {len(final_entries)} entries to {args.output} (dedupe={'off' if args.no_dedupe else 'on'})")

if __name__ == "__main__":
    main()
