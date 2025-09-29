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

def main():
    """Main function to combine M3U playlists with minimal editing."""
    parser = argparse.ArgumentParser(description="Combines multiple M3U playlists.")
    parser.add_argument("-o", "--output", default="ashsec.m3u", help="Output file path.")
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

    combined_lines = []
    has_header = False

    for url in urls:
        print(f"⏳ Processing {url}...")
        lines = fetch_m3u_content(url, args.timeout)
        
        if lines:
            # Check if a header exists and add it only once
            if not has_header:
                if lines[0].startswith('#EXTM3U'):
                    combined_lines.append(lines[0])
                    has_header = True
                    lines = lines[1:] # Remove header for remaining files
            
            # Append all remaining lines from the source file
            for line in lines:
                if line.strip(): # Skip empty lines
                    combined_lines.append(line)

    if combined_lines:
        with open(args.output, "w") as f:
            f.write('\n'.join(combined_lines))
        print(f"✅ Successfully created {args.output}.")
    else:
        print(f"⚠️  No content found from any of the URLs. {args.output} was not created or updated.")

if __name__ == "__main__":
    main()
