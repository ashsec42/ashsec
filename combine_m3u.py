import argparse
import os
import requests
from typing import List

# --- Configuration Constants ---
DEFAULT_OUTPUT_FILE = "ashsec.m3u"
DEFAULT_TIMEOUT = 30  # Increased timeout for slower servers

# headers to mimic a real web browser (Fixes 403 Forbidden errors)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

def fetch_m3u_content(url: str, timeout: int) -> List[str]:
    """
    Fetches M3U content using browser headers to bypass bot protection.
    """
    try:
        # We pass 'headers=BROWSER_HEADERS' so the server thinks we are a browser
        response = requests.get(url, timeout=timeout, headers=BROWSER_HEADERS)
        response.raise_for_status()
        
        # Force encoding to UTF-8 to handle special characters in channel names
        response.encoding = 'utf-8'
        
        lines = response.text.splitlines()
        
        # Check if we actually got a valid playlist length
        if len(lines) < 2:
            print(f"⚠️ Warning: Content from {url} is empty or too short.")
            return []
            
        print(f"✅ Success: Fetched {len(lines)} lines from {url}")
        return lines

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error (Blocked or Not Found) fetching {url}: {e}")
    except requests.exceptions.Timeout:
        print(f"❌ Timeout Error: {url} took too long to respond.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error fetching {url}: {e}")
    
    return []

def main():
    parser = argparse.ArgumentParser(description="Robustly combines M3U playlists for OTT Navigator.")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE, help="Output file path.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP fetch timeout.")
    args = parser.parse_args()

    m3u_links = os.environ.get('M3U_LINKS')
    if not m3u_links:
        print("❌ Error: M3U_LINKS environment variable not set.")
        return

    urls = [link.strip() for link in m3u_links.splitlines() if link.strip()]
    
    combined_lines = [] 
    has_header = False 

    print(f"🚀 Starting aggregation of {len(urls)} playlists...\n")

    for url in urls:
        print(f"⏳ Processing: {url}")
        lines = fetch_m3u_content(url, args.timeout)
        
        if not lines:
            print("   ↳ Skipping (No content fetched)")
            continue
            
        lines_added_count = 0
        for line in lines:
            stripped = line.strip()
            
            # 1. Handle the #EXTM3U header (Keep only the first one)
            if stripped.startswith('#EXTM3U'):
                if not has_header:
                    combined_lines.append(stripped)
                    has_header = True
                continue # Skip all subsequent #EXTM3U headers
            
            # 2. Add EVERYTHING else exactly as is.
            # This preserves #EXTVLCOPT, #EXTHTTP, and blank lines needed by OTT Navigator
            if stripped:
                combined_lines.append(stripped)
                lines_added_count += 1
        
        print(f"   ↳ Added {lines_added_count} lines to the mix.")

    # Safety: Ensure the file starts with the header if no source provided one
    if not has_header:
        combined_lines.insert(0, "#EXTM3U")
    
    # Write to file
    if len(combined_lines) > 1:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write('\n'.join(combined_lines) + '\n') 
            
            print("\n" + "="*50)
            print(f"🎉 Success! Playlist saved to: {args.output}")
            print(f"Total lines: {len(combined_lines)}")
            print("="*50)
        except IOError as e:
             print(f"❌ Error writing to file: {e}")
    else:
        print(f"\n⚠️ Error: No content was collected. Check your M3U links.")

if __name__ == "__main__":
    main()
