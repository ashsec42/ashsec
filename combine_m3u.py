import argparse
import os
import requests
from typing import List

# Map parts of the URL to a friendly group title
PROVIDER_MAPPING = {
    'jstar': 'dio',
    'z5': 'je5',
    'tsepg': 'TataPlay'
}

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

def parse_m3u_lines(lines: List[str], dedupe: bool, catchup: bool, group_title: str) -> List[str]:
    """Parses M3U lines, handles EXTINF, and optionally deduplicates and adds catch-up parameters and group titles."""
    if not lines or not lines[0].startswith('#EXTM3U'):
        print("⚠️  Invalid M3U file, skipping.")
        return []

    processed_lines = []
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

                # Add group-title to the EXTINF line
                if f'group-title="{group_title}"' not in line:
                    line = line.replace('tvg-name=', f'group-title="{group_title}" tvg-name=')
                    if 'group-title' not in line: # If tvg-name isn't present
                         line = line.replace('tvg-id=', f'group-title="{group_title}" tvg-id=')
                         if 'tvg-id' not in line: # Fallback if neither is present
                             line = line.replace('#EXTINF:-1', f'#EXTINF:-1 group-title="{group_title}"')

                # Add catch-up parameter if the flag is set and it's a valid HTTP URL
                if catchup and stream_url.startswith('http'):
                    if '?' in stream_url:
                        stream_url += '&catchup-days=7'
                    else:
                        stream_url += '?catchup-days=7'
                        
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
    parser.add_argument("--catchup", action="store_true", help="Add catch-up parameters to stream URLs.")
    parser.add_argument("--no-dedupe", action="store_true", help="Disable deduplication of stream URLs.")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP fetch timeout in seconds.")
    args = parser.parse_args()

    m3u_links = os.environ.get('M3U_LINKS')
    if not m3u_links:
        print("❌ Error: M3U_LINKS environment variable not set.")
        return

    # EPG URL is hardcoded
    epg_url = "https://avkb.short.gy/epg.xml.gz"
    
    urls = [link.strip() for link in m3u_links.splitlines() if link.strip()]
    if not urls:
        print("❌ Error: M3U_LINKS is empty.")
        return
    
    header = '#EXTM3U'
    if epg_url:
        header += f' url-tvg="{epg_url}"'

    combined_lines = [header]
    total_unique_streams = 0

    for url in urls:
        print(f"⏳ Processing {url}...")
        
        # Determine the group title based on the URL
        group = 'Other'
        for key, value in PROVIDER_MAPPING.items():
            if key in url:
                group = value
                break
        
        lines = fetch_m3u_content(url, args.timeout)
        if lines:
            parsed_content = parse_m3u_lines(lines, not args.no_dedupe, args.catchup, group)
            combined_lines.extend(parsed_content)
    
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
