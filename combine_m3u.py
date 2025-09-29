#!/usr/bin/env python3
"""
combine_m3u.py

Reads a list of M3U URLs or local file paths from an input file, fetches/parses each M3U,
preserves #EXTINF lines, combines them into a single output file, and optionally deduplicates streams.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Optional, Tuple, Iterable
import requests

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Combine multiple M3U playlists into one")
    p.add_argument('-i', '--input', default='input_links.txt', help='Input file path with M3U links (default: input_links.txt)')
    p.add_argument('-o', '--output', default='ashsec.m3u', help='Output M3U file path (default: ashsec.m3u)')
    p.add_argument('--no-dedupe', action='store_true', help='Disable deduplication of stream URLs')
    p.add_argument('--timeout', type=float, default=10.0, help='HTTP fetch timeout in seconds (default: 10)')
    return p.parse_args()

def read_links(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Input links file not found: {path}")
    lines = []
    with path.open('r', encoding='utf-8') as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            lines.append(ln)
    return lines

def fetch_content(link: str, timeout: float, session: Optional[requests.Session]=None) -> str:
    parsed = urlparse(link)
    if parsed.scheme in ('http', 'https'):
        sess = session or requests.Session()
        resp = sess.get(link, timeout=timeout)
        resp.raise_for_status()
        # let requests decode based on headers if possible
        return resp.text
    else:
        # treat as local file path (support file:// or plain paths)
        if parsed.scheme == 'file':
            path = Path(parsed.path)
        else:
            path = Path(link)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {path}")
        return path.read_text(encoding='utf-8', errors='ignore')

def parse_m3u(content: str) -> Iterable[Tuple[Optional[str], str]]:
    """
    Parse M3U content and yield (extinf_line_or_None, stream_url) preserving EXTINF when present.
    """
    extinf = None
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith('#EXTINF'):
            extinf = line
            continue
        if line.startswith('#'):
            # unknown tag: ignore unless it's EXTINF (already handled)
            continue
        # this is a stream URL / path
        yield (extinf, line)
        extinf = None

def combine(entries: Iterable[Tuple[Optional[str], str]], dedupe: bool=True):
    seen = set()
    for extinf, url in entries:
        key = url.strip()
        if dedupe:
            if key in seen:
                continue
            seen.add(key)
        yield extinf, url

def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    try:
        links = read_links(input_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
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
            print(f"Warning: failed to fetch/parse {link}: {e}", file=sys.stderr)
    final_entries = list(combine(all_entries, dedupe=not args.no_dedupe))
    # write output
    with output_path.open('w', encoding='utf-8') as out:
        out.write('#EXTM3U\\n')
        for extinf, url in final_entries:
            if extinf:
                out.write(f'{extinf}\\n')
            out.write(f'{url}\\n')
    print(f"Wrote {len(final_entries)} entries to {output_path} (dedupe={'off' if args.no_dedupe else 'on'})")

if __name__ == '__main__':
    main()
