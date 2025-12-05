import argparse
import os
import requests
from typing import List

# --- Configuration Constants ---
DEFAULT_OUTPUT_FILE = "ashsec.m3u"
DEFAULT_TIMEOUT = 30 

# Headers to mimic a real web browser (Fixes 403 Forbidden errors)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

def fetch_m3u_content(url: str, timeout: int) -> List[str]:
    """
    Fetches M3U content and cleans invisible characters that break Android apps.
    """
    try:
        response = requests.get(url, timeout=timeout, headers=BROWSER_HEADERS)
        response.raise_for_status()
        response.encoding = 'utf-8' # Force UTF-8 encoding
        
        # KEY FIX: Remove BOM (Byte Order Mark) - \ufeff
        # This invisible character often makes Android apps stop reading the file.
        content = response.text.replace('\ufeff', '')
        
        lines = content.splitlines()
        
        if len(lines) < 2:
            print(f"⚠️ Warning: Content from {url} is too short.")
            return []
            
        print(f"✅ Success: Fetched {len(lines)} lines from {url}")
        return lines

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
    
    return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    m3u_links = os.environ.get('M3U_LINKS')
    if not m3u_links:
        print("❌ Error: M3U_LINKS not set.")
        return

    # --- FIX WAS APPLIED HERE ---
    urls = [link.strip() for link in m3u_links.splitlines() if link.strip()]
    
    # Initialize with the standard header
    combined_lines = ["#EXTM3U"] 

    print(f"🚀 Starting aggregation of {len(urls)} playlists...\n")

    for url in urls:
        print(f"⏳ Processing: {url}")
        lines = fetch_m3u_content(url, args.timeout)
        
        if not lines:
            continue
            
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue

            # Skip existing headers (we already added one at the start)
            if stripped.startswith('#EXTM3U'):
                continue
            
            # APPEND EVERYTHING ELSE (including #EXTVLCOPT, etc.)
            combined_lines.append(stripped)

    # Write to file
    if len(combined_lines) > 1:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write('\n'.join(combined_lines)) # Join with newlines
        
        print("\n" + "="*50)
        print(f"🎉 Success! Playlist saved to: {args.output}")
        print(f"Total lines: {len(combined_lines)}")
        print("="*50)
