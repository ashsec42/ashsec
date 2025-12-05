import argparse
import os
import requests
import json
from typing import List

# --- Configuration ---
DEFAULT_OUTPUT_FILE = "ashsec.m3u"
DEFAULT_TIMEOUT = 30 
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def fetch_m3u_content(url: str, timeout: int) -> List[str]:
    try:
        response = requests.get(url, timeout=timeout, headers=BROWSER_HEADERS)
        response.raise_for_status()
        response.encoding = 'utf-8'
        # Clean invisible BOM characters
        return response.text.replace('\ufeff', '').splitlines()
    except Exception as e:
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

    urls = [link.strip() for link in m3u_links.splitlines() if link.strip()]
    
    combined_lines = ["#EXTM3U"]
    
    print(f"🚀 Starting conversion of {len(urls)} playlists...\n")

    for url in urls:
        print(f"⏳ Processing: {url}")
        lines = fetch_m3u_content(url, args.timeout)
        
        if not lines: 
            continue

        # Variables to hold data for the CURRENT channel being processed
        current_extinf = None
        current_headers = {}

        for line in lines:
            line = line.strip()
            if not line: continue

            # 1. Capture Channel Info
            if line.startswith('#EXTINF:'):
                current_extinf = line
                current_headers = {} # Reset headers for new channel
            
            # 2. Capture User-Agent
            elif line.startswith('#EXTVLCOPT:http-user-agent='):
                current_headers['User-Agent'] = line.split('=', 1)[1]
            
            # 3. Capture Referer
            elif line.startswith('#EXTVLCOPT:http-referrer='):
                current_headers['Referer'] = line.split('=', 1)[1]
                
            # 4. Capture Origin
            elif line.startswith('#EXTVLCOPT:http-origin='):
                current_headers['Origin'] = line.split('=', 1)[1]

            # 5. Capture Cookie (JSON Format)
            elif line.startswith('#EXTHTTP:'):
                try:
                    # Extract the JSON part after #EXTHTTP:
                    json_str = line.split(':', 1)[1]
                    data = json.loads(json_str)
                    if "cookie" in data:
                        current_headers['Cookie'] = data['cookie']
                except:
                    pass # Ignore if JSON is malformed

            # 6. Process the URL (The final step for a channel)
            elif line.startswith('http') and not line.startswith('#'):
                if current_extinf:
                    # Start building the pipe section
                    # Format: http://url...|User-Agent=X&Referer=Y&Cookie=Z
                    
                    url_with_headers = line
                    header_parts = []
                    
                    if 'User-Agent' in current_headers:
                        header_parts.append(f"User-Agent={current_headers['User-Agent']}")
                    if 'Referer' in current_headers:
                        header_parts.append(f"Referer={current_headers['Referer']}")
                    if 'Cookie' in current_headers:
                        header_parts.append(f"Cookie={current_headers['Cookie']}")
                    # Note: OTT Nav handles Origin differently, but Referer is usually enough. 
                    # If needed, we can add Origin as a generic header.

                    if header_parts:
                        url_with_headers += "|" + "&".join(header_parts)

                    # Append to master list
                    combined_lines.append(current_extinf)
                    combined_lines.append(url_with_headers)
                    
                    # Reset
                    current_extinf = None
                    current_headers = {}

    # Write to file
    if len(combined_lines) > 1:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write('\n'.join(combined_lines))
        
        print("\n" + "="*50)
        print(f"🎉 Success! Converted & Saved to: {args.output}")
        print(f"Total Channels: {(len(combined_lines)-1)//2}")
        print("="*50)
    else:
        print(f"\n⚠️ Error: No channels found.")

if __name__ == "__main__":
    main()
