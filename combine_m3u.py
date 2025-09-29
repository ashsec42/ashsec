import argparse
import os
import requests
from typing import List

def fetch_m3u_content(url: str, timeout: int) -> List[str]:
    """Fetches M3U content from a URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text.splitlines()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
        return []

def parse_m3u_lines(lines: List[str], dedupe: bool) -> List[str]:
    """Parses M3U lines, handles EXTINF, and optionally deduplicates."""
    if not lines or not lines[0].startswith('#EXTM3U'):
        print("⚠️  Invalid M3U file, skipping.")
        return []

    processed_lines = ['#EXTM3U']
    seen_urls = set()

    for i in range(1, len(lines)):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # Find the next line, which should be the stream URL
            if i + 1 < len(lines):
                stream_url = lines[i+1].strip()
                if dedupe:
                    if stream_url not in seen_urls:
                        processed_lines.append(line)
                        processed_lines.append(stream_url)
                        seen_urls.add(stream_url)
                else:
                    processed_lines.append(line)
                    processed_lines.append(stream_url)
    return processed_lines

def main():
    """Main function to combine M3U playlists."""
    parser = argparse.ArgumentParser(description="Combines multiple M3U playlists.")
    parser.add_argument("-o", "--output", default="ashsec.m3u", help="Output file path.")
    parser.add_argument("--no-dedupe", action="store_true", help="Disable deduplication of stream URLs.")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP fetch timeout in seconds.")
    args = parser.parse_args()

    m3u_links = os.environ.get('M3U_LINKS')
    if not m3u_links:
        print("❌ Error: M3U_LINKS environment variable not set.")
        return

    urls = [link.strip() for link in m3u_links.splitlines() if link.strip()]
    if not urls:
        print("❌ Error: M3U_LINKS is empty.")
        return

    combined_lines = ['#EXTM3U']
    for url in urls:
        print(f"⏳ Processing {url}...")
        lines = fetch_m3u_content(url, args.timeout)
        if lines:
            parsed_content = parse_m3u_lines(lines, not args.no_dedupe)
            # Exclude the '#EXTM3U' header from subsequent files
            combined_lines.extend(parsed_content[1:])
    
    # Write the combined playlist to the output file
    with open(args.output, "w") as f:
        f.write('\n'.join(combined_lines))
    print(f"✅ Successfully created {args.output} with {len(combined_lines) - 1} entries.")

if __name__ == "__main__":
    main()
