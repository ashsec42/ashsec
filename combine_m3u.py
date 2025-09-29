import argparse
import os
import requests
from typing import List

def fetch_m3u_content(url: str, timeout: int) -> List[str]:
    """Fetches M3U content from a URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        print(f"✅ Successfully fetched content from {url}")
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
    total_streams = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # Look for the next non-comment/non-empty line for the stream URL
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                j += 1
            
            if j < len(lines):
                stream_url = lines[j].strip()
                total_streams += 1
                if dedupe:
                    if stream_url not in seen_urls:
                        processed_lines.append(line)
                        processed_lines.append(stream_url)
                        seen_urls.add(stream_url)
                else:
                    processed_lines.append(line)
                    processed_lines.append(stream_url)
                i = j + 1 # Continue after the found stream URL
            else:
                i += 1 # Move to next line if no stream URL is found
        else:
            i += 1 # Move to next line

    if total_streams > 0:
        print(f"Parsed {total_streams} streams. Adding to combined list.")
    else:
        print("No valid streams found in this playlist.")
    
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
    total_unique_streams = 0

    for url in urls:
        print(f"⏳ Processing {url}...")
        lines = fetch_m3u_content(url, args.timeout)
        if lines:
            parsed_content = parse_m3u_lines(lines, not args.no_dedupe)
            # Exclude the '#EXTM3U' header from subsequent files
            combined_lines.extend(parsed_content[1:])
    
    # Check if any content was actually added
    if len(combined_lines) > 1:
        with open(args.output, "w") as f:
            f.write('\n'.join(combined_lines))
        total_unique_streams = (len(combined_lines) - 1) // 2
        print(f"✅ Successfully created {args.output} with {total_unique_streams} unique stream entries.")
    else:
        print(f"⚠️  No valid streams found from any of the URLs. {args.output} was not created or updated.")

if __name__ == "__main__":
    main()
